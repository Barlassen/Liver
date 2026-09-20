#!/usr/bin/env python3
"""Donusturulmus veri icin kalite kontrol envanteri uretir.

Yaptigi kontroller:
  1. Dosya okunabiliyor mu, NaN var mi
  2. Etiket degerleri beklenen kumede mi (0/1/2)
  3. Maskeden hesaplanan karaciger hacmi ve lezyon sayisi metadata ile tutuyor mu
     (donusum hatalarini yakalayan en degerli kontrol)
  4. HU araligi, voksel araligi, gorus alani makul mu
  5. Ayni goruntunun veri setinde birden fazla kez bulunmasi (kopya vaka).
     AbdomenAtlas 17 acik veri setinin birlesimi oldugu icin ayni hasta iki ayri
     BDMAP ID ile bulunabilir. Biri egitimde digeri testte kalirsa skorlar siser.

Hicbir dosya silinmez; her vaka "uygun" / "incelenecek" / "dislandi" olarak isaretlenir.

Kullanim:
  python 03_kalite_kontrol.py --raw /mnt/veri/nnUNet_raw --meta /mnt/veri/ham/AbdomenAtlas3.0MiniWithMeta.csv
"""
import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage

VERI_SETI = "Dataset001_LiverTumor"
KUCUK = 16  # kopya tespiti icin kucultulmus hacim kenar uzunlugu


