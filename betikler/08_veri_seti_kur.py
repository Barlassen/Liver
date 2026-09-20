#!/usr/bin/env python3
"""AbdomenAtlas'tan temiz bir karaciger veri seti tanimlar (manifest uretir).

Bu betik goruntu indirmez; hangi vakanin hangi bolumde olacagini belirleyen
CSV'leri uretir. Indirme ve donusturme betikleri bu manifesti kullanir.

Kurallar:
  1. LiTS / MSD Task03 kokenli vakalar (07_lits_eslesme.py ciktisi) TAMAMEN
     dislanir -> LiTS, kendi uzman etiketleriyle harici test seti olarak kalir.
  2. RSNA Trauma bloku (ID >= 5196) ana kohortun disinda tutulur; istege bagli
     ikinci bir harici test olarak kullanilabilir (--rsna-harici).
  3. Bolunme hasta duzeyindedir. Ic test icin AbdomenAtlas'in hazir IID listesi
     kullanilir, dogrulama egitim havuzundan ayrilir.
  4. Tumorsuz vakalar da alinir; ozgulluk ancak boyle olculebilir.
  5. Indirilecek parca sayisi sinirlidir (Kaggle diski dar), bu yuzden tumorlu
     vaka bakimindan en zengin parcalar secilir.

Kullanim:
  python 08_veri_seti_kur.py --meta veri/AbdomenAtlas3.0MiniWithMeta.csv \
      --ids veri/TrainTestIDS --lits veri_seti/lits_kokenli.csv \
      --cikti veri_seti --parca-sayisi 6 --tumorsuz-orani 1.5
"""
import argparse
from pathlib import Path

import pandas as pd

PARCA = 232
RSNA_BASLANGIC = 5196
L = "number of liver lesion instances"
D = "largest liver lesion diameter (cm)"


