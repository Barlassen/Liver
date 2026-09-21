#!/usr/bin/env python3
"""Dogrusal sonda: kodlayici ozniteliklerinde "tumor mu karaciger mi" bilgisi var mi?

Hicbir model egitmeden, donuk kodlayicinin her blogunun token ciktisina lojistik
regresyon oturtur ve karaciger icindeki tokenlerde tumor/karaciger ayrimini olcer.
Egitim vakalarinda oturtulur, DOGRULAMA vakalarinda (farkli hastalar) olculur.

Test edilen hipotezler (her biri bir "varyant"):
  hazir_standart : Kol A'nin girdisi (pencere -140..260 + genis pencere)
  hazir_dar      : dar karaciger penceresi (-20..180) -> doku kontrasti artar mi?
  rastgele       : ayni mimari, on egitimsiz -> on egitim ne kaziyor?
  hazir_zoom2    : karaciger merkezli 128x128 kirpim 2x buyutulur -> token 24 mm yerine 12 mm

Her varyantta bloklar ayri ayri + k4 birlesimi (6/12/18/24) + son cikti sondalanir.
Referans: kodlayicisiz ham pikseller (token basina 2x16x16 voksel).

Olcut: dogrulama tokenlerinde AUC
  tam   : tokenin >=%50'si tumor  vs  hic tumor yok
  kismi : tokenin %0-50'si tumor (kucuk lezyon / sinir) vs hic tumor yok

Kullanim:
  python betikler/15_dogrusal_sonda.py --egitim ~/veri/veri22/train --dogrulama ~/veri/veri22/val \
      --cikti ~/sonda
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mimari"))
from kodlayici import VJepaKodlayici  # noqa: E402
from tahmin import _doldur_kirp  # noqa: E402
from veri import _yukle  # noqa: E402

SLAB, BOYUT, YAMA, TUBELET = 16, 256, 16, 2
STANDART = ((-140.0, 260.0), (-1000.0, 1000.0))
DAR = ((-20.0, 180.0), (-1000.0, 1000.0))
VARYANTLAR = {
    "hazir_standart": dict(rastgele=False, pencere=STANDART, zoom=False),
    "hazir_dar": dict(rastgele=False, pencere=DAR, zoom=False),
    "rastgele": dict(rastgele=True, pencere=STANDART, zoom=False),
    "hazir_zoom2": dict(rastgele=False, pencere=STANDART, zoom=True),
}
BLOKLAR = [1, 3, 6, 9, 12, 15, 18, 21, 24]
K4 = [6, 12, 18, 24]
AZAMI_NEGATIF = 30000          # egitimde negatif token ust siniri (hiz icin)


def pencerele(hu, pencere):
    return np.stack([np.clip((hu - a) / (u - a), 0, 1) for a, u in pencere]).astype(np.float32)


def slablari_sec(yol: Path, adet: int):
    """Tumorlu bolgeden deterministik slab'ler: tumor dilimlerinin ceyreklerine ortalanir."""
    hu, et, _ = _yukle(yol)
    D = hu.shape[2]
    tz = np.where((et == 2).any(axis=(0, 1)))[0]
    if len(tz) == 0:
        return []
    merkezler = sorted({int(np.quantile(tz, q)) for q in np.linspace(0.2, 0.8, adet)})
    cikti = []
    for m in merkezler:
        z0 = int(np.clip(m - SLAB // 2, 0, max(0, D - SLAB)))
        h = np.moveaxis(hu[..., z0:z0 + SLAB], -1, 0)
        e = np.moveaxis(et[..., z0:z0 + SLAB], -1, 0)
        if h.shape[0] < SLAB:
            eksik = SLAB - h.shape[0]
            h = np.pad(h, ((0, eksik), (0, 0), (0, 0)), mode="edge")
            e = np.pad(e, ((0, eksik), (0, 0), (0, 0)), mode="edge")
        cikti.append((h, e))
    return cikti


def girdi_hazirla(h, e, pencere, zoom):
    """(D,H,W) HU + etiket -> model girdisi (K,D,256,256) ve etiket (D,256,256)."""
    x = pencerele(h, pencere)                               # (K, D, H, W)
    if not zoom:
        x, _ = _doldur_kirp(x, BOYUT)
        y, _ = _doldur_kirp(e[None].astype(np.float32), BOYUT)
        return x, y[0].astype(np.int64)
    # karaciger merkezli 128x128 kirpim -> 256'ya 2x buyutme
    b = BOYUT // 2
    K, D, H, W = x.shape
    ph, pw = max(0, b - H), max(0, b - W)
    if ph or pw:
        x = np.pad(x, ((0, 0), (0, 0), (0, ph), (0, pw)))
        e = np.pad(e, ((0, 0), (0, ph), (0, pw)))
        H, W = x.shape[-2:]
    kc = np.argwhere(e >= 1)
    cy, cx = (kc[:, 1].mean(), kc[:, 2].mean()) if len(kc) else (H / 2, W / 2)
    y0 = int(np.clip(round(cy - b / 2), 0, H - b))
    x0 = int(np.clip(round(cx - b / 2), 0, W - b))
    x = torch.from_numpy(x[..., y0:y0 + b, x0:x0 + b].copy())
    y = torch.from_numpy(e[:, y0:y0 + b, x0:x0 + b].astype(np.float32).copy())
    x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
    y = F.interpolate(y[None], scale_factor=2, mode="nearest")[0]
    return x.numpy(), y.numpy().astype(np.int64)


def token_etiketleri(y):
    """(D,256,256) etiket -> token basina tumor ve organ oranlari, (t*h*w,) sirasinda."""
    t, h, w = SLAB // TUBELET, BOYUT // YAMA, BOYUT // YAMA
    y = y.reshape(t, TUBELET, h, YAMA, w, YAMA)
    tumor = (y == 2).mean(axis=(1, 3, 5)).reshape(-1)
    organ = (y >= 1).mean(axis=(1, 3, 5)).reshape(-1)
    return tumor, organ


def ham_piksel(x):
    """Kodlayicisiz referans: token basina karaciger penceresindeki 2x16x16 voksel."""
    t, h, w = SLAB // TUBELET, BOYUT // YAMA, BOYUT // YAMA
    v = x[0].reshape(t, TUBELET, h, YAMA, w, YAMA).transpose(0, 2, 4, 1, 3, 5)
    return v.reshape(t * h * w, -1)


@torch.no_grad()
def oznitelik_topla(kod, vakalar, varyant, cihaz, slab_adedi):
    """Organ icindeki tokenler icin: {katman: (N, C)}, tumor orani, vaka kimligi."""
    ozn = {k: [] for k in BLOKLAR + ["son", "ham"]}
    oranlar, kimlik = [], []
    for vi, yol in enumerate(vakalar):
        for h, e in slablari_sec(yol, slab_adedi):
            x, y = girdi_hazirla(h, e, varyant["pencere"], varyant["zoom"])
            tumor, organ = token_etiketleri(y)
            sec = organ >= 0.5
            if not sec.any():
                continue
            xt = torch.from_numpy(x).unsqueeze(0).to(cihaz)
            with torch.autocast(cihaz.type, dtype=torch.float16, enabled=cihaz.type == "cuda"):
                c = kod.govde(pixel_values_videos=kod._hazirla(xt), output_hidden_states=True)
            gizli = c.hidden_states
            assert len(gizli) == 25, f"25 gizli durum bekleniyordu (gomme + 24 blok), {len(gizli)} geldi"
            for k in BLOKLAR:
                ozn[k].append(gizli[k][0][torch.from_numpy(sec).to(cihaz)].float().cpu().numpy()
                              .astype(np.float16))
            ozn["son"].append(c.last_hidden_state[0][torch.from_numpy(sec).to(cihaz)]
                              .float().cpu().numpy().astype(np.float16))
            ozn["ham"].append(ham_piksel(x)[sec].astype(np.float16))
            oranlar.append(tumor[sec])
            kimlik.append(np.full(sec.sum(), vi))
    ozn = {k: np.concatenate(v) for k, v in ozn.items()}
    ozn["k4"] = np.concatenate([ozn[k] for k in K4], axis=1)
    return ozn, np.concatenate(oranlar), np.concatenate(kimlik)


def sonda(Xe, ye_oran, Xd, yd_oran, tohum=0):
    """Egitimde tam pozitif (>=0.5) vs negatif (0) ile oturt; dogrulamada tam ve kismi AUC."""
    rng = np.random.default_rng(tohum)
    poz, neg = np.where(ye_oran >= 0.5)[0], np.where(ye_oran == 0)[0]
    if len(neg) > AZAMI_NEGATIF:
        neg = rng.choice(neg, AZAMI_NEGATIF, replace=False)
    idx = np.concatenate([poz, neg])
    olc = StandardScaler().fit(Xe[idx].astype(np.float32))
    clf = LogisticRegression(C=0.1, max_iter=2000, class_weight="balanced")
    clf.fit(olc.transform(Xe[idx].astype(np.float32)), (ye_oran[idx] >= 0.5).astype(int))
    skor = clf.decision_function(olc.transform(Xd.astype(np.float32)))
    dneg = yd_oran == 0
    sonuc = {}
    for ad, m in (("tam", yd_oran >= 0.5), ("kismi", (yd_oran > 0) & (yd_oran < 0.5))):
        yy = np.concatenate([np.ones(m.sum()), np.zeros(dneg.sum())])
        ss = np.concatenate([skor[m], skor[dneg]])
        sonuc[f"auc_{ad}"] = float(roc_auc_score(yy, ss))
        sonuc[f"ap_{ad}"] = float(average_precision_score(yy, ss))
        sonuc[f"n_{ad}"] = int(m.sum())
    sonuc["n_negatif"] = int(dneg.sum())
    return sonuc


def tumorlu_vakalar(klasor: Path, adet: int, tohum: int):
    fs = sorted(klasor.glob("*.npz"))
    np.random.default_rng(tohum).shuffle(fs)
    secilen = []
    for f in fs:
        if (np.load(f)["etiket"] == 2).any():
            secilen.append(f)
        if len(secilen) == adet:
            break
    return secilen


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--egitim", required=True)
    p.add_argument("--dogrulama", required=True)
    p.add_argument("--cikti", required=True)
    p.add_argument("--egitim-vaka", type=int, default=80)
    p.add_argument("--dogrulama-vaka", type=int, default=40)
    p.add_argument("--slab-adedi", type=int, default=3)
    p.add_argument("--varyantlar", nargs="*", default=list(VARYANTLAR))
    a = p.parse_args()

    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    egit_v = tumorlu_vakalar(Path(a.egitim), a.egitim_vaka, 0)
    dogr_v = tumorlu_vakalar(Path(a.dogrulama), a.dogrulama_vaka, 1)
    ortak = {v.stem for v in egit_v} & {v.stem for v in dogr_v}
    assert not ortak, f"egitim/dogrulama cakisiyor: {ortak}"
    print(f"egitim {len(egit_v)} vaka | dogrulama {len(dogr_v)} vaka (hasta ayrik)")

    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    tum = []
    for ad in a.varyantlar:
        v = VARYANTLAR[ad]
        t0 = time.time()
        torch.manual_seed(0)
        kod = VJepaKodlayici(dondur=True, rastgele=v["rastgele"]).to(cihaz).eval()
        Oe, ye, _ = oznitelik_topla(kod, egit_v, v, cihaz, a.slab_adedi)
        Od, yd, _ = oznitelik_topla(kod, dogr_v, v, cihaz, a.slab_adedi)
        del kod
        torch.cuda.empty_cache()
        print(f"\n### {ad}  (egitim token {len(ye)}, poz {(ye >= .5).sum()} | "
              f"dogrulama token {len(yd)}, poz {(yd >= .5).sum()}, kismi "
              f"{((yd > 0) & (yd < .5)).sum()})  oznitelik {time.time()-t0:.0f} sn")
        katmanlar = ([] if v["zoom"] or v["pencere"] is DAR or v["rastgele"] else ["ham"]) \
            + BLOKLAR + ["k4", "son"]
        if v["pencere"] is DAR:
            katmanlar = ["ham"] + katmanlar
        for k in katmanlar:
            s = sonda(Oe[k], ye, Od[k], yd)
            s.update(varyant=ad, katman=str(k))
            tum.append(s)
            print(f"  {str(k):>4}: AUC tam {s['auc_tam']:.3f} | kismi {s['auc_kismi']:.3f} | "
                  f"AP tam {s['ap_tam']:.3f}", flush=True)
        (cikti / "sonda.json").write_text(json.dumps(tum, indent=1))
    print(f"\nYazildi: {cikti/'sonda.json'}")


if __name__ == "__main__":
    main()
