#!/usr/bin/env python3
"""Cozucu egitimi (kodlayici dondurulmus).

Kaggle'in 9 saatlik oturum sinirina gore tasarlandi: --sure-siniri dolunca
checkpoint yazip temiz cikar. Ayni komut tekrar calistirilinca kaldigi yerden
devam eder.

Ornek:
  python egit.py --egitim /kaggle/input/liver/train --dogrulama /kaggle/input/liver/val \
      --cikti /kaggle/working/vjepa --epoch 40 --sure-siniri 8.0
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from cozucu import DiceCEKaybi, Model
from kodlayici import SahteKodlayici, VJepaKodlayici, VARSAYILAN_MODEL
from veri import SlabVeriSeti


def vakalari_bul(klasor):
    k = Path(klasor)
    vakalar = sorted(list(k.glob("*.npz")) + list(k.glob("*_0000.nii.gz")))
    if not vakalar:
        raise SystemExit(f"{klasor} icinde vaka bulunamadi")
    return vakalar


@torch.no_grad()
def dogrula(model, yukleyici, cihaz, kayip_fn):
    model.eval()
    kayiplar, dice_tumor, dice_kc = [], [], []
    for x, y in yukleyici:
        x, y = x.to(cihaz), y.to(cihaz)
        with torch.autocast(cihaz.type, dtype=torch.float16, enabled=cihaz.type == "cuda"):
            logit = model(x)
            kayiplar.append(float(kayip_fn(logit, y)))
        tahmin = logit.argmax(1)
        for sinif, liste in ((2, dice_tumor), (1, dice_kc)):
            a, b = tahmin == sinif, y == sinif
            toplam = float(a.sum() + b.sum())
            if toplam > 0:
                liste.append(2 * float((a & b).sum()) / toplam)
    model.train()
    return (float(np.mean(kayiplar)) if kayiplar else float("nan"),
            float(np.mean(dice_kc)) if dice_kc else float("nan"),
            float(np.mean(dice_tumor)) if dice_tumor else float("nan"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--egitim", required=True)
    p.add_argument("--dogrulama", required=True)
    p.add_argument("--cikti", required=True)
    p.add_argument("--model-adi", default=VARSAYILAN_MODEL)
    p.add_argument("--sahte-kodlayici", action="store_true", help="agirlik indirmeden boru hatti testi")
    p.add_argument("--slab", type=int, default=16)
    p.add_argument("--boyut", type=int, default=256)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--adim", type=int, default=200, help="epoch basina adim")
    p.add_argument("--epoch", type=int, default=40)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--sure-siniri", type=float, default=8.0, help="saat; dolunca checkpoint yazip cikar")
    p.add_argument("--isci", type=int, default=2)
    a = p.parse_args()

    baslangic = time.time()
    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)

    kodlayici = SahteKodlayici() if a.sahte_kodlayici else VJepaKodlayici(a.model_adi)
    model = Model(kodlayici).to(cihaz)
    egitilen = [p_ for p_ in model.parameters() if p_.requires_grad]
    print(f"Egitilen parametre: {sum(p_.numel() for p_ in egitilen)/1e6:.1f} M / "
          f"toplam {sum(p_.numel() for p_ in model.parameters())/1e6:.1f} M")

    egitim = SlabVeriSeti(vakalari_bul(a.egitim), a.slab, a.boyut,
                          ornek_sayisi=a.adim * a.batch, artir=True)
    dogrulama = SlabVeriSeti(vakalari_bul(a.dogrulama), a.slab, a.boyut,
                             ornek_sayisi=40, artir=False, tumor_orani=0.5, tohum=1)
    yk_e = DataLoader(egitim, batch_size=a.batch, num_workers=a.isci, pin_memory=True, drop_last=True)
    yk_d = DataLoader(dogrulama, batch_size=a.batch, num_workers=a.isci)

    kayip_fn = DiceCEKaybi().to(cihaz)
    iyilestirici = torch.optim.AdamW(egitilen, lr=a.lr, weight_decay=1e-4)
    zamanlayici = torch.optim.lr_scheduler.CosineAnnealingLR(iyilestirici, T_max=a.epoch)
    olcek = torch.amp.GradScaler(enabled=cihaz.type == "cuda")

    ck = cikti / "checkpoint.pt"
    baslangic_epoch, gecmis, en_iyi = 0, [], -1.0
    if ck.exists():
        durum = torch.load(ck, map_location=cihaz, weights_only=False)
        model.cozucu.load_state_dict(durum["cozucu"])
        iyilestirici.load_state_dict(durum["iyilestirici"])
        zamanlayici.load_state_dict(durum["zamanlayici"])
        baslangic_epoch, gecmis, en_iyi = durum["epoch"], durum["gecmis"], durum["en_iyi"]
        print(f"Checkpoint bulundu, epoch {baslangic_epoch}'ten devam ediliyor")

    for epoch in range(baslangic_epoch, a.epoch):
        model.train()
        toplam, n = 0.0, 0
        for x, y in yk_e:
            x, y = x.to(cihaz, non_blocking=True), y.to(cihaz, non_blocking=True)
            iyilestirici.zero_grad(set_to_none=True)
            with torch.autocast(cihaz.type, dtype=torch.float16, enabled=cihaz.type == "cuda"):
                kayip = kayip_fn(model(x), y)
            olcek.scale(kayip).backward()
            olcek.step(iyilestirici)
            olcek.update()
            toplam += float(kayip.detach())
            n += 1
        zamanlayici.step()

        d_kayip, d_kc, d_tumor = dogrula(model, yk_d, cihaz, kayip_fn)
        gecen = (time.time() - baslangic) / 3600
        gecmis.append(dict(epoch=epoch + 1, egitim_kayip=toplam / max(n, 1),
                           dogrulama_kayip=d_kayip, dice_karaciger=d_kc, dice_tumor=d_tumor))
        print(f"epoch {epoch+1}/{a.epoch} kayip {toplam/max(n,1):.4f} | "
              f"dogrulama {d_kayip:.4f} Dice kc {d_kc:.3f} tumor {d_tumor:.3f} | "
              f"{gecen:.2f} sa", flush=True)

        durum = dict(cozucu=model.cozucu.state_dict(), iyilestirici=iyilestirici.state_dict(),
                     zamanlayici=zamanlayici.state_dict(), epoch=epoch + 1,
                     gecmis=gecmis, en_iyi=en_iyi, ayarlar=vars(a))
        torch.save(durum, ck)
        if not np.isnan(d_tumor) and d_tumor > en_iyi:
            en_iyi = d_tumor
            durum["en_iyi"] = en_iyi
            torch.save(durum, cikti / "en_iyi.pt")
        (cikti / "gecmis.json").write_text(json.dumps(gecmis, indent=2))

        if gecen > a.sure_siniri:
            print(f"\nSure siniri ({a.sure_siniri} sa) doldu. Checkpoint yazildi.")
            print("Ayni komutu tekrar calistirarak kaldigi yerden devam edebilirsin.")
            return

    print(f"\nEgitim bitti. En iyi tumor Dice (dogrulama): {en_iyi:.3f}")


if __name__ == "__main__":
    main()
