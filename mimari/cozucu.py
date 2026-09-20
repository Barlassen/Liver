#!/usr/bin/env python3
"""Hafif 3B cozucu: kodlayici token'larindan voksel maskesi uretir.

ViT 16x16 yamalarla calistigi icin token haritasi kaba (256 -> 16). Kucuk
lezyonlarin kaybolmamasi icin ham goruntuden gelen yuksek cozunurluklu atlama
baglantilari (skip connection) ekleniyor -- U-Net'i calistiran fikrin aynisi.

Egitilen parametre sayisi ~7 M; 16 GB'lik GPU'ya rahat sigar.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


def blok(gir, cik):
    return nn.Sequential(
        nn.Conv3d(gir, cik, 3, padding=1, bias=False),
        nn.InstanceNorm3d(cik, affine=True), nn.LeakyReLU(0.01, inplace=True),
        nn.Conv3d(cik, cik, 3, padding=1, bias=False),
        nn.InstanceNorm3d(cik, affine=True), nn.LeakyReLU(0.01, inplace=True),
    )


class GoruntuGovdesi(nn.Module):
    """Ham goruntuden 1/2, 1/4 ve 1/8 cozunurlukte ozellik uretir (yalnizca H, W kucultur)."""

    def __init__(self, gir=2, taban=32):
        super().__init__()
        self.k1 = blok(gir, taban)                                  # 1/1
        self.k2 = nn.Sequential(nn.AvgPool3d((1, 2, 2)), blok(taban, taban * 2))      # 1/2
        self.k3 = nn.Sequential(nn.AvgPool3d((1, 2, 2)), blok(taban * 2, taban * 4))  # 1/4
        self.k4 = nn.Sequential(nn.AvgPool3d((1, 2, 2)), blok(taban * 4, taban * 4))  # 1/8

    def forward(self, x):
        a = self.k1(x)
        b = self.k2(a)
        c = self.k3(b)
        d = self.k4(c)
        return a, b, c, d


class Cozucu(nn.Module):
    """Kodlayici ozelligi (B, C, t, h, w) + ham goruntu -> (B, sinif, D, H, W)."""

    def __init__(self, kodlayici_boyutu: int, sinif: int = 3, taban: int = 32, gir_kanal: int = 2):
        super().__init__()
        self.govde = GoruntuGovdesi(gir_kanal, taban)
        self.giris = nn.Sequential(
            nn.Conv3d(kodlayici_boyutu, taban * 8, 1, bias=False),
            nn.InstanceNorm3d(taban * 8, affine=True), nn.LeakyReLU(0.01, inplace=True))
        self.y8 = blok(taban * 8 + taban * 4, taban * 4)   # 1/8
        self.y4 = blok(taban * 4 + taban * 4, taban * 2)   # 1/4
        self.y2 = blok(taban * 2 + taban * 2, taban)       # 1/2
        self.y1 = blok(taban + taban, taban)               # 1/1
        self.bas = nn.Conv3d(taban, sinif, 1)

    @staticmethod
    def _uyarla(x, hedef):
        if x.shape[-3:] != hedef.shape[-3:]:
            x = F.interpolate(x, size=hedef.shape[-3:], mode="trilinear", align_corners=False)
        return x

    def forward(self, ozellik, goruntu):
        a, b, c, d = self.govde(goruntu)
        z = self.giris(ozellik)
        z = self.y8(torch.cat([self._uyarla(z, d), d], 1))
        z = self.y4(torch.cat([self._uyarla(z, c), c], 1))
        z = self.y2(torch.cat([self._uyarla(z, b), b], 1))
        z = self.y1(torch.cat([self._uyarla(z, a), a], 1))
        return self.bas(z)


class DiceCEKaybi(nn.Module):
    """Dice + capraz entropi. Tumor sinifi seyrek oldugu icin agirlikli."""

    def __init__(self, sinif=3, agirlik=(0.2, 1.0, 3.0), duzeltme=1e-5):
        super().__init__()
        self.sinif, self.duzeltme = sinif, duzeltme
        self.ce = nn.CrossEntropyLoss(weight=torch.tensor(agirlik, dtype=torch.float32))

    def forward(self, logit, hedef):
        ce = self.ce(logit, hedef)
        olasilik = torch.softmax(logit.float(), 1)
        tek = F.one_hot(hedef, self.sinif).permute(0, 4, 1, 2, 3).float()
        eksen = (0, 2, 3, 4)
        kesisim = (olasilik * tek).sum(eksen)
        toplam = olasilik.sum(eksen) + tek.sum(eksen)
        dice = (2 * kesisim + self.duzeltme) / (toplam + self.duzeltme)
        return ce + (1 - dice[1:].mean())      # arka plan Dice'i kayba katilmaz


class Model(nn.Module):
    """Kodlayici + cozucu."""

    def __init__(self, kodlayici, sinif=3, taban=32, gir_kanal=2):
        super().__init__()
        self.kodlayici = kodlayici
        self.cozucu = Cozucu(kodlayici.cikti_boyutu, sinif, taban, gir_kanal)

    def forward(self, x, ozellik=None):
        if ozellik is None:
            ozellik = self.kodlayici(x)
        return self.cozucu(ozellik.to(x.dtype), x)
