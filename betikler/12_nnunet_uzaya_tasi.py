#!/usr/bin/env python3
"""nnU-Net tahminlerini JEPA kollarinin degerlendirme uzayina tasir.

nnU-Net orijinal cozunurlukte calisir; JEPA kollari ise karaciger cevresine
kirpilmis, 1.5 x 1.5 x 2.0 mm'ye orneklenmis hacimlerde. Ayni metriklerle
karsilastirmak icin nnU-Net tahminleri de ayni kirpma + ornekleme islemine
sokulur. Islem 06_kaggle_hazirla.py ile BIREBIR AYNI kuralla yapilir; kirpma
kutusu gercek etiketten hesaplanir, boylece iki kol da ayni bolgeyi gorur.

Kullanim:
  python 12_nnunet_uzaya_tasi.py --tahmin ~/Liver/cikti/kol_c_nnunet/tahmin_ic_ham \
      --raw ~/veri/nnUNet_raw --npz ~/veri/veri15/test \
      --cikti ~/Liver/cikti/kol_c_nnunet/tahmin_ic
"""
import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage

VERI_SETI = "Dataset001_LiverTumor"
KENAR_MM = 20.0          # 06_kaggle_hazirla.py ile ayni


def voksel_araligi(affine) -> np.ndarray:
    return np.linalg.norm(np.asarray(affine)[:3, :3], axis=0)


def vakayi_tasi(args):
    ad, tahmin_p, gt_p, npz_p, cikti = args
    try:
        gt_im = nib.load(gt_p)
        gt = np.asanyarray(gt_im.dataobj).astype(np.uint8)
        pr = np.asanyarray(nib.load(tahmin_p).dataobj).astype(np.uint8)
        if pr.shape != gt.shape:
            raise ValueError(f"tahmin {pr.shape} ile etiket {gt.shape} ayni degil")
        aralik = voksel_araligi(gt_im.affine).astype(np.float32)

        hedef = np.load(npz_p)
        hedef_aralik = hedef["aralik"].astype(np.float32)
        hedef_bicim = hedef["etiket"].shape

        if (gt >= 1).any():                      # 06 ile ayni kirpma
            koord = np.argwhere(gt >= 1)
            alt = np.maximum(koord.min(0) - (KENAR_MM / aralik).astype(int), 0)
            ust = np.minimum(koord.max(0) + 1 + (KENAR_MM / aralik).astype(int), gt.shape)
            pr = pr[tuple(slice(int(a), int(b)) for a, b in zip(alt, ust))]

        olcek = aralik / hedef_aralik
        if not np.allclose(olcek, 1.0, atol=0.02):
            pr = ndimage.zoom(pr, olcek, order=0).astype(np.uint8)

        # Yuvarlamadan kaynakli 1-2 vokselluk farki hedef bicime oturt
        if pr.shape != hedef_bicim:
            yeni = np.zeros(hedef_bicim, dtype=np.uint8)
            kes = tuple(slice(0, min(a, b)) for a, b in zip(pr.shape, hedef_bicim))
            yeni[kes] = pr[kes]
            pr = yeni

        affine = np.eye(4, dtype=np.float32)
        affine[:3, :3] = np.diag(hedef_aralik)
        Path(cikti).mkdir(parents=True, exist_ok=True)
        nib.save(nib.Nifti1Image(pr, affine), Path(cikti) / f"{ad}.nii.gz")
        return dict(vaka=ad, bicim=str(pr.shape), hata="")
    except Exception as e:  # noqa: BLE001
        return dict(vaka=ad, bicim="", hata=f"{type(e).__name__}: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tahmin", required=True, help="nnU-Net tahminleri (orijinal uzay)")
    p.add_argument("--raw", required=True, help="nnUNet_raw dizini (gercek etiketler icin)")
    p.add_argument("--npz", required=True, help="hedef uzaydaki .npz vakalari")
    p.add_argument("--cikti", required=True)
    p.add_argument("--alt", default="Ts", help="labelsTr mi labelsTs mi")
    p.add_argument("--isler", type=int, default=os.cpu_count() or 8)
    a = p.parse_args()

    etiket_k = Path(a.raw) / VERI_SETI / f"labels{a.alt}"
    isler = []
    for npz_p in sorted(Path(a.npz).glob("*.npz")):
        ad = npz_p.stem
        tahmin_p, gt_p = Path(a.tahmin) / f"{ad}.nii.gz", etiket_k / f"{ad}.nii.gz"
        if tahmin_p.exists() and gt_p.exists():
            isler.append((ad, str(tahmin_p), str(gt_p), str(npz_p), a.cikti))
        else:
            print(f"UYARI: eksik dosya -> {ad}")
    print(f"{len(isler)} tahmin tasiniyor -> {a.cikti}")

    sonuclar = []
    with ProcessPoolExecutor(max_workers=a.isler) as havuz:
        for f in as_completed([havuz.submit(vakayi_tasi, i) for i in isler]):
            sonuclar.append(f.result())
    hatalar = [s for s in sonuclar if s["hata"]]
    print(f"tamam: {len(sonuclar)-len(hatalar)} | hata: {len(hatalar)}")
    for h in hatalar[:5]:
        print(" ", h["vaka"], h["hata"])


if __name__ == "__main__":
    main()
