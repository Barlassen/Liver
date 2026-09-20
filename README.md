# Liver — AbdomenAtlas 3.0'dan karaciğer tümörü veri seti ve modeller

CT'de karaciğer tümörü **tespiti ve segmentasyonu**. Model çıktısı voksel başına
`0 = arka plan`, `1 = karaciğer`, `2 = tümör`.

Bu depo iki şeyi içerir:
1. **AbdomenAtlas 3.0'ı eğitime hazır hale getiren temiz bir veri seti tanımı** (manifest + betikler)
2. **Modeller:** nnU-Net baseline ve dondurulmuş V-JEPA 2 kodlayıcısı üzerine kurulu segmentasyon mimarisi

Ayrıntılı bağlam için [HANDOFF.md](HANDOFF.md), mimari için [MIMARI-PLANI.md](MIMARI-PLANI.md).

---

## Veri seti tasarımı

| Bölüm | Kaynak | Vaka | Tümörlü | Tümörsüz |
|---|---|---|---|---|
| Eğitim | AbdomenAtlas 3.0 | 657 | 253 | 404 |
| Doğrulama | AbdomenAtlas 3.0 | 115 | 57 | 58 |
| İç test | AbdomenAtlas 3.0 | 153 | 60 | 93 |
| **Harici test** | **LiTS (orijinal, uzman etiketli)** | 131 | 131 | 0 |

Sayılar `--parca-sayisi 6` içindir ve `veri_seti/OZET.md` dosyasında tutulur.

### Tasarım kuralları

1. **LiTS / MSD Task03 kökenli vakalar eğitimden tamamen çıkarıldı.** LiTS, kendi uzman
   etiketleriyle harici test seti olarak kullanılıyor. AbdomenAtlas'ın kaynak eşleme
   tablosu yayımlanmadığı için bu vakalar boyut + voksel aralığı parmak iziyle bulundu
   (`betikler/07_lits_eslesme.py`).
2. **Bölünme hasta düzeyinde.** Aynı hastanın hiçbir verisi iki bölümde birden bulunmuyor.
3. **Tümörsüz hastalar dahil.** Aksi halde özgüllük (specificity) ölçülemez.
4. **RSNA Trauma bloğu (ID ≥ 5196) ana kohortun dışında.** İsteğe bağlı ikinci bir harici
   test olarak kullanılabilir (`--rsna-harici`).
5. **Hiçbir vaka sessizce silinmiyor.** Dışlananlar `veri_seti/dislanan.csv` içinde
   gerekçesiyle duruyor; kalite kontrol sonuçları `envanter.csv`'ye yazılıyor.

### ⚠️ Bulgular

- **AbdomenAtlas, MSD ve LiTS'i içeriyor** (945 + 131 tarama). Bu yüzden MSD, üzerinde
  değişiklik yapılmadan harici doğrulama olarak kullanılamaz.
- **LiTS taramalarının çoğu AbdomenAtlas'ta iki kez bulunuyor** — bir kez LiTS, bir kez
  MSD Task03 girişi olarak, farklı BDMAP ID'leriyle. 97 çift adayın 92'sinde iki kaydın
  karaciğer hacmi %2'den az farklı. Bu, veri setinin kendi içinde eğitim/test sızıntısı
  riski taşıdığı anlamına gelir; her iki kopya da dışlandı.
- **CT ile maske aynı ızgarada geliyor.** Dönüştürülen 918 vakanın tamamı birebir eşleşti.
  Metadata'daki `shape` sütunu kırpma öncesi orijinal boyutu gösterdiği için başta uyumsuzluk
  sanılmıştı; gerçekte dosyalar tutarlı. Dönüştürme betiği yine de affine farkını ele alıyor:
  voksel aralığı veya yönelimi uyuşmayan 7 vaka hata olarak işaretlenip dışlandı.

---

## Kullanım

### 1. Veri setini tanımla (indirme gerekmez)

```bash
python betikler/07_lits_eslesme.py --meta veri/AbdomenAtlas3.0MiniWithMeta.csv --cikti veri_seti
python betikler/08_veri_seti_kur.py --meta veri/AbdomenAtlas3.0MiniWithMeta.csv \
       --ids veri/TrainTestIDS --lits veri_seti/lits_kokenli.csv --cikti veri_seti --parca-sayisi 6
```

### 2. Görüntüleri indir ve dönüştür (disk: ~300 GB)

```bash
bash   betikler/00_kurulum.sh /mnt/veri
bash   betikler/01_indir.sh   /mnt/veri 6
python betikler/02_donustur.py --ham /mnt/veri/ham --cikti /mnt/veri/nnUNet_raw \
       --vakalar veri_seti/karaciger_vakalar.csv
python betikler/03_kalite_kontrol.py --raw /mnt/veri/nnUNet_raw \
       --meta veri/AbdomenAtlas3.0MiniWithMeta.csv
```

### 3. Harici test setini hazırla (LiTS, ~27 GB indirme)

```bash
python betikler/09_lits_hazirla.py --cikti /mnt/veri/harici_lits --format npz
```

LiTS etiket düzeni bizimkiyle birebir aynı (`1 = karaciğer`, `2 = tümör`), dönüştürme
gerekmiyor. Çıktı `LITS_0000.npz` biçiminde, eğitim verisiyle aynı formatta.

### 4. Kaggle için küçült (~10 GB)

```bash
python betikler/06_kaggle_hazirla.py --raw /mnt/veri/nnUNet_raw --cikti /mnt/veri/kaggle \
       --envanter /mnt/veri/nnUNet_raw/Dataset001_LiverTumor/envanter.csv
```

### 5. Eğit

```bash
bash betikler/05_egit.sh /mnt/veri                     # nnU-Net baseline
python mimari/egit.py --egitim .../train --dogrulama .../val \
       --cikti .../vjepa --epoch 40 --sure-siniri 8.0  # V-JEPA 2 + çözücü
```

### 6. Değerlendir

```bash
python betikler/04_degerlendir.py --gt .../labelsTs --tahmin .../tahmin --cikti .../metrik
```

Metrikler: Dice ve HD95 (karaciğer, tümör) · lezyon duyarlılığı · hasta başına yanlış
pozitif · boyuta göre duyarlılık (<1 cm / 1–2 cm / >2 cm) · hasta düzeyi duyarlılık,
özgüllük ve AUC.

---

## Klasörler

```
veri/        AbdomenAtlas metadata'sı ve hazır ayrım listeleri
veri_seti/   Üretilen manifestler: egitim.csv, dogrulama.csv, ic_test.csv,
             dislanan.csv, lits_kokenli.csv, indirme_plani.csv, OZET.md
betikler/    Veri hattı: indirme, dönüştürme, kalite kontrol, değerlendirme
mimari/      V-JEPA 2 kodlayıcı + 3B çözücü, eğitim ve çıkarım
```

## Lisans notu

AbdomenAtlas 3.0: **CC-BY-NC-SA-4.0** — akademik kullanım serbest, ticari kullanım yasak.
Ürünleştirme aşamasında bu ayrım kritik.
