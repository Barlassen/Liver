#!/usr/bin/env python3
"""Slab (dilim grubu) tabanli veri yukleyici.

V-JEPA 2 kodlayicisi video bekler: T kare x H x W. Biz eksenel CT dilimlerini
kare gibi veriyoruz -> bir "slab" = ust uste T dilim.

Girdi: 02_donustur.py ciktisi (nnU-Net formati) veya 06_kaggle_hazirla.py'nin
kucultulmus .npz dosyalari. Ikisi de desteklenir.
"""
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

# Karaciger penceresi (merkez 60, genislik 400) ve genis pencere.
PENCERELER = ((-140.0, 260.0), (-1000.0, 1000.0))


def pencerele(hu: np.ndarray) -> np.ndarray:
    """HU hacmini kanallara ayrilmis [0,1] araligina cevirir -> (K, D, H, W)."""
    kanallar = [np.clip((hu - alt) / (ust - alt), 0, 1) for alt, ust in PENCERELER]
    return np.stack(kanallar).astype(np.float32)


def _yukle(yol: Path):
    """Vakayi (hu, etiket, aralik) olarak dondurur."""
    if yol.suffix == ".npz":
        d = np.load(yol)
        return d["ct"].astype(np.float32), d["etiket"].astype(np.int64), tuple(d["aralik"])
    import nibabel as nib
    ct_im = nib.load(yol)
    etiket_p = Path(str(yol).replace("images", "labels").replace("_0000.nii.gz", ".nii.gz"))
    aralik = tuple(np.abs(np.diag(ct_im.affine)[:3]).tolist())
    return (np.asanyarray(ct_im.dataobj).astype(np.float32),
            np.asanyarray(nib.load(etiket_p).dataobj).astype(np.int64), aralik)


class SlabVeriSeti(Dataset):
    """Egitim icin rastgele slab ornekler; tumor iceren slab'leri one cikarir."""

    def __init__(self, vakalar, slab=16, boyut=256, tumor_orani=0.5, artir=True,
                 ornek_sayisi=None, tohum=0):
        self.vakalar = [Path(v) for v in vakalar]
        self.slab, self.boyut, self.tumor_orani, self.artir = slab, boyut, tumor_orani, artir
        self.n = ornek_sayisi or len(self.vakalar) * 8
        self.rng = np.random.default_rng(tohum)
        self._onbellek = {}

    def __len__(self):
        return self.n

    def _vaka(self, i):
        yol = self.vakalar[i % len(self.vakalar)]
        if yol not in self._onbellek:
            if len(self._onbellek) > 4:          # RAM'i sismesin diye kucuk onbellek
                self._onbellek.pop(next(iter(self._onbellek)))
            self._onbellek[yol] = _yukle(yol)
        return self._onbellek[yol]

    def __getitem__(self, idx):
        hu, etiket, _ = self._vaka(int(self.rng.integers(len(self.vakalar))))
        H, W, D = hu.shape          # NIfTI sirasi: (H, W, dilim)

        # z ekseninde baslangic: tumor varsa buyuk olasilikla tumorlu bolgeden sec
        tumor_z = np.where((etiket == 2).any(axis=(0, 1)))[0] if (etiket == 2).any() else None
        if tumor_z is not None and self.rng.random() < self.tumor_orani:
            merkez = int(self.rng.choice(tumor_z))
            z0 = int(np.clip(merkez - self.slab // 2, 0, max(0, D - self.slab)))
        else:
            z0 = int(self.rng.integers(0, max(1, D - self.slab + 1)))

        dilim_hu = hu[..., z0:z0 + self.slab]
        dilim_et = etiket[..., z0:z0 + self.slab]
        # (H, W, D) -> (D, H, W)
        dilim_hu = np.moveaxis(dilim_hu, -1, 0)
        dilim_et = np.moveaxis(dilim_et, -1, 0)
        if dilim_hu.shape[0] < self.slab:        # kisa kalirsa kenarla doldur
            eksik = self.slab - dilim_hu.shape[0]
            dilim_hu = np.pad(dilim_hu, ((0, eksik), (0, 0), (0, 0)), mode="edge")
            dilim_et = np.pad(dilim_et, ((0, eksik), (0, 0), (0, 0)), mode="edge")

        x = pencerele(dilim_hu)                  # (K, D, H, W)
        y = dilim_et

        if self.artir:
            if self.rng.random() < 0.5:
                x, y = x[..., ::-1].copy(), y[..., ::-1].copy()      # sag-sol cevir
            if self.rng.random() < 0.3:
                x = np.clip(x * self.rng.uniform(0.9, 1.1) +
                            self.rng.uniform(-0.05, 0.05), 0, 1)     # parlaklik/kontrast

        x, y = self._boyutlandir(x, y)
        return torch.from_numpy(x), torch.from_numpy(y)

    def _boyutlandir(self, x, y):
        """H, W eksenlerini kodlayicinin bekledigi boyuta getirir (kirp veya doldur)."""
        b = self.boyut
        K, D, H, W = x.shape
        if (H, W) != (b, b):
            h0 = max(0, (H - b) // 2)
            w0 = max(0, (W - b) // 2)
            x, y = x[..., h0:h0 + b, w0:w0 + b], y[..., h0:h0 + b, w0:w0 + b]
            ph, pw = b - x.shape[-2], b - x.shape[-1]
            if ph > 0 or pw > 0:
                x = np.pad(x, ((0, 0), (0, 0), (0, ph), (0, pw)))
                y = np.pad(y, ((0, 0), (0, ph), (0, pw)))
        return np.ascontiguousarray(x), np.ascontiguousarray(y)


def slab_bol(D: int, slab: int, ortusme: int = 4):
    """Cikarim icin hacmi ortusen slab'lere boler."""
    adim = max(1, slab - ortusme)
    basliklar = list(range(0, max(1, D - slab + 1), adim))
    if basliklar[-1] + slab < D:
        basliklar.append(max(0, D - slab))
    return basliklar
