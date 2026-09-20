#!/usr/bin/env python3
"""AbdomenAtlas 3.0 maskelerini nnU-Net formatina donusturur.

Etiketler: 0 = arka plan, 1 = karaciger, 2 = tumor

ONEMLI: AbdomenAtlas'ta maske hacmi CT ile ayni izgarada olmayabilir. Ornek:
CT (512, 512, 339) iken maske (511, 404, 339) olabilir -- maske kirpilmis,
affine'in kaydirma (translation) kismi farki tasiyor. Bu betik maskeyi CT
izgarasina geri oturtur; voksel araliklari ve yonelim ayni olmak zorundadir.
Oturmayan vakalar donusturulmez, raporda "hata" olarak isaretlenir.

Kullanim:
  python 02_donustur.py --ham /mnt/veri/ham --cikti /mnt/veri/nnUNet_raw \
      --vakalar karaciger_vakalar.csv --isler 16
"""
import argparse
import json
import os
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

VERI_SETI = "Dataset001_LiverTumor"
ONEK = "LIVER"


def ct_yolu(ham: Path, vid: str) -> Path:
    for aday in [ham / "images" / vid / "ct.nii.gz", ham / "images" / vid / f"{vid}.nii.gz"]:
        if aday.exists():
            return aday
    bulunan = sorted((ham / "images" / vid).glob("*.nii.gz"))
    if not bulunan:
        raise FileNotFoundError(f"{vid}: CT bulunamadi")
    return bulunan[0]


def izgaraya_otur(maske_im, ct_im) -> np.ndarray:
    """Maskeyi CT izgarasina yerlestirir. Ayni izgaradaysa dogrudan dondurur."""
    m = np.asanyarray(maske_im.dataobj)
    if maske_im.shape == ct_im.shape and np.allclose(maske_im.affine, ct_im.affine, atol=1e-3):
        return m, "birebir", (0, 0, 0)

    # Maske voksel koordinatlarini CT voksel koordinatlarina ceviren donusum.
    M = np.linalg.inv(ct_im.affine) @ maske_im.affine
    if not np.allclose(M[:3, :3], np.eye(3), atol=1e-3):
        raise ValueError("voksel araligi/yonelimi farkli, basit kaydirma yetmiyor")
    ofset = np.rint(M[:3, 3]).astype(int)
    if not np.allclose(M[:3, 3], ofset, atol=0.1):
        raise ValueError(f"kaydirma tam voksel degil: {M[:3, 3]}")

    cikti = np.zeros(ct_im.shape, dtype=m.dtype)
    dilim_ct, dilim_m = [], []
    for eksen in range(3):
        bas = int(ofset[eksen])
        son = bas + m.shape[eksen]
        kes_bas, kes_son = max(bas, 0), min(son, ct_im.shape[eksen])
        if kes_bas >= kes_son:
            raise ValueError("maske CT hacminin tamamen disinda")
        dilim_ct.append(slice(kes_bas, kes_son))
        dilim_m.append(slice(kes_bas - bas, kes_son - bas))
    cikti[tuple(dilim_ct)] = m[tuple(dilim_m)]
    return cikti, "ofset", tuple(int(x) for x in ofset)


