#!/usr/bin/env python3
"""Kaggle icin kucultulmus veri seti uretir.

Kaggle'da disk dar (~20 GB kalici) ve oturum 9 saat. Tam cozunurlukte 500 vaka
sigmaz. Bu betik her vakayi:
  1. karaciger maskesinin cevresine kirpar (kenar payiyla),
  2. sabit voksel araligina yeniden orneklendirir (varsayilan 2 x 2 x 3 mm),
  3. HU'yu int16 olarak .npz icinde saklar
-> vaka basina ~15-25 MB. 500 vaka ~ 10 GB.

Ciktiyi Kaggle Dataset olarak yukleyip her oturumda hazir kullanabilirsin.

Kullanim:
  python 06_kaggle_hazirla.py --raw /mnt/veri/nnUNet_raw --cikti /mnt/veri/kaggle \
      --envanter /mnt/veri/nnUNet_raw/Dataset001_LiverTumor/envanter.csv --dogrulama-orani 0.15
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
KENAR_MM = 20.0      # karaciger sinirinin disinda birakilacak pay


def vakayi_hazirla(args):
    vid, bolum, raw, cikti, hedef_aralik, kirp = args
    kok = Path(raw) / VERI_SETI
    alt = "Tr" if bolum in ("train", "val") else "Ts"
    ct_p = kok / f"images{alt}" / f"LIVER_{vid[6:]}_0000.nii.gz"
    et_p = kok / f"labels{alt}" / f"LIVER_{vid[6:]}.nii.gz"
    try:
        ct_im = nib.load(ct_p)
        ct = np.asanyarray(ct_im.dataobj).astype(np.float32)
        et = np.asanyarray(nib.load(et_p).dataobj).astype(np.uint8)
        aralik = np.abs(np.diag(ct_im.affine)[:3]).astype(np.float32)

        if kirp and (et >= 1).any():
            koord = np.argwhere(et >= 1)
            alt_k = np.maximum(koord.min(0) - (KENAR_MM / aralik).astype(int), 0)
            ust_k = np.minimum(koord.max(0) + 1 + (KENAR_MM / aralik).astype(int), et.shape)
            dilim = tuple(slice(int(a), int(b)) for a, b in zip(alt_k, ust_k))
            ct, et = ct[dilim], et[dilim]

        olcek = aralik / np.asarray(hedef_aralik, dtype=np.float32)
        if not np.allclose(olcek, 1.0, atol=0.02):
            ct = ndimage.zoom(ct, olcek, order=1)                      # dogrusal
            et = ndimage.zoom(et, olcek, order=0).astype(np.uint8)     # en yakin komsu
        ct = np.clip(ct, -1024, 3071).astype(np.int16)

        affine = np.eye(4, dtype=np.float32)
        affine[:3, :3] = np.diag(hedef_aralik)
        hedef = Path(cikti) / bolum
        hedef.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(hedef / f"LIVER_{vid[6:]}.npz", ct=ct, etiket=et,
                            aralik=np.asarray(hedef_aralik, dtype=np.float32), affine=affine)
        mb = (hedef / f"LIVER_{vid[6:]}.npz").stat().st_size / 1e6
        return dict(bdmap_id=vid, bolum=bolum, shape=str(ct.shape), mb=round(mb, 1),
                    tumor_voksel=int((et == 2).sum()), hata="")
    except Exception as e:  # noqa: BLE001
        return dict(bdmap_id=vid, bolum=bolum, shape="", mb=0.0, tumor_voksel=0,
                    hata=f"{type(e).__name__}: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True)
    p.add_argument("--cikti", required=True)
    p.add_argument("--envanter", default=None, help="03_kalite_kontrol.py ciktisi; yoksa donusum raporu kullanilir")
    p.add_argument("--aralik", type=float, nargs=3, default=[2.0, 2.0, 3.0])
    p.add_argument("--vaka-siniri", type=int, default=500, help="toplam vaka sayisi ustu")
    p.add_argument("--dogrulama-orani", type=float, default=0.15)
    p.add_argument("--kirpma", action="store_true", default=True)
    p.add_argument("--isler", type=int, default=os.cpu_count() or 8)
    a = p.parse_args()

    kok = Path(a.raw) / VERI_SETI
    kaynak = Path(a.envanter) if a.envanter else kok / "donusum_raporu.csv"
    df = pd.read_csv(kaynak)
    if "durum" in df:
        df = df[df.durum != "dislandi"]
    df = df.rename(columns={"split": "bolum"})

    # Tumorlu vakalarin hepsini al, tumorsuzlerden dengeleyecek kadar ekle.
    if "tumor_voksel" in df:
        df["tumor"] = df.tumor_voksel > 0
    else:
        df["tumor"] = df.get("lezyon_sayisi", 0) > 0
    secilen = []
    for bolum, grup in df.groupby("bolum"):
        pay = int(a.vaka_siniri * len(grup) / len(df))
        tumorlu = grup[grup.tumor]
        tumorsuz = grup[~grup.tumor].sample(
            min(len(grup[~grup.tumor]), max(0, pay - len(tumorlu))), random_state=0)
        secilen.append(pd.concat([tumorlu.head(pay), tumorsuz]))
    sec = pd.concat(secilen)

    # Egitim bolumunun bir kismi dogrulamaya ayrilir (hasta duzeyinde).
    egitim = sec[sec.bolum == "train"].sample(frac=1.0, random_state=0)
    n_dog = int(len(egitim) * a.dogrulama_orani)
    bolumler = {}
    for i, vid in enumerate(egitim.bdmap_id):
        bolumler[vid] = "val" if i < n_dog else "train"
    for vid in sec[sec.bolum == "test"].bdmap_id:
        bolumler[vid] = "test"

    isler = [(vid, bolumler[vid], a.raw, a.cikti, a.aralik, a.kirpma) for vid in sec.bdmap_id]
    print(f"{len(isler)} vaka hazirlaniyor -> {a.cikti} (aralik {a.aralik} mm)")

    sonuclar = []
    with ProcessPoolExecutor(max_workers=a.isler) as havuz:
        gelecekler = [havuz.submit(vakayi_hazirla, i) for i in isler]
        for n, f in enumerate(as_completed(gelecekler), 1):
            sonuclar.append(f.result())
            if n % 50 == 0:
                print(f"  {n}/{len(isler)}", flush=True)

    rapor = pd.DataFrame(sonuclar)
    rapor.to_csv(Path(a.cikti) / "kaggle_rapor.csv", index=False)
    basarili = rapor[rapor.hata == ""]
    print("\n--- Ozet ---")
    print(basarili.groupby("bolum").agg(vaka=("bdmap_id", "size"), toplam_mb=("mb", "sum"),
                                        tumorlu=("tumor_voksel", lambda s: int((s > 0).sum()))).to_string())
    print(f"\nToplam boyut: {basarili.mb.sum()/1000:.1f} GB")
    if (rapor.hata != "").any():
        print(rapor[rapor.hata != ""][["bdmap_id", "hata"]].head().to_string(index=False))


if __name__ == "__main__":
    main()
