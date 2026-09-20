#!/usr/bin/env python3
"""Tahminleri degerlendirir: segmentasyon + tespit metrikleri.

Ciktilar:
  vaka_bazli.csv   -> her hasta icin Dice, HD95, hacim hatasi, lezyon sayilari
  lezyon_bazli.csv -> her gercek lezyon icin bulundu/bulunmadi ve boyut grubu
  ozet.json / ekrana ozet -> abstract'a yazilacak sayilar

Metrikler:
  Segmentasyon : Dice ve HD95 (karaciger organi ve tumor icin ayri)
  Tespit (lezyon) : duyarlilik, hasta basina yanlis pozitif, boyuta gore duyarlilik
  Tespit (hasta)  : duyarlilik, ozgulluk, AUC (skor = tahmin edilen tumor hacmi)

Kullanim:
  python 04_degerlendir.py --gt /mnt/veri/nnUNet_raw/Dataset001_LiverTumor/labelsTs \
      --tahmin /mnt/veri/cikti/nnunet_test --cikti /mnt/veri/cikti/nnunet_metrik
"""
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage

BAGLANTI = np.ones((3, 3, 3))          # 26 komsuluk
ORTUSME_ESIGI = 0.1                    # gercek lezyonun en az %10'u ortusurse "bulundu"
HASTA_ESIGI_CM3 = 0.1                  # bu hacmin uzerinde tumor -> hasta pozitif


def voksel_araligi(affine) -> np.ndarray:
    """Voksel araligi (mm). np.diag yerine sutun normu kullanilir: oblik
    (dondurulmus) affine'lerde kosegen sifir olabilir ve hesaplari bozar."""
    return np.linalg.norm(np.asarray(affine)[:3, :3], axis=0)


def etiket_yukle(yol: Path):
    """Etiket hacmini ve voksel araligini dondurur. .nii.gz ve .npz destekli."""
    if yol.suffix == ".npz":
        d = np.load(yol)
        return d["etiket"].astype(np.uint8), tuple(float(x) for x in d["aralik"])
    im = nib.load(yol)
    return (np.asanyarray(im.dataobj).astype(np.uint8),
            tuple(voksel_araligi(im.affine).tolist()))


def dice(a: np.ndarray, b: np.ndarray) -> float:
    toplam = a.sum() + b.sum()
    if toplam == 0:
        return float("nan")            # ikisi de bossa tanimsiz, ortalamaya katilmaz
    return float(2 * np.logical_and(a, b).sum() / toplam)


def yuzey_mesafeleri(a: np.ndarray, b: np.ndarray, aralik) -> np.ndarray:
    """a'nin yuzeyinden b'nin yuzeyine olan mesafeler (mm)."""
    if not a.any() or not b.any():
        return np.array([])
    kenar_a = a ^ ndimage.binary_erosion(a)
    mesafe_b = ndimage.distance_transform_edt(~b, sampling=aralik)
    return mesafe_b[kenar_a]


def hd95(a: np.ndarray, b: np.ndarray, aralik) -> float:
    d1, d2 = yuzey_mesafeleri(a, b, aralik), yuzey_mesafeleri(b, a, aralik)
    if d1.size == 0 or d2.size == 0:
        return float("nan")
    return float(np.percentile(np.concatenate([d1, d2]), 95))


def boyut_grubu(cap_mm: float) -> str:
    if cap_mm < 10:
        return "<1cm"
    if cap_mm < 20:
        return "1-2cm"
    return ">=2cm"


def vakayi_degerlendir(args):
    ad, gt_p, tahmin_p = args
    gt, aralik = etiket_yukle(Path(gt_p))
    pr, _ = etiket_yukle(Path(tahmin_p))
    if gt.shape != pr.shape:
        raise ValueError(f"{ad}: gercek {gt.shape} ile tahmin {pr.shape} ayni degil")
    voksel_cm3 = float(np.prod(aralik)) / 1000.0

    gt_kc, pr_kc = gt >= 1, pr >= 1               # organ = karaciger + tumor
    gt_t, pr_t = gt == 2, pr == 2

    satir = dict(
        vaka=ad,
        dice_karaciger=dice(gt_kc, pr_kc),
        dice_tumor=dice(gt_t, pr_t),
        hd95_karaciger=hd95(gt_kc, pr_kc, aralik),
        hd95_tumor=hd95(gt_t, pr_t, aralik),
        gt_tumor_hacmi_cm3=float(gt_t.sum() * voksel_cm3),
        tahmin_tumor_hacmi_cm3=float(pr_t.sum() * voksel_cm3),
    )
    satir["hacim_hatasi_yuzde"] = (
        abs(satir["tahmin_tumor_hacmi_cm3"] - satir["gt_tumor_hacmi_cm3"])
        / satir["gt_tumor_hacmi_cm3"] * 100 if satir["gt_tumor_hacmi_cm3"] > 0 else np.nan)

    gt_lab, gt_n = ndimage.label(gt_t, structure=BAGLANTI)
    pr_lab, pr_n = ndimage.label(pr_t, structure=BAGLANTI)

    lezyonlar = []
    eslesen_tahminler = set()
    for i in range(1, gt_n + 1):
        m = gt_lab == i
        koord = np.argwhere(m)
        cap = float(((koord.max(0) - koord.min(0) + 1) * np.array(aralik)).max())
        ortusen = pr_lab[m]
        ortusen = ortusen[ortusen > 0]
        bulundu = False
        if ortusen.size / m.sum() >= ORTUSME_ESIGI:
            bulundu = True
            eslesen_tahminler.update(np.unique(ortusen).tolist())
        lezyonlar.append(dict(vaka=ad, lezyon=i, cap_mm=round(cap, 1),
                              boyut_grubu=boyut_grubu(cap),
                              hacim_cm3=round(float(m.sum() * voksel_cm3), 3),
                              bulundu=bulundu))

    yanlis_pozitif = pr_n - len({i for i in eslesen_tahminler if i > 0})
    satir.update(gt_lezyon_sayisi=gt_n, tahmin_lezyon_sayisi=pr_n,
                 bulunan_lezyon=sum(l["bulundu"] for l in lezyonlar),
                 yanlis_pozitif=max(0, yanlis_pozitif),
                 gt_pozitif=bool(gt_t.any()),
                 tahmin_pozitif=bool(satir["tahmin_tumor_hacmi_cm3"] > HASTA_ESIGI_CM3))
    return satir, lezyonlar


