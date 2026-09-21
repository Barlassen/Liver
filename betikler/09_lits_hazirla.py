#!/usr/bin/env python3
"""LiTS / MSD Task03'u harici test seti olarak hazirlar.

LiTS etiket duzeni bizimkiyle birebir ayni: 0 = arka plan, 1 = karaciger,
2 = tumor. Donusum gerekmiyor, yalnizca kirpma + yeniden orneklendirme.

Bu vakalar AbdomenAtlas egitim havuzundan dislandi (bkz. 07_lits_eslesme.py),
bu yuzden gercek bir harici dogrulama seti olusturuyorlar -- ustelik etiketleri
uzman cizimi.

Arsiv ~27 GB. Indirme bir kez yapilir; --tar ile yerel dosya da verilebilir.

Kullanim:
  python 09_lits_hazirla.py --cikti /mnt/veri/harici_lits --format npz
  python 09_lits_hazirla.py --tar /mnt/veri/Task03_Liver.tar --cikti /mnt/veri/harici_lits \
      --format nnunet
"""
import argparse
import os
import shutil
import tarfile
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage

TAR_URL = "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task03_Liver.tar"
KENAR_MM = 20.0


def arsivi_indir(hedef: Path) -> Path:
    if hedef.exists():
        print(f"Arsiv zaten var: {hedef}")
        return hedef
    print(f"Indiriliyor (~27 GB): {TAR_URL}")
    try:
        import certifi
        import ssl
        baglam = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        baglam = None
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(TAR_URL, context=baglam) as y, open(hedef, "wb") as f:
        shutil.copyfileobj(y, f, length=8 << 20)
    return hedef


def arsivi_ac(tar_yolu: Path, klasor: Path):
    """Yalnizca imagesTr ve labelsTr uyelerini acar (imagesTs etiketsiz, ise yaramaz)."""
    if (klasor / "imagesTr").exists():
        print("Arsiv zaten acilmis")
        return
    klasor.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_yolu) as t:
        uyeler = [m for m in t.getmembers()
                  if m.isfile() and ("imagesTr" in m.name or "labelsTr" in m.name)
                  and m.name.endswith(".nii.gz") and "._" not in m.name]
        print(f"{len(uyeler)} dosya aciliyor")
        for m in uyeler:
            m.name = "/".join(m.name.split("/")[-2:])   # Task03_Liver/imagesTr/x -> imagesTr/x
            t.extract(m, klasor)


def voksel_araligi(affine) -> np.ndarray:
    """Voksel araligi (mm). np.diag yerine sutun normu kullanilir: oblik
    (dondurulmus) affine'lerde kosegen sifir olabilir ve hesaplari bozar."""
    return np.linalg.norm(np.asarray(affine)[:3, :3], axis=0)


