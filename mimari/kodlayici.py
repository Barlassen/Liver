#!/usr/bin/env python3
"""V-JEPA 2 kodlayici sarmalayicisi (dondurulmus).

V-JEPA 2 videoyla egitildi: (B, T, 3, H, W). Biz eksenel CT dilimlerini kare
gibi veriyoruz. Cikti token dizisi (B, N, C) olup N = (T/tubelet) * (H/p) * (W/p);
bunu (B, C, t, h, w) bicimine geri katliyoruz ki cozucu 3B evrisim uygulayabilsin.

Kodlayici DONDURULMUS: gradyan yok, egitilen tek sey cozucu. Boylece 16 GB'lik
bir Kaggle GPU'suna sigar ve ozellikler bir kez hesaplanip onbelleklenebilir.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

VARSAYILAN_MODEL = "facebook/vjepa2-vitl-fpc64-256"
ORT, STD = 0.485, 0.229  # tek kanala indirgenmis ImageNet istatistigi


class VJepaKodlayici(nn.Module):
    """dondur=True: V-JEPA 2 agirliklari donduruldu, yalnizca cozucu egitilir.
    rastgele=True: ayni mimari, ON EGITILMIS AGIRLIK YOK -> ablasyon kolu.
    Ikisinin farki "V-JEPA on egitimi ne kazandiriyor" sorusunun cevabidir."""

    def __init__(self, model_adi: str = VARSAYILAN_MODEL, dondur: bool = True,
                 rastgele: bool = False, coz_son_blok: int = 0):
        super().__init__()
        from transformers import AutoConfig, AutoModel  # torch'suz ortamda import edilebilsin
        if rastgele:
            self.govde = AutoModel.from_config(AutoConfig.from_pretrained(model_adi))
        else:
            self.govde = AutoModel.from_pretrained(model_adi)
        cfg = self.govde.config
        self.yama = getattr(cfg, "patch_size", 16)
        self.tubelet = getattr(cfg, "tubelet_size", 2)
        self.boyut = getattr(cfg, "hidden_size", 1024)
        self.dondu = dondur
        if dondur:
            for p in self.govde.parameters():
                p.requires_grad_(False)
            self.govde.eval()
        self.cozulen = self._son_bloklari_coz(coz_son_blok) if (dondur and coz_son_blok) else []
        if self.cozulen:
            self.dondu = False        # govde artik kismen egitiliyor
            print(f"kodlayicinin son {coz_son_blok} blogu cozuldu "
                  f"({sum(p.numel() for p in self.cozulen)/1e6:.1f} M parametre)")

    def _son_bloklari_coz(self, n: int):
        """Transformer bloklarinin son n tanesini egitilebilir yapar (ince ayar kolu).
        Blok indeksleri parametre adlarindan cikarilir; mimariye ozel isim varsaymaz."""
        import re
        indeksler = set()
        for ad, _ in self.govde.named_parameters():
            m = re.search(r"(?:layers?|blocks?)\.(\d+)\.", ad)
            if m:
                indeksler.add(int(m.group(1)))
        if not indeksler:
            print("UYARI: transformer bloklari bulunamadi, kodlayici tamamen dondu")
            return []
        esik = max(indeksler) - n + 1
        cozulen = []
        for ad, p in self.govde.named_parameters():
            m = re.search(r"(?:layers?|blocks?)\.(\d+)\.", ad)
            if m and int(m.group(1)) >= esik:
                p.requires_grad_(True)
                cozulen.append(p)
        return cozulen

    def train(self, mod: bool = True):
        super().train(mod)
        if self.dondu:
            self.govde.eval()   # dondurulmus govde her zaman eval modunda kalir
        return self

    @property
    def cikti_boyutu(self) -> int:
        return self.boyut

    def _hazirla(self, x: torch.Tensor) -> torch.Tensor:
        """(B, K, D, H, W) -> (B, D, 3, H, W), normalize edilmis."""
        if x.shape[1] == 1:
            kanallar = [x[:, 0]] * 3
        else:  # (karaciger penceresi, karaciger penceresi, genis pencere)
            kanallar = [x[:, 0], x[:, 0], x[:, 1]]
        v = torch.stack(kanallar, dim=2)          # (B, D, 3, H, W)
        return (v - ORT) / STD

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """(B, K, D, H, W) -> (B, C, t, h, w)"""
        B, _, D, H, W = x.shape
        v = self._hazirla(x)
        baglam = torch.no_grad() if self.dondu else torch.enable_grad()
        with baglam:
            cikti = self.govde(pixel_values_videos=v)
        tokenler = cikti.last_hidden_state              # (B, N, C)
        t, h, w = D // self.tubelet, H // self.yama, W // self.yama
        beklenen = t * h * w
        if tokenler.shape[1] != beklenen:
            raise RuntimeError(
                f"token sayisi {tokenler.shape[1]}, beklenen {beklenen} "
                f"(D={D}, H={H}, W={W}, tubelet={self.tubelet}, yama={self.yama}). "
                "Girdi boyutlarini modelin bekledigi degerlere ayarlayin.")
        return tokenler.transpose(1, 2).reshape(B, self.boyut, t, h, w)


class SahteKodlayici(nn.Module):
    """Agirlik indirmeden boru hattini test etmek icin: ayni bicimde cikti uretir."""

    def __init__(self, boyut=256, yama=16, tubelet=2):
        super().__init__()
        self.boyut, self.yama, self.tubelet = boyut, yama, tubelet
        self.govde = nn.Conv3d(2, boyut, kernel_size=(tubelet, yama, yama),
                               stride=(tubelet, yama, yama))

    @property
    def cikti_boyutu(self):
        return self.boyut

    def forward(self, x):
        return F.gelu(self.govde(x))
