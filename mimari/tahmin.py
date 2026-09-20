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

import numpy as np
import torch

from cozucu import Model
from kodlayici import SahteKodlayici, VJepaKodlayici, VARSAYILAN_MODEL
from veri import _yukle, pencerele, slab_bol


def kaydet(maske: np.ndarray, kaynak: Path, hedef: Path):
    import nibabel as nib
    if kaynak.suffix == ".npz":
        d = np.load(kaynak)
        affine = d["affine"] if "affine" in d else np.diag(list(d["aralik"]) + [1.0])
    else:
        affine = nib.load(kaynak).affine
    im = nib.Nifti1Image(maske.astype(np.uint8), affine)
    im.set_data_dtype(np.uint8)
    nib.save(im, hedef)


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
        x = torch.from_numpy(pencerele(np.moveaxis(parca, 0, -1)))  # (K, d, H, W)
        x = x.unsqueeze(0).to(cihaz)

        # H, W kodlayicinin bekledigi boyuta getirilir, sonra geri buyutulur.
        kucuk = torch.nn.functional.interpolate(
            x, size=(slab, boyut, boyut), mode="trilinear", align_corners=False)
        with torch.autocast(cihaz.type, dtype=torch.float16, enabled=cihaz.type == "cuda"):
            logit = model(kucuk)
        logit = torch.nn.functional.interpolate(
            logit.float(), size=(slab, H, W), mode="trilinear", align_corners=False)[0]

        toplam[:, z0:z0 + d] += logit[:, :d].cpu().numpy()
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
    p.add_argument("--slab", type=int, default=16)
    p.add_argument("--boyut", type=int, default=256)
    a = p.parse_args()

    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)

    kodlayici = (SahteKodlayici() if a.sahte_kodlayici
                 else VJepaKodlayici(a.model_adi, rastgele=a.rastgele_kodlayici))
    model = Model(kodlayici).to(cihaz).eval()
    durum = torch.load(a.checkpoint, map_location=cihaz, weights_only=False)
    model.cozucu.load_state_dict(durum["cozucu"])
    print(f"Checkpoint yuklendi (epoch {durum['epoch']}, en iyi tumor Dice {durum['en_iyi']:.3f})")

    vakalar = sorted(list(Path(a.vakalar).glob("*.npz")) + list(Path(a.vakalar).glob("*_0000.nii.gz")))
    for n, yol in enumerate(vakalar, 1):
        maske = vakayi_tahmin_et(model, yol, cihaz, a.slab, a.boyut)
        ad = yol.name.replace("_0000.nii.gz", ".nii.gz").replace(".npz", ".nii.gz")
        kaydet(maske, yol, cikti / ad)
        print(f"  {n}/{len(vakalar)} {ad}", flush=True)
    print(f"\nTahminler: {cikti}")


if __name__ == "__main__":
    main()