def vakayi_hazirla(args):
    ad, ct_p, et_p, cikti, bicim, hedef_aralik, kirp, gercek = args
    try:
        ct_im = nib.load(ct_p)
        ct = np.asanyarray(ct_im.dataobj).astype(np.float32)
        et = np.asanyarray(nib.load(et_p).dataobj).astype(np.uint8)
        aralik = voksel_araligi(ct_im.affine).astype(np.float32)
        if gercek is not None:
            # Baslik sahte (LiTS 28-47: 1x1x1 mm); gercek deger IRCAD DICOM'undan
            aralik = np.asarray(gercek, dtype=np.float32)
        if not np.all(aralik > 0):
            raise ValueError(f"gecersiz voksel araligi: {aralik}")

        degerler = set(np.unique(et).tolist())
        if not degerler <= {0, 1, 2}:
            raise ValueError(f"beklenmeyen etiket degerleri: {sorted(degerler)}")

        if kirp and (et >= 1).any():
            koord = np.argwhere(et >= 1)
            alt = np.maximum(koord.min(0) - (KENAR_MM / aralik).astype(int), 0)
            ust = np.minimum(koord.max(0) + 1 + (KENAR_MM / aralik).astype(int), et.shape)
            dilim = tuple(slice(int(x), int(y)) for x, y in zip(alt, ust))
            ct, et = ct[dilim], et[dilim]

        if bicim == "npz":
            olcek = aralik / np.asarray(hedef_aralik, dtype=np.float32)
            if not np.allclose(olcek, 1.0, atol=0.02):
                ct = ndimage.zoom(ct, olcek, order=1)
                et = ndimage.zoom(et, olcek, order=0).astype(np.uint8)
            affine = np.eye(4, dtype=np.float32)
            affine[:3, :3] = np.diag(hedef_aralik)
            Path(cikti).mkdir(parents=True, exist_ok=True)
            np.savez_compressed(Path(cikti) / f"{ad}.npz",
                                ct=np.clip(ct, -1024, 3071).astype(np.int16), etiket=et,
                                aralik=np.asarray(hedef_aralik, dtype=np.float32), affine=affine)
        else:  # nnunet: imagesTs / labelsTs
            for alt_k in ("imagesTs", "labelsTs"):
                (Path(cikti) / alt_k).mkdir(parents=True, exist_ok=True)
            nib.save(nib.Nifti1Image(ct.astype(np.int16), ct_im.affine),
                     Path(cikti) / "imagesTs" / f"{ad}_0000.nii.gz")
            nib.save(nib.Nifti1Image(et, ct_im.affine),
                     Path(cikti) / "labelsTs" / f"{ad}.nii.gz")

        lab, n = ndimage.label(et == 2, structure=np.ones((3, 3, 3)))
        voksel_cm3 = float(np.prod(hedef_aralik if bicim == "npz" else aralik)) / 1000
        return dict(vaka=ad, shape=str(ct.shape), lezyon_sayisi=int(n),
                    karaciger_cm3=round(float((et >= 1).sum() * voksel_cm3), 1),
                    tumor_cm3=round(float((et == 2).sum() * voksel_cm3), 2), hata="")
    except Exception as e:  # noqa: BLE001
        return dict(vaka=ad, shape="", lezyon_sayisi=0, karaciger_cm3=0.0, tumor_cm3=0.0,
                    hata=f"{type(e).__name__}: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tar", default=None, help="yerel Task03_Liver.tar; yoksa indirilir")
    p.add_argument("--calisma", default=None, help="arsivin acilacagi klasor (varsayilan: cikti/ham)")
    p.add_argument("--cikti", required=True)
    p.add_argument("--format", choices=["npz", "nnunet"], default="npz")
    p.add_argument("--aralik", type=float, nargs=3, default=[2.0, 2.0, 3.0])
    p.add_argument("--kirpma", action="store_true", default=True)
    p.add_argument("--isler", type=int, default=os.cpu_count() or 8)
    p.add_argument("--gercek-aralik", default=None,
                   help="lits_no,sx,sy,sz CSV'si; bu vakalarda basliktaki voksel araligi yerine kullanilir "
                        "(LiTS 28-47 basliklari sahte 1x1x1 mm)")
    p.add_argument("--sadece", type=int, nargs="*", default=None,
                   help="yalnizca bu LiTS numaralarini isle (rapor ayri dosyaya yazilir)")
    a = p.parse_args()

    cikti = Path(a.cikti)
    calisma = Path(a.calisma) if a.calisma else cikti / "ham"
    tar_yolu = Path(a.tar) if a.tar else calisma / "Task03_Liver.tar"

    arsivi_indir(tar_yolu)
    arsivi_ac(tar_yolu, calisma)

    goruntuler = sorted((calisma / "imagesTr").glob("liver_*.nii.gz"))
    gercek = {}
    if a.gercek_aralik:
        g = pd.read_csv(a.gercek_aralik)
        gercek = {int(r.lits_no): (r.sx, r.sy, r.sz) for r in g.itertuples()}
    isler = []
    for ct_p in goruntuler:
        et_p = calisma / "labelsTr" / ct_p.name
        if et_p.exists():
            no = int(ct_p.stem.replace(".nii", "").split("_")[-1])
            if a.sadece is not None and no not in a.sadece:
                continue
            ad = "LITS_" + str(no).zfill(4)
            isler.append((ad, str(ct_p), str(et_p), str(cikti), a.format, a.aralik, a.kirpma,
                          gercek.get(no)))
    print(f"{len(isler)} LiTS vakasi hazirlaniyor -> {cikti} ({a.format})")

    sonuclar = []
    with ProcessPoolExecutor(max_workers=a.isler) as havuz:
        gelecekler = [havuz.submit(vakayi_hazirla, i) for i in isler]
        for n, f in enumerate(as_completed(gelecekler), 1):
            sonuclar.append(f.result())
            if n % 20 == 0:
                print(f"  {n}/{len(isler)}", flush=True)

    rapor = pd.DataFrame(sonuclar).sort_values("vaka")
    cikti.mkdir(parents=True, exist_ok=True)
    rapor_adi = "lits_harici.csv" if a.sadece is None else "lits_harici_duzeltme.csv"
    rapor.to_csv(cikti / rapor_adi, index=False)
    basarili = rapor[rapor.hata == ""]
    print("\n--- Ozet ---")
    print(f"hazirlanan vaka : {len(basarili)}")
    print(f"tumorlu vaka    : {int((basarili.lezyon_sayisi > 0).sum())}")
    print(f"toplam lezyon   : {int(basarili.lezyon_sayisi.sum())}")
    print(f"ortanca karaciger hacmi: {basarili.karaciger_cm3.median():.0f} cm3")
    if (rapor.hata != "").any():
        print(rapor[rapor.hata != ""][["vaka", "hata"]].head().to_string(index=False))
    print(f"\nRapor: {cikti/rapor_adi}")


if __name__ == "__main__":
    main()
