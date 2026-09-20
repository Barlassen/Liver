#!/usr/bin/env python3
"""3D-IRCADb-01'i ikinci harici test seti olarak hazirlar.

IRCAD AbdomenAtlas'in icinde DEGIL: 20 hastanin hicbirinin geometrisi
(boyut + voksel araligi) AbdomenAtlas metadata'siyla eslesmedi ve AbdomenAtlas
2.0 makalesi IRCAD'i acikca "egitime dahil edilmeyen harici test seti" olarak
kullaniyor. Bu yuzden gercek bir dagitim-disi (OOD) test seti.

Veri DICOM olarak geliyor:
  3Dircadb1.N/PATIENT_DICOM/          -> CT dilimleri
  3Dircadb1.N/MASKS_DICOM/liver/      -> karaciger maskesi
  3Dircadb1.N/MASKS_DICOM/livertumor*/-> tumor maskeleri (birden fazla olabilir)
  3Dircadb1.N/MASKS_DICOM/liverkyst*/ -> kist; TUMOR SAYILMAZ, karaciger olarak kalir

Cikti egitim verisiyle ayni: 0 = arka plan, 1 = karaciger, 2 = tumor, .npz

Kullanim:
  python 13_ircad_hazirla.py --zip ~/veri/ircad/3Dircadb1.zip --calisma ~/veri/ircad/ham \
      --cikti ~/veri/ircad15 --aralik 1.5 1.5 2.0
"""
import argparse
import os
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

KENAR_MM = 20.0


def dicom_hacim(klasor: Path):
    """DICOM dilimlerini konuma gore siralayip (H, W, dilim) hacim dondurur."""
    import pydicom
    dosyalar = sorted(klasor.iterdir())
    dilimler = []
    for d in dosyalar:
        try:
            dilimler.append(pydicom.dcmread(str(d)))
        except Exception:  # noqa: BLE001
            continue
    if not dilimler:
        raise FileNotFoundError(f"{klasor}: DICOM okunamadi")
    # Konuma gore sirala (yoksa dosya adi sirasi)
    try:
        dilimler.sort(key=lambda s: float(s.ImagePositionPatient[2]))
    except Exception:  # noqa: BLE001
        pass
    hacim = np.stack([s.pixel_array for s in dilimler], axis=-1).astype(np.float32)

    ilk = dilimler[0]
    egim = float(getattr(ilk, "RescaleSlope", 1) or 1)
    kesme = float(getattr(ilk, "RescaleIntercept", 0) or 0)
    hacim = hacim * egim + kesme                       # HU'ya cevir

    px = [float(x) for x in getattr(ilk, "PixelSpacing", [1.0, 1.0])]
    if len(dilimler) > 1:
        try:
            dz = abs(float(dilimler[1].ImagePositionPatient[2]) -
                     float(dilimler[0].ImagePositionPatient[2]))
        except Exception:  # noqa: BLE001
            dz = float(getattr(ilk, "SliceThickness", 1.0))
    else:
        dz = float(getattr(ilk, "SliceThickness", 1.0))
    return hacim, np.array([px[0], px[1], dz or 1.0], dtype=np.float32)


def maske_hacmi(klasor: Path) -> np.ndarray:
    import pydicom
    dilimler = []
    for d in sorted(klasor.iterdir()):
        try:
            dilimler.append(pydicom.dcmread(str(d)))
        except Exception:  # noqa: BLE001
            continue
    try:
        dilimler.sort(key=lambda s: float(s.ImagePositionPatient[2]))
    except Exception:  # noqa: BLE001
        pass
    return (np.stack([s.pixel_array for s in dilimler], axis=-1) > 0)