def kucult(hacim: np.ndarray, k: int = KUCUK) -> np.ndarray:
    """Hacmi k x k x k boyutuna indirger (kopya karsilastirmasi icin parmak izi)."""
    adim = [max(1, s // k) for s in hacim.shape]
    kirpik = hacim[::adim[0], ::adim[1], ::adim[2]]
    zoom = [k / s for s in kirpik.shape]
    return ndimage.zoom(kirpik.astype(np.float32), zoom, order=1)[:k, :k, :k]


def vakayi_incele(args):
    vid, split, raw = args
    kok = Path(raw) / VERI_SETI
    alt = "Tr" if split == "train" else "Ts"
    goruntu = kok / f"images{alt}" / f"LIVER_{vid[6:]}_0000.nii.gz"
    etiket_p = kok / f"labels{alt}" / f"LIVER_{vid[6:]}.nii.gz"
    s = dict(bdmap_id=vid, split=split, bayraklar=[])
    try:
        et_im = nib.load(etiket_p)
        et = np.asanyarray(et_im.dataobj)
        voksel_cm3 = abs(np.linalg.det(et_im.affine[:3, :3])) / 1000.0
        aralik = np.abs(np.diag(et_im.affine)[:3])

        degerler = set(np.unique(et).tolist())
        if not degerler <= {0, 1, 2}:
            s["bayraklar"].append(f"beklenmeyen_etiket:{sorted(degerler)}")

        s["karaciger_hacmi_cm3"] = round(float((et >= 1).sum() * voksel_cm3), 1)
        tumor = et == 2
        s["tumor_hacmi_cm3"] = round(float(tumor.sum() * voksel_cm3), 2)
        lab, n = ndimage.label(tumor, structure=np.ones((3, 3, 3)))
        s["lezyon_sayisi"] = int(n)
        if n:
            boyutlar = np.bincount(lab.ravel())[1:]
            en_buyuk = int(np.argmax(boyutlar)) + 1
            koord = np.argwhere(lab == en_buyuk)
            uzanim = (koord.max(0) - koord.min(0) + 1) * aralik
            s["en_buyuk_cap_cm"] = round(float(uzanim.max() / 10), 2)
        else:
            s["en_buyuk_cap_cm"] = 0.0

        s["z_araligi_mm"] = round(float(aralik[2]), 2)
        s["shape"] = str(et_im.shape)
        if s["karaciger_hacmi_cm3"] < 300:
            s["bayraklar"].append("karaciger_kucuk_veya_bos")

        ct_im = nib.load(goruntu)
        ct = np.asanyarray(ct_im.dataobj, dtype=np.float32)
        if ct_im.shape != et_im.shape:
            s["bayraklar"].append("ct_etiket_boyut_farki")
        if not np.isfinite(ct).all():
            s["bayraklar"].append("nan_veya_inf")
        p1, p99 = np.percentile(ct, [1, 99])
        s["hu_p1"], s["hu_p99"] = round(float(p1), 1), round(float(p99), 1)
        if p1 > -200 or p99 > 4000 or p99 < 100:
            s["bayraklar"].append("hu_araligi_supheli")
        if et.sum() > 0:
            kc_hu = float(np.median(ct[et == 1])) if (et == 1).any() else float("nan")
            s["karaciger_medyan_hu"] = round(kc_hu, 1)
            if not (-20 < kc_hu < 200):
                s["bayraklar"].append("karaciger_hu_supheli")
        s["parmak_izi"] = kucult(ct).ravel()
        s["durum"] = "uygun"
    except Exception as e:  # noqa: BLE001
        s["durum"] = "dislandi"
        s["bayraklar"].append(f"okunamadi:{type(e).__name__}")
        s["parmak_izi"] = None
    s["bayraklar"] = ";".join(s["bayraklar"])
    return s


def kopyalari_bul(izler: dict, esik: float = 0.9995):
    """Kosinus benzerligi esigi asan vaka ciftlerini gruplar."""
    idler = [k for k, v in izler.items() if v is not None]
    if len(idler) < 2:
        return {}
    M = np.stack([izler[i] for i in idler])
    M = M - M.mean(1, keepdims=True)
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-8
    benzerlik = M @ M.T
    np.fill_diagonal(benzerlik, 0)

    ebeveyn = {i: i for i in range(len(idler))}

    def bul(x):
        while ebeveyn[x] != x:
            ebeveyn[x] = ebeveyn[ebeveyn[x]]
            x = ebeveyn[x]
        return x

    for i, j in zip(*np.where(np.triu(benzerlik > esik))):
        a, b = bul(int(i)), bul(int(j))
        if a != b:
            ebeveyn[a] = b

    gruplar = {}
    for i, vid in enumerate(idler):
        gruplar.setdefault(bul(i), []).append(vid)
    return {vid: f"G{no}" for no, uyeler in enumerate(
        [u for u in gruplar.values() if len(u) > 1], 1) for vid in uyeler}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True)
    p.add_argument("--meta", required=True)
    p.add_argument("--isler", type=int, default=os.cpu_count() or 8)
    p.add_argument("--cikti", default=None)
    a = p.parse_args()

    kok = Path(a.raw) / VERI_SETI
    rapor = pd.read_csv(kok / "donusum_raporu.csv")
    uygun = rapor[rapor.durum == "uygun"]
    print(f"{len(uygun)} vaka inceleniyor")

    sonuclar = []
    with ProcessPoolExecutor(max_workers=a.isler) as havuz:
        gelecekler = [havuz.submit(vakayi_incele, (r.bdmap_id, r.split, a.raw))
                      for r in uygun.itertuples()]
        for n, f in enumerate(as_completed(gelecekler), 1):
            sonuclar.append(f.result())
            if n % 50 == 0:
                print(f"  {n}/{len(uygun)}", flush=True)

    izler = {s["bdmap_id"]: s.pop("parmak_izi") for s in sonuclar}
    env = pd.DataFrame(sonuclar)

    # --- metadata ile karsilastirma -----------------------------------------
    meta = pd.read_csv(a.meta).rename(columns={"BDMAP ID": "bdmap_id"})
    m = meta[["bdmap_id", "liver volume (cm^3)", "number of liver lesion instances",
              "largest liver lesion diameter (cm)", "contrast", "sex", "age"]]
    env = env.merge(m, on="bdmap_id", how="left")
    env["meta_tumor_var"] = env["number of liver lesion instances"] > 0
    env["olculen_tumor_var"] = env["lezyon_sayisi"] > 0
    env["hacim_fark_yuzde"] = (
        (env["karaciger_hacmi_cm3"] - env["liver volume (cm^3)"]).abs()
        / env["liver volume (cm^3)"].replace(0, np.nan) * 100).round(1)

    def ek_bayrak(r):
        b = [r.bayraklar] if r.bayraklar else []
        if r.meta_tumor_var != r.olculen_tumor_var:
            b.append("tumor_metadata_uyusmazligi")
        if pd.notna(r.hacim_fark_yuzde) and r.hacim_fark_yuzde > 20:
            b.append("karaciger_hacmi_uyusmuyor")
        return ";".join(b)

    env["bayraklar"] = env.apply(ek_bayrak, axis=1)

    # --- kopya vakalar -------------------------------------------------------
    gruplar = kopyalari_bul(izler)
    env["kopya_grubu"] = env.bdmap_id.map(gruplar).fillna("")
    # Ayni kopya grubu hem egitimde hem testte ise sizinti riski var.
    riskli = {g for g, alt in env[env.kopya_grubu != ""].groupby("kopya_grubu").split
              .apply(set).items() if len(alt) > 1}
    env.loc[env.kopya_grubu.isin(riskli), "bayraklar"] += ";kopya_train_test_arasi"

    kritik = ["okunamadi", "beklenmeyen_etiket", "ct_etiket_boyut_farki", "nan_veya_inf"]
    env.loc[env.bayraklar.str.contains("|".join(kritik), na=False), "durum"] = "dislandi"
    env.loc[(env.durum == "uygun") & (env.bayraklar != ""), "durum"] = "incelenecek"

    cikti = Path(a.cikti) if a.cikti else kok / "envanter.csv"
    sutunlar = ["bdmap_id", "split", "durum", "bayraklar", "kopya_grubu",
                "karaciger_hacmi_cm3", "liver volume (cm^3)", "hacim_fark_yuzde",
                "lezyon_sayisi", "number of liver lesion instances",
                "en_buyuk_cap_cm", "largest liver lesion diameter (cm)",
                "tumor_hacmi_cm3", "karaciger_medyan_hu", "hu_p1", "hu_p99",
                "z_araligi_mm", "shape", "contrast", "sex", "age"]
    env[[c for c in sutunlar if c in env.columns]].sort_values("bdmap_id").to_csv(cikti, index=False)

    print("\n--- Ozet ---")
    print(env.groupby(["split", "durum"]).size().to_string())
    print("\nEn sik bayraklar:")
    tum = env.bayraklar.str.split(";").explode()
    print(tum[tum != ""].value_counts().head(10).to_string())
    print(f"\nKopya grubu sayisi: {len(set(gruplar.values()))} "
          f"({len(gruplar)} vaka), train/test arasi riskli grup: {len(riskli)}")
    print(f"Envanter: {cikti}")


if __name__ == "__main__":
    main()
