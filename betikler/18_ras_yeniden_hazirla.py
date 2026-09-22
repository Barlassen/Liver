#!/usr/bin/env python3
"""Mevcut bolunmeyi AYNEN koruyarak veriyi kanonik RAS yonunde yeniden uretir.

Sorun: AbdomenAtlas goruntuleri farkli yonlerde (egitimde RAS %45, LAS %25,
LPS %20, IPL %8, LAI %2). Hat ucuncu ekseni hep "eksenel kesit" varsayiyordu;
IPL vakalarda bu aslinda sagital kesit, LPS vakalarda goruntu bas asagi.

Cozum: goruntu ve etiket nib.as_closest_canonical ile RAS'a cevrilir
(yalniz eksen permutasyonu + ayna; yeniden ornekleme yok), sonra
06_kaggle_hazirla.py ile BIREBIR ayni kirpma ve yeniden ornekleme uygulanir.

Bolunme yeniden hesaplanmaz: --eski klasorundeki train/val/test dosya adlari
okunur, her vaka ayni bolume yazilir.

Kullanim:
  python betikler/18_ras_yeniden_hazirla.py --eski ~/veri/veri22 --raw ~/veri/nnUNet_raw22 \
      --cikti ~/veri/veri22ras --aralik 1.5 1.5 2.0
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
KENAR_MM = 20.0      # 06_kaggle_hazirla.py ile ayni


def voksel_araligi(affine) -> np.ndarray:
    return np.linalg.norm(np.asarray(affine)[:3, :3], axis=0)


def kaynak_bul(kok: Path, no: str):
    for alt in ("Tr", "Ts"):
        ct_p = kok / f"images{alt}" / f"LIVER_{no}_0000.nii.gz"
        et_p = kok / f"labels{alt}" / f"LIVER_{no}.nii.gz"
        if ct_p.exists() and et_p.exists():
            return ct_p, et_p
    raise FileNotFoundError(f"LIVER_{no} ham dosyasi bulunamadi")


def vakayi_hazirla(args):
    no, bolum, raw, cikti, hedef_aralik = args
    try:
        ct_p, et_p = kaynak_bul(Path(raw) / VERI_SETI, no)
        ct_im, et_im = nib.load(ct_p), nib.load(et_p)
        if ct_im.shape != et_im.shape or not np.allclose(ct_im.affine, et_im.affine, atol=1e-3):
            raise ValueError("CT ve etiket ayni izgarada degil")
        yon_once = "".join(nib.aff2axcodes(ct_im.affine))
        ct_im = nib.as_closest_canonical(ct_im)
        et_im = nib.as_closest_canonical(et_im)
        yon_sonra = "".join(nib.aff2axcodes(ct_im.affine))
        if yon_sonra != "RAS":
            raise ValueError(f"kanoniklestirme sonrasi yon {yon_sonra}")

        ct = np.asanyarray(ct_im.dataobj).astype(np.float32)
        et = np.asanyarray(et_im.dataobj).astype(np.uint8)
        aralik = voksel_araligi(ct_im.affine).astype(np.float32)
        if not np.all(aralik > 0):
            raise ValueError(f"gecersiz voksel araligi: {aralik}")

        # --- buradan sonrasi 06_kaggle_hazirla.py ile birebir ayni ---
        if (et >= 1).any():
            koord = np.argwhere(et >= 1)
            alt_k = np.maximum(koord.min(0) - (KENAR_MM / aralik).astype(int), 0)
            ust_k = np.minimum(koord.max(0) + 1 + (KENAR_MM / aralik).astype(int), et.shape)
            dilim = tuple(slice(int(a), int(b)) for a, b in zip(alt_k, ust_k))
            ct, et = ct[dilim], et[dilim]
        olcek = aralik / np.asarray(hedef_aralik, dtype=np.float32)
        if not np.allclose(olcek, 1.0, atol=0.02):
            ct = ndimage.zoom(ct, olcek, order=1)
            et = ndimage.zoom(et, olcek, order=0).astype(np.uint8)
        if min(ct.shape) < 8:
            raise ValueError(f"kirpma sonrasi hacim cok kucuk: {ct.shape}")
        ct = np.clip(ct, -1024, 3071).astype(np.int16)

        affine = np.eye(4, dtype=np.float32)
        affine[:3, :3] = np.diag(hedef_aralik)
        hedef = Path(cikti) / bolum
        hedef.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(hedef / f"LIVER_{no}.npz", ct=ct, etiket=et,
                            aralik=np.asarray(hedef_aralik, dtype=np.float32), affine=affine)
        return dict(vaka=f"LIVER_{no}", bolum=bolum, yon_once=yon_once, shape=str(ct.shape),
                    tumor_voksel=int((et == 2).sum()), hata="")
    except Exception as e:  # noqa: BLE001
        return dict(vaka=f"LIVER_{no}", bolum=bolum, yon_once="", shape="", tumor_voksel=0,
                    hata=f"{type(e).__name__}: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--eski", required=True, help="bolunmesi korunacak mevcut veri klasoru")
    p.add_argument("--raw", required=True)
    p.add_argument("--cikti", required=True)
    p.add_argument("--aralik", type=float, nargs=3, default=[1.5, 1.5, 2.0])
    p.add_argument("--isler", type=int, default=os.cpu_count() or 8)
    a = p.parse_args()

    isler = []
    for bolum in ("train", "val", "test"):
        for f in sorted((Path(a.eski) / bolum).glob("LIVER_*.npz")):
            isler.append((f.stem[6:], bolum, a.raw, a.cikti, a.aralik))
    print(f"{len(isler)} vaka RAS yonunde yeniden hazirlaniyor -> {a.cikti}")

    sonuclar = []
    with ProcessPoolExecutor(max_workers=a.isler) as havuz:
        for n, f in enumerate(as_completed([havuz.submit(vakayi_hazirla, i) for i in isler]), 1):
            sonuclar.append(f.result())
            if n % 200 == 0:
                print(f"  {n}/{len(isler)}", flush=True)

    rapor = pd.DataFrame(sonuclar).sort_values("vaka")
    Path(a.cikti).mkdir(parents=True, exist_ok=True)
    rapor.to_csv(Path(a.cikti) / "ras_rapor.csv", index=False)
    ok = rapor[rapor.hata == ""]
    print("\n--- Ozet ---")
    print(ok.groupby("bolum").size().to_string())
    print("onceki yon dagilimi:", ok.yon_once.value_counts().to_dict())
    if (rapor.hata != "").any():
        print(f"HATA: {int((rapor.hata != '').sum())} vaka")
        print(rapor[rapor.hata != ""][["vaka", "hata"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