def hastayi_hazirla(args):
    no, kok, cikti, hedef_aralik = args
    hasta = Path(kok) / f"3Dircadb1.{no}"
    try:
        ct, aralik = dicom_hacim(hasta / "PATIENT_DICOM")
        maske_kok = hasta / "MASKS_DICOM"
        kc = maske_hacmi(maske_kok / "liver")
        etiket = kc.astype(np.uint8)                   # 1 = karaciger

        tumor_klasorleri = [k for k in maske_kok.iterdir()
                            if k.is_dir() and k.name.lower().startswith("livertumor")]
        for k in tumor_klasorleri:
            etiket[maske_hacmi(k)] = 2                 # 2 = tumor
        kist_sayisi = len([k for k in maske_kok.iterdir()
                           if k.is_dir() and "kyst" in k.name.lower()])

        # Karaciger cevresine kirp (egitim verisiyle ayni kural)
        koord = np.argwhere(etiket >= 1)
        alt = np.maximum(koord.min(0) - (KENAR_MM / aralik).astype(int), 0)
        ust = np.minimum(koord.max(0) + 1 + (KENAR_MM / aralik).astype(int), etiket.shape)
        dilim = tuple(slice(int(a), int(b)) for a, b in zip(alt, ust))
        ct, etiket = ct[dilim], etiket[dilim]

        olcek = aralik / np.asarray(hedef_aralik, dtype=np.float32)
        if not np.allclose(olcek, 1.0, atol=0.02):
            ct = ndimage.zoom(ct, olcek, order=1)
            etiket = ndimage.zoom(etiket, olcek, order=0).astype(np.uint8)

        affine = np.eye(4, dtype=np.float32)
        affine[:3, :3] = np.diag(hedef_aralik)
        Path(cikti).mkdir(parents=True, exist_ok=True)
        ad = f"IRCAD_{no:04d}"
        np.savez_compressed(Path(cikti) / f"{ad}.npz",
                            ct=np.clip(ct, -1024, 3071).astype(np.int16), etiket=etiket,
                            aralik=np.asarray(hedef_aralik, dtype=np.float32), affine=affine)

        lab, n = ndimage.label(etiket == 2, structure=np.ones((3, 3, 3)))
        voksel_cm3 = float(np.prod(hedef_aralik)) / 1000
        return dict(vaka=ad, shape=str(ct.shape), orijinal_aralik=str(aralik.round(3).tolist()),
                    tumor_klasoru=len(tumor_klasorleri), kist_klasoru=kist_sayisi,
                    lezyon_sayisi=int(n),
                    karaciger_cm3=round(float((etiket >= 1).sum() * voksel_cm3), 1),
                    tumor_cm3=round(float((etiket == 2).sum() * voksel_cm3), 2), hata="")
    except Exception as e:  # noqa: BLE001
        return dict(vaka=f"IRCAD_{no:04d}", shape="", orijinal_aralik="", tumor_klasoru=0,
                    kist_klasoru=0, lezyon_sayisi=0, karaciger_cm3=0.0, tumor_cm3=0.0,
                    hata=f"{type(e).__name__}: {e}")


def arsivi_ac(zip_yolu: Path, calisma: Path):
    calisma.mkdir(parents=True, exist_ok=True)
    if list(calisma.glob("3Dircadb1.*")):
        print("arsiv zaten acilmis")
        return
    print(f"{zip_yolu} aciliyor")
    with zipfile.ZipFile(zip_yolu) as z:
        z.extractall(calisma)
    # Ic ice zip'ler: 3Dircadb1.N/PATIENT_DICOM.zip gibi
    for ic in sorted(calisma.rglob("*.zip")):
        with zipfile.ZipFile(ic) as z:
            z.extractall(ic.parent)
        ic.unlink()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--zip", required=True)
    p.add_argument("--calisma", required=True)
    p.add_argument("--cikti", required=True)
    p.add_argument("--aralik", type=float, nargs=3, default=[1.5, 1.5, 2.0])
    p.add_argument("--isler", type=int, default=min(10, os.cpu_count() or 8))
    a = p.parse_args()

    calisma = Path(a.calisma)
    arsivi_ac(Path(a.zip), calisma)
    kok = calisma if list(calisma.glob("3Dircadb1.*")) else next(calisma.iterdir())

    isler = [(n, str(kok), a.cikti, a.aralik) for n in range(1, 21)
             if (Path(kok) / f"3Dircadb1.{n}").exists()]
    print(f"{len(isler)} IRCAD hastasi hazirlaniyor -> {a.cikti}")

    sonuclar = []
    with ProcessPoolExecutor(max_workers=a.isler) as havuz:
        for f in as_completed([havuz.submit(hastayi_hazirla, i) for i in isler]):
            sonuclar.append(f.result())

    rapor = pd.DataFrame(sonuclar).sort_values("vaka")
    Path(a.cikti).mkdir(parents=True, exist_ok=True)
    rapor.to_csv(Path(a.cikti) / "ircad_rapor.csv", index=False)
    ok = rapor[rapor.hata == ""]
    print("\n--- Ozet ---")
    print(f"hazirlanan hasta : {len(ok)}")
    print(f"tumorlu hasta    : {int((ok.lezyon_sayisi > 0).sum())}")
    print(f"toplam lezyon    : {int(ok.lezyon_sayisi.sum())}")
    print(f"kist klasoru olan: {int((ok.kist_klasoru > 0).sum())} hasta (kistler tumor sayilmadi)")
    print(f"karaciger hacmi ortanca: {ok.karaciger_cm3.median():.0f} cm3")
    if (rapor.hata != "").any():
        print(rapor[rapor.hata != ""][["vaka", "hata"]].to_string(index=False))


if __name__ == "__main__":
    main()
