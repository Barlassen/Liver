#!/usr/bin/env python3
"""Iki kolu ayni test vakalarinda eslestirilmis olarak karsilastirir.

Kol farki kucuk oldugunda (orn. V-JEPA vs rastgele kodlayici) "A daha iyi"
diyebilmek icin tek ortalama yetmez. Her metrik icin:
  - fark (A - B)
  - hasta duzeyinde bootstrap %95 guven araligi (hastalar yeniden orneklenir)
  - Wilcoxon isaretli sira testi (vaka bazli metrikler icin)

Lezyon duyarliligi ve hasta duzeyi AUC icin de ayni hasta-kume bootstrap'i
kullanilir; boylece cok lezyonlu hastalar guven araligini yapay daraltmaz.

Kullanim:
  python 16_kol_karsilastir.py --a ~/Liver/cikti22/kol_a_vjepa --b ~/Liver/cikti22/kol_b_rastgele \
      --setler ic lits ircad --hedef ~/Liver/cikti22/A_vs_B.md
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon

sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module  # noqa: E402

auc = import_module("04_degerlendir").auc     # degerlendirmeyle BIREBIR ayni AUC

TEKRAR = 10000


def yukle(kol: Path, s: str):
    m = kol / f"metrik_{s}"
    return pd.read_csv(m / "vaka_bazli.csv"), pd.read_csv(m / "lezyon_bazli.csv")


def hizli_auc(skor, y):
    """Mann-Whitney AUC; 04_degerlendir.auc ile ayni tanim (esitlikler ortalama sirayla)."""
    r = rankdata(skor)
    n1 = y.sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))


def karsilastir(va, la, vb, lb, rng):
    v = va.merge(vb, on="vaka", suffixes=("_a", "_b"))
    assert len(v) == len(va) == len(vb), "iki kolun vaka listesi ayni degil"
    assert (v.gt_pozitif_a == v.gt_pozitif_b).all()
    l = la.merge(lb, on=["vaka", "lezyon"], suffixes=("_a", "_b"))
    assert len(l) == len(la) == len(lb), "iki kolun lezyon listesi ayni degil"

    satirlar = []
    t = v[v.gt_pozitif_a].set_index("vaka")

    def vaka_metrigi(ad, sutun, kume, yuksek_iyi=True):
        a, b = kume[f"{sutun}_a"], kume[f"{sutun}_b"]
        ok = a.notna() & b.notna() & np.isfinite(a) & np.isfinite(b)
        a, b = a[ok], b[ok]
        fark = a - b
        f = fark.to_numpy()
        ornek = rng.integers(0, len(f), (TEKRAR, len(f)))
        ga = np.percentile(f[ornek].mean(axis=1), [2.5, 97.5])
        p = wilcoxon(a, b).pvalue if (fark != 0).any() else 1.0
        satirlar.append(dict(metrik=ad, n=int(ok.sum()), A=a.mean(), B=b.mean(), fark=fark.mean(),
                             ga_alt=ga[0], ga_ust=ga[1], p=p, yuksek_iyi=yuksek_iyi))

    vaka_metrigi("Tumor Dice (tumorlu vakalar)", "dice_tumor", t)
    vaka_metrigi("Tumor HD95 mm (tumorlu vakalar)", "hd95_tumor", t, yuksek_iyi=False)
    vi = v.set_index("vaka")
    vaka_metrigi("Karaciger Dice", "dice_karaciger", vi)
    vaka_metrigi("Yanlis pozitif / hasta", "yanlis_pozitif", vi, yuksek_iyi=False)

    # Lezyon duyarliligi: hasta-kume bootstrap
    hs = l.groupby("vaka").agg(n=("lezyon", "size"), a=("bulundu_a", "sum"), b=("bulundu_b", "sum"))
    n_, a_, b_ = hs.n.to_numpy(), hs.a.to_numpy(), hs.b.to_numpy()
    ornek = rng.integers(0, len(hs), (TEKRAR, len(hs)))
    ga = np.percentile((a_[ornek].sum(1) - b_[ornek].sum(1)) / n_[ornek].sum(1), [2.5, 97.5])
    ab = l.bulundu_a & ~l.bulundu_b
    ba = ~l.bulundu_a & l.bulundu_b
    satirlar.append(dict(metrik="Lezyon duyarliligi", n=len(l), A=l.bulundu_a.mean(),
                         B=l.bulundu_b.mean(), fark=l.bulundu_a.mean() - l.bulundu_b.mean(),
                         ga_alt=ga[0], ga_ust=ga[1], p=np.nan, yuksek_iyi=True,
                         not_=f"yalniz A buldu {int(ab.sum())}, yalniz B buldu {int(ba.sum())}"))

    # Hasta duzeyi AUC (skor = tahmin edilen tumor hacmi, 04 ile ayni)
    if (~v.gt_pozitif_a).any():
        y = vi.gt_pozitif_a.to_numpy()
        sa, sb = vi.tahmin_tumor_hacmi_cm3_a.to_numpy(), vi.tahmin_tumor_hacmi_cm3_b.to_numpy()
        aa, bb = auc(sa, y), auc(sb, y)
        assert abs(hizli_auc(sa, y) - aa) < 1e-4 and abs(hizli_auc(sb, y) - bb) < 1e-4, \
            "hizli AUC 04_degerlendir ile uyusmuyor"
        farklar = []
        for o in rng.integers(0, len(y), (TEKRAR, len(y))):
            if 0 < y[o].sum() < len(o):
                farklar.append(hizli_auc(sa[o], y[o]) - hizli_auc(sb[o], y[o]))
        ga = np.percentile(farklar, [2.5, 97.5])
        satirlar.append(dict(metrik="Hasta duzeyi AUC", n=len(vi), A=aa, B=bb, fark=aa - bb,
                             ga_alt=ga[0], ga_ust=ga[1], p=np.nan, yuksek_iyi=True))
    return pd.DataFrame(satirlar)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--setler", nargs="+", default=["ic", "lits", "ircad"])
    p.add_argument("--hedef")
    p.add_argument("--tohum", type=int, default=0)
    a = p.parse_args()

    rng = np.random.default_rng(a.tohum)
    ka, kb = Path(a.a), Path(a.b)
    parcalar = [f"# {ka.name} (A) vs {kb.name} (B)", "",
                f"Eslestirilmis karsilastirma; %95 GA = hasta duzeyinde bootstrap ({TEKRAR} tekrar); "
                "p = Wilcoxon isaretli sira testi. GA sifiri icermiyorsa fark anlamli.", ""]
    for s in a.setler:
        if not (ka / f"metrik_{s}").exists() or not (kb / f"metrik_{s}").exists():
            parcalar += [f"## {s}: metrik yok, atlandi", ""]
            continue
        d = karsilastir(*yukle(ka, s), *yukle(kb, s), rng)
        parcalar += [f"## {s}", "", "| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |",
                     "|---|---|---|---|---|---|---|---|"]
        for r in d.itertuples():
            anlamli = r.ga_alt > 0 or r.ga_ust < 0
            iyi = (r.fark > 0) == r.yuksek_iyi
            etiket = ("evet, A iyi" if iyi else "evet, B iyi") if anlamli else "hayir"
            pm = "—" if not np.isfinite(r.p) else (f"{r.p:.2g}" if r.p >= 1e-4 else "<0.0001")
            parcalar.append(f"| {r.metrik} | {r.n} | {r.A:.3f} | {r.B:.3f} | {r.fark:+.3f} | "
                            f"{r.ga_alt:+.3f} … {r.ga_ust:+.3f} | {pm} | {etiket} |")
        notlar = d[d.get("not_", pd.Series(dtype=str)).notna()] if "not_" in d else []
        for r in getattr(notlar, "itertuples", lambda: [])():
            parcalar.append(f"\n{r.metrik}: {r.not_}")
        parcalar.append("")
    metin = "\n".join(parcalar)
    print(metin)
    if a.hedef:
        Path(a.hedef).write_text(metin)
        print(f"\nYazildi: {a.hedef}")


if __name__ == "__main__":
    main()
