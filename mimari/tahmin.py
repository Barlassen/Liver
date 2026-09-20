#!/usr/bin/env python3
"""Egitilmis cozucuyle tum hacimde cikarim.

Hacim ortusen slab'lere bolunur, logit'ler toplanir, sonunda argmax alinir.
Cikti nnU-Net etiketleriyle ayni adla yazilir; boylece 04_degerlendir.py
dogrudan calisir.

Ornek:
  python tahmin.py --vakalar /kaggle/input/liver/test --checkpoint /kaggle/working/vjepa/en_iyi.pt \
      --cikti /kaggle/working/tahmin
"""
import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from scipy import ndimage

from cozucu import Model
from kodlayici import SahteKodlayici, VJepaKodlayici, VARSAYILAN_MODEL
from veri import _yukle, pencerele, slab_bol


def son_isleme(maske: np.ndarray, aralik, en_kucuk_cm3: float = 0.05) -> np.ndarray:
    """Klasik iki son-isleme adimi:
      1. Karaciger disindaki tumor tahminleri elenir (anatomik olarak imkansiz).
      2. Cok kucuk kopuk bilesenler atilir -> yanlis pozitif azalir.
    En buyuk karaciger bileseni disindaki karaciger parcalari da temizlenir."""
    kc = maske >= 1
    if kc.any():
        lab, n = ndimage.label(kc)
        if n > 1:
            en_buyuk = int(np.argmax(np.bincount(lab.ravel())[1:])) + 1
            maske[(lab != en_buyuk) & kc] = 0
    tumor = maske == 2
    if tumor.any():
        voksel_cm3 = float(np.prod(aralik)) / 1000.0
        lab, n = ndimage.label(tumor, structure=np.ones((3, 3, 3)))
        boyutlar = np.bincount(lab.ravel())
        for i in range(1, n + 1):
            if boyutlar[i] * voksel_cm3 < en_kucuk_cm3:
                maske[lab == i] = 1                  # karacigere geri ver
    return maske


def kaydet(maske: np.ndarray, kaynak: Path, hedef: Path):
    if kaynak.suffix == ".npz":
        d = np.load(kaynak)
        affine = d["affine"] if "affine" in d else np.diag(list(d["aralik"]) + [1.0])
    else:
        affine = nib.load(kaynak).affine
    im = nib.Nifti1Image(maske.astype(np.uint8), affine)
    im.set_data_dtype(np.uint8)
    nib.save(im, hedef)


def _doldur_kirp(x: np.ndarray, b: int):
    """Egitimdekiyle AYNI islem: merkezden kirp, sonra sifirla doldur.
    Cikarimda olcekleme yapilirsa anatomi yanlis buyuklukte gorunur ve model coker."""
    K, d, H, W = x.shape
    h0, w0 = max(0, (H - b) // 2), max(0, (W - b) // 2)
    kirpik = x[..., h0:h0 + b, w0:w0 + b]
    hk, wk = kirpik.shape[-2], kirpik.shape[-1]
    dolu = np.zeros((K, d, b, b), dtype=x.dtype)
    dolu[..., :hk, :wk] = kirpik
    return dolu, (h0, w0, hk, wk)


@torch.no_grad()
def vakayi_tahmin_et(model, yol: Path, cihaz, slab=16, boyut=256, sinif=3):
    hu, _, _ = _yukle(yol)
    H, W, D = hu.shape
    toplam = np.zeros((sinif, D, H, W), dtype=np.float32)
    sayac = np.zeros(D, dtype=np.float32)

    for z0 in slab_bol(D, slab):
        parca = np.moveaxis(hu[..., z0:z0 + slab], -1, 0)          # (d, H, W)
        d = parca.shape[0]
        if d < slab:
            parca = np.pad(parca, ((0, slab - d), (0, 0), (0, 0)), mode="edge")
        ham = pencerele(parca)                                      # (K, d, H, W)
        dolu, (h0, w0, hk, wk) = _doldur_kirp(ham, boyut)
        x = torch.from_numpy(dolu).unsqueeze(0).to(cihaz)

        with torch.autocast(cihaz.type, dtype=torch.float16, enabled=cihaz.type == "cuda"):
            logit = model(x)
        logit = logit.float()[0]                                     # (sinif, slab, b, b)

        # Doldurmayi geri al: yalnizca gercek anatomiye denk gelen bolge yazilir.
        toplam[:, z0:z0 + d, h0:h0 + hk, w0:w0 + wk] += logit[:, :d, :hk, :wk].cpu().numpy()
        sayac[z0:z0 + d] += 1

    toplam /= np.maximum(sayac, 1)[None, :, None, None]
    return np.moveaxis(toplam.argmax(0).astype(np.uint8), 0, -1)     # (H, W, D)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vakalar", required=True)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--cikti", required=True)
    p.add_argument("--model-adi", default=VARSAYILAN_MODEL)
    p.add_argument("--sahte-kodlayici", action="store_true")
    p.add_argument("--rastgele-kodlayici", action="store_true")
    p.add_argument("--coz-son-blok", type=int, default=0)
    p.add_argument("--slab", type=int, default=16)
    p.add_argument("--boyut", type=int, default=256)
    p.add_argument("--son-isleme", action="store_true",
                   help="karaciger disi tumorleri ve cok kucuk bilesenleri ele")
    p.add_argument("--en-kucuk-cm3", type=float, default=0.05)
    a = p.parse_args()

    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)

    kodlayici = (SahteKodlayici() if a.sahte_kodlayici
                 else VJepaKodlayici(a.model_adi, rastgele=a.rastgele_kodlayici,
                                     coz_son_blok=a.coz_son_blok))
    model = Model(kodlayici).to(cihaz).eval()
    durum = torch.load(a.checkpoint, map_location=cihaz, weights_only=False)
    model.cozucu.load_state_dict(durum["cozucu"])
    if durum.get("kodlayici"):
        model.kodlayici.load_state_dict(durum["kodlayici"])
    print(f"Checkpoint yuklendi (epoch {durum['epoch']}, en iyi tumor Dice {durum['en_iyi']:.3f})")

    vakalar = sorted(list(Path(a.vakalar).glob("*.npz")) + list(Path(a.vakalar).glob("*_0000.nii.gz")))
    for n, yol in enumerate(vakalar, 1):
        maske = vakayi_tahmin_et(model, yol, cihaz, a.slab, a.boyut)
        if a.son_isleme:
            aralik = (np.load(yol)["aralik"] if yol.suffix == ".npz"
                      else np.linalg.norm(nib.load(yol).affine[:3, :3], axis=0))
            maske = son_isleme(maske, aralik, a.en_kucuk_cm3)
        ad = yol.name.replace("_0000.nii.gz", ".nii.gz").replace(".npz", ".nii.gz")
        kaydet(maske, yol, cikti / ad)
        print(f"  {n}/{len(vakalar)} {ad}", flush=True)
    print(f"\nTahminler: {cikti}")


if __name__ == "__main__":
    main()
