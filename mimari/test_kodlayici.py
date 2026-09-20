#!/usr/bin/env python3
"""V-JEPA 2 kodlayicisini gercek agirliklarla dogrular.

Veri indirmeden once calistirilir: agirliklar iniyor mu, token sayisi
bekledigimiz (t x h x w) ile uyusuyor mu, bellek ve hiz ne durumda?

Kullanim:
  python test_kodlayici.py --slab 16 --boyut 256 --batch 2
"""
import argparse
import time

import torch

from cozucu import DiceCEKaybi, Model
from kodlayici import VARSAYILAN_MODEL, VJepaKodlayici


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-adi", default=VARSAYILAN_MODEL)
    p.add_argument("--slab", type=int, default=16)
    p.add_argument("--boyut", type=int, default=256)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--adim", type=int, default=5, help="hiz olcumu icin ileri+geri gecis sayisi")
    a = p.parse_args()

    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"cihaz: {cihaz}")

    t0 = time.time()
    kodlayici = VJepaKodlayici(a.model_adi)
    print(f"kodlayici yuklendi ({time.time()-t0:.1f} sn): yama={kodlayici.yama} "
          f"tubelet={kodlayici.tubelet} boyut={kodlayici.cikti_boyutu}")

    model = Model(kodlayici).to(cihaz)
    egitilen = sum(p_.numel() for p_ in model.parameters() if p_.requires_grad)
    toplam = sum(p_.numel() for p_ in model.parameters())
    print(f"parametre: egitilen {egitilen/1e6:.1f} M / toplam {toplam/1e6:.1f} M")

    x = torch.rand(a.batch, 2, a.slab, a.boyut, a.boyut, device=cihaz)
    y = torch.randint(0, 3, (a.batch, a.slab, a.boyut, a.boyut), device=cihaz)

    with torch.no_grad(), torch.autocast(cihaz.type, dtype=torch.float16,
                                         enabled=cihaz.type == "cuda"):
        ozellik = model.kodlayici(x)
    print(f"kodlayici cikti bicimi: {tuple(ozellik.shape)}  "
          f"(beklenen: B={a.batch}, C={kodlayici.cikti_boyutu}, "
          f"t={a.slab//kodlayici.tubelet}, h=w={a.boyut//kodlayici.yama})")

    kayip_fn = DiceCEKaybi().to(cihaz)
    iyilestirici = torch.optim.AdamW([p_ for p_ in model.parameters() if p_.requires_grad], lr=1e-4)
    olcek = torch.amp.GradScaler(enabled=cihaz.type == "cuda")

    if cihaz.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    for i in range(a.adim):
        iyilestirici.zero_grad(set_to_none=True)
        with torch.autocast(cihaz.type, dtype=torch.float16, enabled=cihaz.type == "cuda"):
            kayip = kayip_fn(model(x), y)
        olcek.scale(kayip).backward()
        olcek.step(iyilestirici)
        olcek.update()
        if i == 0:
            print(f"ilk adim tamam, kayip {float(kayip.detach()):.4f}")
    if cihaz.type == "cuda":
        torch.cuda.synchronize()
    sure = (time.time() - t0) / a.adim

    print(f"\nadim suresi: {sure*1000:.0f} ms (batch {a.batch})")
    if cihaz.type == "cuda":
        print(f"tepe bellek: {torch.cuda.max_memory_allocated()/2**30:.1f} GiB")
    print(f"tahmini: 200 adimlik epoch ~ {sure*200/60:.1f} dk, 40 epoch ~ {sure*200*40/3600:.1f} saat")
    print("\nTEST BASARILI")


if __name__ == "__main__":
    main()
