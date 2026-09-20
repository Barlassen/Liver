#!/usr/bin/env python3
"""Tum kollarin metriklerini tek karsilastirma tablosunda toplar.

Her kol icin cikti/<kol>/metrik_<set>/ozet.json okunur ve abstract'a
dogrudan girebilecek markdown tablolari uretilir.

Kullanim:
  python 10_sonuc_tablosu.py --cikti ~/Liver/cikti --hedef ~/Liver/cikti/SONUCLAR.md
"""
import argparse
import json
from pathlib import Path

import pandas as pd

KOL_ADLARI = {
    "kol_a_vjepa": "V-JEPA 2 (dondurulmus)",
    "kol_d_inceayar": "V-JEPA 2 (son 4 blok ince ayar)",
    "kol_b_rastgele": "Rastgele kodlayici (ablasyon)",
    "kol_c_nnunet": "nnU-Net (baseline)",
}
SET_ADLARI = {"ic": "Ic test (AbdomenAtlas)", "lits": "Harici test (LiTS)"}

SATIRLAR = [
    ("dice_tumor_ort_tumorlu_vakalarda", "Tumor Dice", 3),
    ("dice_karaciger_ort", "Karaciger Dice", 3),
    ("hd95_tumor_ort_mm", "Tumor HD95 (mm)", 1),
    ("hd95_karaciger_ort_mm", "Karaciger HD95 (mm)", 1),
    ("lezyon_duyarliligi", "Lezyon duyarliligi", 3),
    ("hasta_basina_yanlis_pozitif", "Hasta basina yanlis pozitif", 2),
    ("hasta_duzeyi_duyarlilik", "Hasta duzeyi duyarlilik", 3),
    ("hasta_duzeyi_ozgulluk", "Hasta duzeyi ozgulluk", 3),
    ("hasta_duzeyi_auc", "Hasta duzeyi AUC", 3),
    ("tumor_hacim_hatasi_ort_yuzde", "Tumor hacim hatasi (%)", 1),
]


def oku(kok: Path):
    kayitlar = {}
    for kol_yolu in sorted(kok.glob("*/metrik_*")):
        kol, set_adi = kol_yolu.parent.name, kol_yolu.name.replace("metrik_", "")
        ozet_p = kol_yolu / "ozet.json"
        if ozet_p.exists():
            kayitlar[(kol, set_adi)] = json.loads(ozet_p.read_text())
    return kayitlar


def tablo(kayitlar, set_adi):
    kollar = [k for (k, s) in kayitlar if s == set_adi]
    kollar.sort(key=lambda k: list(KOL_ADLARI).index(k) if k in KOL_ADLARI else 99)
    if not kollar:
        return None
    ilk = kayitlar[(kollar[0], set_adi)]
    baslik = (f"**{SET_ADLARI.get(set_adi, set_adi)}** — {ilk['vaka_sayisi']} vaka "
              f"({ilk['tumorlu_vaka']} tumorlu, {ilk['tumorsuz_vaka']} tumorsuz)")

    satirlar = ["| Metrik | " + " | ".join(KOL_ADLARI.get(k, k) for k in kollar) + " |",
                "|---" * (len(kollar) + 1) + "|"]
    for anahtar, etiket, basamak in SATIRLAR:
        degerler = []
        for k in kollar:
            v = kayitlar[(k, set_adi)].get(anahtar)
            degerler.append("—" if v is None else f"{v:.{basamak}f}")
        if set(degerler) != {"—"}:
            satirlar.append(f"| {etiket} | " + " | ".join(degerler) + " |")

    # boyuta gore duyarlilik ayri tablo
    boyut = []
    gruplar = ["<1cm", "1-2cm", ">=2cm"]
    for g in gruplar:
        hucreler = []
        for k in kollar:
            d = (kayitlar[(k, set_adi)].get("boyuta_gore_duyarlilik") or {}).get(g)
            hucreler.append("—" if not d else f"{d['duyarlilik']:.3f} (n={d['n']})")
        if set(hucreler) != {"—"}:
            boyut.append(f"| {g} | " + " | ".join(hucreler) + " |")
    if boyut:
        satirlar += ["", "Boyuta gore lezyon duyarliligi:", "",
                     "| Boyut | " + " | ".join(KOL_ADLARI.get(k, k) for k in kollar) + " |",
                     "|---" * (len(kollar) + 1) + "|"] + boyut
    return baslik + "\n\n" + "\n".join(satirlar)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cikti", required=True)
    p.add_argument("--hedef", default=None)
    a = p.parse_args()

    kok = Path(a.cikti)
    kayitlar = oku(kok)
    if not kayitlar:
        raise SystemExit(f"{kok} altinda metrik bulunamadi")

    parcalar = ["# Sonuclar", ""]
    for set_adi in ["ic", "lits"]:
        t = tablo(kayitlar, set_adi)
        if t:
            parcalar += [t, ""]

    # ham degerler, tekrar uretilebilirlik icin
    ham = pd.DataFrame([{**{"kol": k, "set": s}, **v} for (k, s), v in kayitlar.items()])
    ham = ham.drop(columns=[c for c in ham.columns if c == "boyuta_gore_duyarlilik"])
    parcalar += ["## Ham degerler", "", "```", ham.to_string(index=False), "```"]

    metin = "\n".join(parcalar)
    print(metin)
    if a.hedef:
        Path(a.hedef).write_text(metin)
        print(f"\nYazildi: {a.hedef}")


if __name__ == "__main__":
    main()