def parca_dosyasi(indeks: int, tur: str) -> str:
    bas = indeks * PARCA + 1
    son = min((indeks + 1) * PARCA, 9262)
    return f"AbdomenAtlas3_{tur}_BDMAP_BDMAP_{bas:08d}_BDMAP_{son:08d}.tar.gz"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--meta", required=True)
    p.add_argument("--ids", required=True, help="TrainTestIDS klasoru")
    p.add_argument("--lits", required=True, help="lits_kokenli.csv")
    p.add_argument("--cikti", default="veri_seti")
    p.add_argument("--parca-sayisi", type=int, default=6)
    p.add_argument("--tumorsuz-orani", type=float, default=1.5,
                   help="tumorlu vaka basina kac tumorsuz vaka")
    p.add_argument("--dogrulama-orani", type=float, default=0.15)
    p.add_argument("--ic-test-tumor", type=int, default=60,
                   help="ic testte hedeflenen tumorlu vaka sayisi; IID listesi yetmezse havuzdan tamamlanir")
    p.add_argument("--rsna-harici", action="store_true",
                   help="RSNA blokundan ikinci bir harici test seti de tanimla")
    p.add_argument("--onceki", default=None,
                   help="onceki manifest (karaciger_vakalar.csv). Oradaki egitim vakalari "
                        "yeni bolunmede de egitimde, test vakalari testte kalir; boylece "
                        "iki veri boyutu ayni test setinde adil karsilastirilabilir")
    p.add_argument("--tohum", type=int, default=0)
    a = p.parse_args()

    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)

    m = pd.read_csv(a.meta).rename(columns={"BDMAP ID": "bdmap_id"})
    m["num"] = m.bdmap_id.str[6:].astype(int)
    m["parca"] = (m.num - 1) // PARCA
    m["tumor"] = m[L] > 0
    m["rsna"] = m.num >= RSNA_BASLANGIC

    lits = set(pd.read_csv(a.lits).bdmap_id)
    m["lits_kokenli"] = m.bdmap_id.isin(lits)

    ic_test_ids = set(pd.read_csv(Path(a.ids) / "IID_test.csv")["BDMAP ID"])
    m["iid_test"] = m.bdmap_id.isin(ic_test_ids)

    # Onceki bolunmeye sadakat: eski egitim vakasi yeni testte yer alamaz (ve tersi).
    onceki_egitim, onceki_test = set(), set()
    if a.onceki:
        o = pd.read_csv(a.onceki)
        onceki_egitim = set(o[o.split == "train"]["BDMAP ID"])
        onceki_test = set(o[o.split == "test"]["BDMAP ID"])
        m.loc[m.bdmap_id.isin(onceki_egitim), "iid_test"] = False
        m.loc[m.bdmap_id.isin(onceki_test), "iid_test"] = True
        print(f"onceki manifest: {len(onceki_egitim)} egitim, {len(onceki_test)} test vakasi sabitlendi")

    # --- uygun havuz --------------------------------------------------------
    havuz = m[~m.lits_kokenli & ~m.rsna].copy()

    # Tumorlu vaka bakimindan en zengin parcalar
    sira = (havuz[havuz.tumor].groupby("parca").size()
            .sort_values(ascending=False).head(a.parca_sayisi).index.tolist())
    havuz = havuz[havuz.parca.isin(sira)]

    tumorlu = havuz[havuz.tumor]
    hedef_tumorsuz = int(len(tumorlu) * a.tumorsuz_orani)
    tumorsuz = havuz[~havuz.tumor].sample(min(hedef_tumorsuz, (~havuz.tumor).sum()),
                                          random_state=a.tohum)
    secilen = pd.concat([tumorlu, tumorsuz]).sort_values("num")

    ic_test = secilen[secilen.iid_test]
    kalan = secilen[~secilen.iid_test].sample(frac=1.0, random_state=a.tohum)
    # IID listesi kucuk kalirsa havuzdan tamamla (yine hasta duzeyinde, ayrik).
    eksik_tumor = max(0, a.ic_test_tumor - int(ic_test.tumor.sum()))
    if eksik_tumor:
        # Onceki egitim vakalari teste alinamaz
        aday = kalan[~kalan.bdmap_id.isin(onceki_egitim)]
        ek_t = aday[aday.tumor].head(eksik_tumor)
        ek_s = aday[~aday.tumor].head(int(eksik_tumor * a.tumorsuz_orani))
        ic_test = pd.concat([ic_test, ek_t, ek_s])
        kalan = kalan[~kalan.bdmap_id.isin(ic_test.bdmap_id)]
    egitim_havuzu = kalan
    n_dog = int(len(egitim_havuzu) * a.dogrulama_orani)
    # Dogrulamada da tumorlu/tumorsuz dengesi korunsun
    dog_tumorlu = egitim_havuzu[egitim_havuzu.tumor].head(max(1, n_dog // 2))
    dog_tumorsuz = egitim_havuzu[~egitim_havuzu.tumor].head(n_dog - len(dog_tumorlu))
    dogrulama = pd.concat([dog_tumorlu, dog_tumorsuz])
    egitim = egitim_havuzu[~egitim_havuzu.bdmap_id.isin(dogrulama.bdmap_id)]

    sutunlar = ["bdmap_id", "parca", "tumor", L, D, "contrast", "spacing", "shape", "sex", "age"]
    for ad, df in [("egitim", egitim), ("dogrulama", dogrulama), ("ic_test", ic_test)]:
        df[sutunlar].sort_values("bdmap_id").assign(bolum=ad).to_csv(
            cikti / f"{ad}.csv", index=False)

    # 02_donustur.py'nin bekledigi birlesik liste (split sutunuyla)
    birlesik = pd.concat([
        egitim.assign(split="train"), dogrulama.assign(split="train"),
        ic_test.assign(split="test")])
    birlesik.rename(columns={"bdmap_id": "BDMAP ID"})[
        ["BDMAP ID", "split", "parca", "tumor"]].sort_values("BDMAP ID").to_csv(
        cikti / "karaciger_vakalar.csv", index=False)

    # Dislananlar (seffaflik icin)
    dislanan = m[m.lits_kokenli | (m.rsna if not a.rsna_harici else False)][["bdmap_id", "num", "tumor"]].copy()
    dislanan["neden"] = ["LiTS/MSD kokenli (harici teste ayrildi)" if r.bdmap_id in lits
                         else "RSNA Trauma blogu" for r in dislanan.itertuples()]
    dislanan.to_csv(cikti / "dislanan.csv", index=False)

    if a.rsna_harici:
        rsna = m[m.rsna & m.tumor]
        rsna[sutunlar].assign(bolum="rsna_harici").to_csv(cikti / "rsna_harici.csv", index=False)

    # Indirme plani: yalnizca gereken parcalar
    plan = pd.DataFrame({"parca": sorted(sira)})
    plan["goruntu"] = plan.parca.map(lambda i: parca_dosyasi(i, "images"))
    plan["maske"] = plan.parca.map(lambda i: parca_dosyasi(i, "masks"))
    plan["secilen_vaka"] = plan.parca.map(secilen.groupby("parca").size()).fillna(0).astype(int)
    plan.to_csv(cikti / "indirme_plani.csv", index=False)

    ozet = f"""# Veri seti ozeti

| Bolum | Vaka | Tumorlu | Tumorsuz |
|---|---|---|---|
| Egitim | {len(egitim)} | {int(egitim.tumor.sum())} | {int((~egitim.tumor).sum())} |
| Dogrulama | {len(dogrulama)} | {int(dogrulama.tumor.sum())} | {int((~dogrulama.tumor).sum())} |
| Ic test | {len(ic_test)} | {int(ic_test.tumor.sum())} | {int((~ic_test.tumor).sum())} |
| **Harici test (LiTS)** | 131 | 131 | 0 |

- Dislanan LiTS/MSD kokenli vaka: {len(lits)}
- Kullanilan parca: {sorted(sira)} (toplam {len(sira)} x ~14 GB goruntu + ~0,3 GB maske)
- Tumor boyut dagilimi (egitim): {egitim[egitim.tumor][D].describe()[['min','50%','max']].round(1).to_dict()}
"""
    (cikti / "OZET.md").write_text(ozet)
    print(ozet)
    print(f"Dosyalar: {cikti}/egitim.csv, dogrulama.csv, ic_test.csv, "
          f"karaciger_vakalar.csv, dislanan.csv, indirme_plani.csv")


if __name__ == "__main__":
    main()
