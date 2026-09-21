#!/usr/bin/env python3
"""Lezyon duyarliligi neden dusuk? Kacirilan lezyonlarin dokumu + medyanlar.

04_degerlendir.py ciktilarini (vaka_bazli.csv, lezyon_bazli.csv) okur; istenirse
maskelerden her lezyonun ortusme oranini yeniden hesaplar (--maske).

Kullanim:
  python 14_duyarlilik_analizi.py --metrik ~/Liver/cikti/kol_a_vjepa/metrik_ic
  python 14_duyarlilik_analizi.py --metrik ... --gt ~/veri/veri15/test \
      --tahmin ~/Liver/cikti/kol_a_vjepa/tahmin_ic
"""
import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
BAGLANTI = np.ones((3, 3, 3))


def ceyrek(s):
    s = pd.Series(s).dropna()
    return f"ort {s.mean():.3f} | medyan {s.median():.3f} | IQR {s.quantile(.25):.3f}-{s.quantile(.75):.3f}"


def ortusmeler(args):
    """Her gercek lezyon icin: ortusme orani ve en yakin tahmine uzaklik (mm)."""
    gt_p, pr_p = args
    from importlib import import_module
    d = import_module("04_degerlendir")
    gt, aralik = d.etiket_yukle(Path(gt_p))
    pr, _ = d.etiket_yukle(Path(pr_p))
    gt_t, pr_t = gt == 2, pr == 2
    lab, n = ndimage.label(gt_t, structure=BAGLANTI)
    uzak = ndimage.distance_transform_edt(~pr_t, sampling=aralik) if pr_t.any() else None
    kayit = []
    for i in range(1, n + 1):
        m = lab == i
        kayit.append(dict(vaka=Path(gt_p).name.split(".")[0], lezyon=i,
                          ortusme=float(pr_t[m].mean()),
                          uzaklik_mm=float(uzak[m].min()) if uzak is not None else np.inf,
                          kc_icinde=float((pr[m] >= 1).mean())))
    return kayit


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--metrik", required=True)
    p.add_argument("--gt")
    p.add_argument("--tahmin")
    p.add_argument("--isler", type=int, default=min(8, os.cpu_count() or 4))
    a = p.parse_args()

    vaka = pd.read_csv(Path(a.metrik) / "vaka_bazli.csv")
    lez = pd.read_csv(Path(a.metrik) / "lezyon_bazli.csv")
    t = vaka[vaka.gt_pozitif]

    print(f"### {a.metrik}")
    print(f"tumorlu vaka {len(t)} | lezyon {len(lez)}")
    print(f"tumor Dice (tumorlu vakalar) : {ceyrek(t.dice_tumor)}")
    print(f"karaciger Dice (tum vakalar) : {ceyrek(vaka.dice_karaciger)}")
    print(f"tumor HD95 mm                : {ceyrek(t.hd95_tumor.replace(np.inf, np.nan))}")
    print(f"Dice = 0 olan tumorlu vaka   : {(t.dice_tumor == 0).sum()} / {len(t)}")
    print(f"hic tumor tahmin edilmeyen   : {(t.tahmin_tumor_hacmi_cm3 == 0).sum()} / {len(t)}")
    oran = (t.tahmin_tumor_hacmi_cm3 / t.gt_tumor_hacmi_cm3)
    print(f"tahmin/gercek tumor hacmi    : medyan {oran.median():.2f} "
          f"(<1 = eksik boyuyor) | eksik boyanan vaka {(oran < 1).mean():.0%}")

    # Hasta basina duyarlilik: birkac cok-lezyonlu hasta ortalamayi bozuyor mu?
    hb = lez.groupby("vaka").bulundu.agg(["mean", "size"])
    print(f"hasta basina lezyon duyarliligi: {ceyrek(hb['mean'])}")
    cok = hb[hb["size"] > 10]
    print(f"  >10 lezyonlu hasta: {len(cok)} hasta, {int(cok['size'].sum())} lezyon "
          f"(tum lezyonlarin %{100*cok['size'].sum()/len(lez):.0f}'i), "
          f"duyarlilik {lez[lez.vaka.isin(cok.index)].bulundu.mean():.3f}")
    geri = lez[~lez.vaka.isin(cok.index)]
    print(f"  bu hastalar haric duyarlilik: {geri.bulundu.mean():.3f} ({len(geri)} lezyon)")

    # Kacirilan lezyonlarin boyutu
    kac = lez[~lez.bulundu]
    print(f"kacirilan lezyon: {len(kac)} | cap medyani {kac.cap_mm.median():.1f} mm "
          f"(bulunan: {lez[lez.bulundu].cap_mm.median():.1f} mm)")
    for esik in (5, 10):
        k = lez.cap_mm < esik
        print(f"  cap < {esik} mm: {k.sum()} lezyon (%{100*k.mean():.0f}), "
              f"duyarlilik {lez[k].bulundu.mean():.3f}; bunlar haric {lez[~k].bulundu.mean():.3f}")

    if a.gt and a.tahmin:
        isler = []
        for pr in sorted(Path(a.tahmin).glob("*.nii.gz")):
            ad = pr.name[:-7]
            for uz in (".npz", ".nii.gz"):
                g = Path(a.gt) / f"{ad}{uz}"
                if g.exists():
                    isler.append((str(g), str(pr)))
                    break
        with ProcessPoolExecutor(a.isler) as h:
            o = pd.DataFrame([r for rr in h.map(ortusmeler, isler) for r in rr])
        o = o.merge(lez, on=["vaka", "lezyon"])
        k = o[~o.bulundu]
        print(f"\nKacirilan {len(k)} lezyonun dokumu (maskeden):")
        print(f"  hic dokunulmamis (ortusme 0)     : {(k.ortusme == 0).mean():.0%}")
        print(f"  kismen dokunulmus (0 < o < %10)  : {((k.ortusme > 0) & (k.ortusme < .1)).mean():.0%}")
        print(f"  en yakin tahmin <= 5 mm          : {(k.uzaklik_mm <= 5).mean():.0%}")
        print(f"  lezyonun karaciger sanildigi oran: medyan {k.kc_icinde.median():.2f} "
              f"(1 = model orayi karaciger diye boyamis)")
        print(f"  herhangi bir ortusmeyle duyarlilik: {(o.ortusme > 0).mean():.3f} "
              f"(esik %10 ile: {o.bulundu.mean():.3f})")
        for g in ["<1cm", "1-2cm", ">=2cm"]:
            s = o[o.boyut_grubu == g]
            print(f"  {g:6s}: esik %10 {s.bulundu.mean():.2f} | herhangi ortusme {(s.ortusme > 0).mean():.2f} "
                  f"| <=5mm yakin {(s.uzaklik_mm <= 5).mean():.2f}  (n={len(s)})")


if __name__ == "__main__":
    main()