def vakayi_isle(args):
    vid, split, ham, cikti = args
    ham, cikti = Path(ham), Path(cikti)
    try:
        ct_p = ct_yolu(ham, vid)
        ct_im = nib.load(ct_p)
        seg = ham / "masks" / vid / "segmentations"
        kc_im = nib.load(seg / "liver.nii.gz")
        lz_p = seg / "liver_lesion.nii.gz"

        kc, hiz, ofset = izgaraya_otur(kc_im, ct_im)
        etiket = (kc > 0).astype(np.uint8)
        lezyon_var = lz_p.exists()
        if lezyon_var:
            lz, _, _ = izgaraya_otur(nib.load(lz_p), ct_im)
            etiket[lz > 0] = 2  # tumor, karacigerin uzerine yazar

        alt = "Tr" if split == "train" else "Ts"
        goruntu_adi = cikti / VERI_SETI / f"images{alt}" / f"{ONEK}_{vid[6:]}_0000.nii.gz"
        etiket_adi = cikti / VERI_SETI / f"labels{alt}" / f"{ONEK}_{vid[6:]}.nii.gz"

        # Goruntuyu kopyalamak yerine baglanti kuruyoruz (yuzlerce GB'dan tasarruf).
        if goruntu_adi.exists() or goruntu_adi.is_symlink():
            goruntu_adi.unlink()
        os.symlink(os.path.realpath(ct_p), goruntu_adi)

        yeni = nib.Nifti1Image(etiket, ct_im.affine, ct_im.header)
        yeni.set_data_dtype(np.uint8)
        nib.save(yeni, etiket_adi)

        return dict(bdmap_id=vid, split=split, durum="uygun", hizalama=hiz, ofset=str(ofset),
                    ct_shape=str(ct_im.shape), maske_shape=str(kc_im.shape),
                    tumor_voksel=int((etiket == 2).sum()), lezyon_dosyasi=lezyon_var, hata="")
    except Exception as e:  # noqa: BLE001
        return dict(bdmap_id=vid, split=split, durum="hata", hizalama="", ofset="",
                    ct_shape="", maske_shape="", tumor_voksel=0, lezyon_dosyasi=False,
                    hata=f"{type(e).__name__}: {e}", iz=traceback.format_exc(limit=1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ham", required=True, help="images/ ve masks/ klasorlerinin bulundugu dizin")
    p.add_argument("--cikti", required=True, help="nnUNet_raw dizini")
    p.add_argument("--vakalar", required=True, help="karaciger_vaka_sec.py ciktisi")
    p.add_argument("--isler", type=int, default=os.cpu_count() or 8)
    a = p.parse_args()

    vakalar = pd.read_csv(a.vakalar)
    kok = Path(a.cikti) / VERI_SETI
    for alt in ["imagesTr", "labelsTr", "imagesTs", "labelsTs"]:
        (kok / alt).mkdir(parents=True, exist_ok=True)

    # Indirilmemis parcalardaki vakalari atla.
    mevcut = {p.name for p in (Path(a.ham) / "masks").glob("BDMAP_*")}
    vakalar = vakalar[vakalar["BDMAP ID"].isin(mevcut)]
    print(f"{len(vakalar)} vaka donusturulecek ({a.isler} is parcacigi)")

    isler = [(r["BDMAP ID"], r["split"], a.ham, a.cikti) for _, r in vakalar.iterrows()]
    sonuclar = []
    with ProcessPoolExecutor(max_workers=a.isler) as havuz:
        gelecekler = [havuz.submit(vakayi_isle, i) for i in isler]
        for n, f in enumerate(as_completed(gelecekler), 1):
            sonuclar.append(f.result())
            if n % 50 == 0:
                print(f"  {n}/{len(isler)}", flush=True)

    rapor = pd.DataFrame(sonuclar).sort_values("bdmap_id")
    rapor.to_csv(kok / "donusum_raporu.csv", index=False)

    uygun = rapor[rapor.durum == "uygun"]
    egitim = uygun[uygun.split == "train"]
    dataset = {
        "channel_names": {"0": "CT"},
        "labels": {"background": 0, "liver": 1, "tumor": 2},
        "numTraining": int(len(egitim)),
        "file_ending": ".nii.gz",
        "overwrite_image_reader_writer": "NibabelIOWithReorient",
    }
    (kok / "dataset.json").write_text(json.dumps(dataset, indent=2))

    print("\n--- Ozet ---")
    print(rapor.groupby(["split", "durum"]).size().to_string())
    print(rapor.hizalama.value_counts().to_string())
    if (rapor.durum == "hata").any():
        print("\nIlk hatalar:")
        print(rapor[rapor.durum == "hata"][["bdmap_id", "hata"]].head(10).to_string(index=False))
    print(f"\nRapor: {kok / 'donusum_raporu.csv'}")


if __name__ == "__main__":
    main()