def auc(skorlar: np.ndarray, etiketler: np.ndarray) -> float:
    """Rank tabanli AUC (sklearn bagimliligi olmadan)."""
    poz, neg = skorlar[etiketler], skorlar[~etiketler]
    if poz.size == 0 or neg.size == 0:
        return float("nan")
    siralar = pd.Series(np.concatenate([poz, neg])).rank().to_numpy()
    return float((siralar[:poz.size].sum() - poz.size * (poz.size + 1) / 2) / (poz.size * neg.size))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gt", required=True, help="gercek etiket klasoru (labelsTs)")
    p.add_argument("--tahmin", required=True, help="nnU-Net tahmin klasoru")
    p.add_argument("--cikti", required=True)
    p.add_argument("--isler", type=int, default=os.cpu_count() or 8)
    a = p.parse_args()

    gt_klasor, tahmin_klasor, cikti = Path(a.gt), Path(a.tahmin), Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)

    isler = []
    gt_dosyalar = sorted(list(gt_klasor.glob("*.nii.gz")) + list(gt_klasor.glob("*.npz")))
    for gt_p in gt_dosyalar:
        ad = gt_p.name.replace(".nii.gz", "").replace(".npz", "")
        adaylar = [tahmin_klasor / f"{ad}.nii.gz", tahmin_klasor / f"{ad}.npz"]
        tahmin_p = next((x for x in adaylar if x.exists()), None)
        if tahmin_p:
            isler.append((ad, str(gt_p), str(tahmin_p)))
        else:
            print(f"UYARI: tahmin yok -> {gt_p.name}")
    print(f"{len(isler)} vaka degerlendiriliyor")

    satirlar, lezyonlar = [], []
    with ProcessPoolExecutor(max_workers=a.isler) as havuz:
        gelecekler = [havuz.submit(vakayi_degerlendir, i) for i in isler]
        for n, f in enumerate(as_completed(gelecekler), 1):
            s, l = f.result()
            satirlar.append(s)
            lezyonlar.extend(l)
            if n % 25 == 0:
                print(f"  {n}/{len(isler)}", flush=True)

    vaka = pd.DataFrame(satirlar).sort_values("vaka")
    lez = pd.DataFrame(lezyonlar)
    vaka.to_csv(cikti / "vaka_bazli.csv", index=False)
    lez.to_csv(cikti / "lezyon_bazli.csv", index=False)

    tumorlu = vaka[vaka.gt_pozitif]
    ozet = {
        "vaka_sayisi": int(len(vaka)),
        "tumorlu_vaka": int(len(tumorlu)),
        "tumorsuz_vaka": int((~vaka.gt_pozitif).sum()),
        "dice_karaciger_ort": round(float(vaka.dice_karaciger.mean()), 4),
        "dice_tumor_ort_tumorlu_vakalarda": round(float(tumorlu.dice_tumor.mean()), 4),
        "hd95_karaciger_ort_mm": round(float(vaka.hd95_karaciger.mean()), 2),
        "hd95_tumor_ort_mm": round(float(tumorlu.hd95_tumor.mean()), 2),
        "tumor_hacim_hatasi_ort_yuzde": round(float(tumorlu.hacim_hatasi_yuzde.mean()), 1),
        "lezyon_duyarliligi": round(float(lez.bulundu.mean()), 4) if len(lez) else None,
        "hasta_basina_yanlis_pozitif": round(float(vaka.yanlis_pozitif.mean()), 3),
        "hasta_duzeyi_duyarlilik": round(float(vaka[vaka.gt_pozitif].tahmin_pozitif.mean()), 4),
        "hasta_duzeyi_ozgulluk": round(float((~vaka[~vaka.gt_pozitif].tahmin_pozitif).mean()), 4)
        if (~vaka.gt_pozitif).any() else None,
        "hasta_duzeyi_auc": round(auc(vaka.tahmin_tumor_hacmi_cm3.to_numpy(),
                                      vaka.gt_pozitif.to_numpy()), 4),
    }
    if len(lez):
        ozet["boyuta_gore_duyarlilik"] = {
            g: dict(n=int(len(d)), duyarlilik=round(float(d.bulundu.mean()), 4))
            for g, d in lez.groupby("boyut_grubu")}

    (cikti / "ozet.json").write_text(json.dumps(ozet, indent=2, ensure_ascii=False))
    print("\n--- Ozet ---")
    print(json.dumps(ozet, indent=2, ensure_ascii=False))
    print(f"\nDosyalar: {cikti}")


if __name__ == "__main__":
    main()
