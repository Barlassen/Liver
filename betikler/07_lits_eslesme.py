#!/usr/bin/env python3
"""LiTS / MSD Task03 vakalarini AbdomenAtlas icinde bulur.

AbdomenAtlas'in hangi vakasinin hangi acik veri setinden geldigini gosteren
resmi bir eslesme tablosu yok. Ama AbdomenAtlas goruntuleri yeniden
orneklenmemis: hacim boyutu (shape) + voksel araligi (spacing) ikilisi bir
parmak izi gorevi goruyor.

Bu betik MSD Task03_Liver arsivini INDIRMEDEN, yalnizca HTTP aralik
istekleriyle her dosyanin NIfTI basligini okur (dosya basina ~2 KB) ve
AbdomenAtlas metadata'siyla eslestirir.

Cikti: lits_kokenli.csv  ->  eslesen BDMAP ID'leri (egitimden dislanacak)

Kullanim:
  python 07_lits_eslesme.py --meta veri/AbdomenAtlas3.0MiniWithMeta.csv --cikti veri_seti
"""
import argparse
import struct
import urllib.request
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

TAR_URL = "https://msd-for-monai.s3-us-west-2.amazonaws.com/Task03_Liver.tar"


def _ssl_baglami():
    """Bazi Python kurulumlarinda kok sertifikalar eksik olur; certifi varsa onu kullan."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


_BAGLAM = _ssl_baglami()


def aralik_oku(url: str, bas: int, uzunluk: int) -> bytes:
    istek = urllib.request.Request(url, headers={"Range": f"bytes={bas}-{bas + uzunluk - 1}"})
    with urllib.request.urlopen(istek, timeout=60, context=_BAGLAM) as y:
        return y.read()


def nifti_basligi(ham: bytes):
    """gzip'li NIfTI'nin ilk baytlarindan (boyut, aralik) cikarir."""
    cozucu = zlib.decompressobj(16 + zlib.MAX_WBITS)
    bas = cozucu.decompress(ham, 400)
    if len(bas) < 352:
        raise ValueError("baslik eksik")
    kucuk = struct.unpack("<h", bas[40:42])[0] in range(1, 8)
    e = "<" if kucuk else ">"
    dim = struct.unpack(e + "8h", bas[40:56])
    pixdim = struct.unpack(e + "8f", bas[76:108])
    return tuple(int(x) for x in dim[1:4]), tuple(round(float(x), 6) for x in pixdim[1:4])


def tar_gez(url: str, klasor_filtresi: str = "imagesTr"):
    """Tar arsivini aralik istekleriyle gezer, eslesen uyelerin NIfTI basligini dondurur."""
    konum, sonuclar = 0, []
    bos_blok = 0
    while True:
        blok = aralik_oku(url, konum, 512)
        if len(blok) < 512:
            break
        if blok == b"\0" * 512:
            bos_blok += 1
            if bos_blok == 2:          # arsiv sonu
                break
            konum += 512
            continue
        bos_blok = 0
        ad = blok[:100].rstrip(b"\0").decode("utf-8", "replace")
        boyut = int(blok[124:136].rstrip(b"\0 ").decode() or "0", 8)
        tur = blok[156:157]
        veri = konum + 512
        if tur in (b"0", b"\0") and ad.endswith(".nii.gz") and klasor_filtresi in ad \
                and "._" not in ad:
            try:
                shape, aralik = nifti_basligi(aralik_oku(url, veri, min(4096, boyut)))
                sonuclar.append(dict(dosya=ad.split("/")[-1], shape=shape, aralik=aralik))
                if len(sonuclar) % 20 == 0:
                    print(f"  {len(sonuclar)} dosya okundu", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"  UYARI {ad}: {e}")
        konum = veri + (boyut + 511) // 512 * 512
    return sonuclar


def meta_parmak_izi(meta: pd.DataFrame) -> pd.DataFrame:
    def ayir_shape(s):
        return tuple(int(x) for x in str(s).strip("()").split(","))

    def ayir_aralik(s):
        return tuple(round(float(x), 6) for x in str(s).strip("[]").split())

    m = meta.copy()
    m["shape_t"] = m["shape"].map(ayir_shape)
    m["aralik_t"] = m["spacing"].map(ayir_aralik)
    return m


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--meta", required=True)
    p.add_argument("--cikti", default="veri_seti")
    p.add_argument("--tolerans", type=float, default=1e-3)
    a = p.parse_args()

    print("MSD Task03_Liver basliklari okunuyor (arsiv indirilmiyor)...")
    lits = tar_gez(TAR_URL)
    print(f"{len(lits)} LiTS hacminin basligi okundu")

    meta = meta_parmak_izi(pd.read_csv(a.meta))
    satirlar = []
    for kayit in lits:
        aday = meta[meta.shape_t == kayit["shape"]]
        eslesen = [r for r in aday.itertuples()
                   if np.allclose(r.aralik_t, kayit["aralik"], atol=a.tolerans)]
        satirlar.append(dict(
            lits_dosya=kayit["dosya"], shape=str(kayit["shape"]), aralik=str(kayit["aralik"]),
            eslesme_sayisi=len(eslesen),
            bdmap_id=eslesen[0]._asdict()["_1"] if len(eslesen) == 1 else "",
            adaylar=";".join(r._asdict()["_1"] for r in eslesen) if len(eslesen) > 1 else ""))

    df = pd.DataFrame(satirlar)
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    df.to_csv(cikti / "lits_eslesme_detay.csv", index=False)

    kesin = df[df.eslesme_sayisi == 1]
    coklu = df[df.eslesme_sayisi > 1]
    yok = df[df.eslesme_sayisi == 0]

    dislanacak = set(kesin.bdmap_id) | {x for s in coklu.adaylar for x in s.split(";") if x}
    pd.DataFrame(sorted(dislanacak), columns=["bdmap_id"]).to_csv(
        cikti / "lits_kokenli.csv", index=False)

    print("\n--- Ozet ---")
    print(f"tek eslesme  : {len(kesin)}")
    print(f"coklu aday   : {len(coklu)} (hepsi temkinli sekilde dislanir)")
    print(f"eslesme yok  : {len(yok)}")
    print(f"dislanacak BDMAP ID sayisi: {len(dislanacak)}")
    print(f"\nDosyalar: {cikti/'lits_kokenli.csv'}, {cikti/'lits_eslesme_detay.csv'}")


if __name__ == "__main__":
    main()
