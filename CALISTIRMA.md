# 22 Eylül'e kadar çalıştırma planı (Lambda)

**Bugün:** 20 Eylül · **Deadline:** 22 Eylül · **Kalan:** ~48 saat

Hedef: **V-JEPA 2 tabanlı bir segmentasyon sonucu** + karşılaştırma kolları + harici doğrulama.

---

## Üç kol

| Kol | Ne | Neden |
|---|---|---|
| **A. V-JEPA 2 (dondurulmuş) + 3B çözücü** | Asıl sonuç | Ario'nun istediği JEPA sonucu. Meta'nın açık ağırlıkları, MIT lisans |
| **B. Aynı mimari, rastgele kodlayıcı** | Ablasyon | **"V-JEPA ön eğitimi ne kazandırıyor?"** sorusunun doğrudan cevabı. Abstract'ın en güçlü cümlesi buradan çıkar |
| **C. nnU-Net** | Baseline | Alanın standardı. Hakem mutlaka sorar |

Üçü de aynı veri, aynı hasta düzeyi ayrımı, aynı metriklerle ölçülür. Ayrıca her biri
hem **iç testte** hem **LiTS harici testinde** değerlendirilir.

---

## Zaman çizelgesi

| Saat | İş | Nerede |
|---|---|---|
| 0–1 | Makine kur, depoyu klonla, ortamı hazırla | Lambda |
| 1–2 | 6 parça indir (~85 GB) + aç | Lambda |
| 2–3 | Dönüştür (02) + kalite kontrol (03) | Lambda, CPU |
| 3–4 | LiTS indir ve hazırla (09, ~27 GB) | Lambda, CPU |
| 4–12 | **Kol A eğitimi** (V-JEPA + çözücü, ~40 epoch) | Lambda GPU |
| 4–14 | **Kol C** nnU-Net (250 epoch, tek fold) — ikinci GPU varsa paralel | Lambda GPU |
| 12–18 | **Kol B** ablasyon (rastgele kodlayıcı, aynı ayarlar) | Lambda GPU |
| 18–20 | Üç kol için tahmin + metrikler (iç test + LiTS) | Lambda |
| 20–24 | Abstract yazımı | — |

Kol B, Kol A ile aynı süreyi alır; tek GPU varsa A bittikten sonra başlatılır.
Zaman daralırsa **B'nin epoch sayısı düşürülür**, çünkü A + C zaten abstract'ı taşır.

---

## Komutlar (sırayla)

```bash
# 0. Makinede
git clone https://github.com/Barlassen/Liver.git && cd Liver
bash betikler/00_kurulum.sh /mnt/veri
source /mnt/veri/ortam.sh

# 1. AbdomenAtlas: yalnizca secilen 6 parca
bash betikler/01_indir.sh /mnt/veri "5 6 7 8 18 20"

# 2. Donusum + kalite kontrol
python betikler/02_donustur.py --ham /mnt/veri/ham --cikti /mnt/veri/nnUNet_raw \
       --vakalar veri_seti/karaciger_vakalar.csv
python betikler/03_kalite_kontrol.py --raw /mnt/veri/nnUNet_raw \
       --meta /mnt/veri/ham/AbdomenAtlas3.0MiniWithMeta.csv

# 3. Egitim formatina kucult (.npz) + LiTS harici test
python betikler/06_kaggle_hazirla.py --raw /mnt/veri/nnUNet_raw --cikti /mnt/veri/veri \
       --envanter /mnt/veri/nnUNet_raw/Dataset001_LiverTumor/envanter.csv
python betikler/09_lits_hazirla.py --cikti /mnt/veri/harici_lits --format npz

# 4. KOL A: V-JEPA 2 + cozucu
python mimari/egit.py --egitim /mnt/veri/veri/train --dogrulama /mnt/veri/veri/val \
       --cikti /mnt/veri/kol_a --epoch 40 --sure-siniri 9

# 5. KOL B: ablasyon (ayni ayarlar, on egitim yok)
python mimari/egit.py --egitim /mnt/veri/veri/train --dogrulama /mnt/veri/veri/val \
       --cikti /mnt/veri/kol_b --epoch 40 --sure-siniri 9 --rastgele-kodlayici

# 6. KOL C: nnU-Net baseline
bash betikler/05_egit.sh /mnt/veri nnUNetTrainer_250epochs

# 7. Tahmin + metrikler (her kol icin, ic test ve LiTS ayri ayri)
for kol in kol_a kol_b; do
  for set in "/mnt/veri/veri/test ic" "/mnt/veri/harici_lits lits"; do
    read -r yol ad <<< "$set"
    python mimari/tahmin.py --vakalar "$yol" --checkpoint /mnt/veri/$kol/en_iyi.pt \
           --cikti /mnt/veri/$kol/tahmin_$ad $( [ $kol = kol_b ] && echo --rastgele-kodlayici )
    python betikler/04_degerlendir.py --gt "$yol" --tahmin /mnt/veri/$kol/tahmin_$ad \
           --cikti /mnt/veri/$kol/metrik_$ad
  done
done
```

---

## Makine seçimi (Lambda)

| İhtiyaç | Öneri |
|---|---|
| GPU | 1× A100 40/80 GB ya da 1× H100. İki GPU alınabiliyorsa A ve C paralel koşar |
| Disk | **En az 400 GB.** AbdomenAtlas 85 GB + açılmış hali + LiTS 27 GB + nnU-Net ön işleme |
| Kalıcılık | Veri ve checkpoint'ler **persistent filesystem**'e yazılmalı; makine silinince yerel disk gider |
| Bölge | Persistent filesystem ile makine **aynı bölgede** olmalı |

Makine durdurulamıyor, yalnızca siliniyor. İş bitince sil, kredi boşa akmasın.

---

## Riskler ve B planı

| Risk | B planı |
|---|---|
| V-JEPA 2 ağırlıkları inmezse / uyumsuzsa | `--sahte-kodlayici` ile boru hattı zaten doğrulandı; ViT-L yerine daha küçük V-JEPA 2 varyantına düşülür |
| Eğitim yavaş kalırsa | Epoch sayısı düşürülür; `en_iyi.pt` her epoch'ta yazıldığı için elde her zaman bir sonuç olur |
| nnU-Net yetişmezse | Abstract A + B ile gönderilir. Ablasyon, baseline'dan daha ilginç bir karşılaştırmadır |
| Tümör Dice düşük çıkarsa | Sonuç dürüstçe raporlanır: lezyon **tespit** duyarlılığı ve hasta düzeyi AUC öne çıkarılır; segmentasyon ikinci planda kalır |
