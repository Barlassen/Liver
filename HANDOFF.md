# Karaciğer CT Projesi — Devir Notu (Handoff)

**Son güncelleme:** 20 Eylül 2026
**Deadline:** **22 Eylül 2026** (saat dilimi henüz doğrulanmadı)
**Sorumlu:** Barlas Şen (karaciğer) · Oktay Yüce (pankreas)
**Ekip:** Ariorad Vivax (mimari, GPU kaynakları) · Ege Şeker (koordinasyon, veri seti seçimi)
**Eşlik eden doküman:** `proje-ogrenimi.md` (tıbbi ve teknik terimlerin sıfırdan anlatımı, MRI dönemine ait)

---

## 1. Projenin amacı

> **Karın CT'sine bakıp karaciğerdeki tümörleri otomatik bulan (tespit) ve sınırlarını çizen (segmentasyon) bir model eğitmek; bu modelin alanın standardı olan nnU-Net'e göre ne durumda olduğunu ölçmek.**

Model çıktısı voksel başına üç etiket: `0 = arka plan`, `1 = karaciğer`, `2 = tümör`.
Aynı çıktıdan iki iş birden yapılır:
- **Segmentasyon:** tümör sınırları nerede
- **Tespit:** tümör var mı, kaç tane, nerede (maskedeki kopuk parçalar ayrı lezyon sayılır)

**Klinik gerekçe:** küçük lezyonlar gözden kaçabiliyor; tümör hacmi elle ölçülüyor ve uzun sürüyor; girişimsel işlemlerde (biyopsi, ablasyon) iğne hedefi tümörün yerine göre belirleniyor. Vivax'ın uzun vadeli ilgisi bu sonuncusunda.

**Büyük resim:**

| Şimdi (deadline için) | Sonra (asıl hedef) |
|---|---|
| CT, karaciğer tümörü (Barlas) + pankreas (Oktay) | MRI, pankreas, sekanslar arası sentez |
| "Mimari çalışıyor mu?" | "Girişimsel planlamaya yarıyor mu?" |

---

## 2. Proje nasıl buraya geldi

1. **Başlangıç (MRI fikri):** Aynı hastanın T1W MRI'ından T2W MRI'ını üretmek ve sentetik görüntüye göre iğne planlansaydı kaç mm sapılacağını ölçmek ("hedef kayması" metriği). Ayrıntılar `proje-ogrenimi.md` dosyasında.
2. **16 Eylül'de pivot:** Deadline yaklaştığı için MRI rafa kaldırıldı. Ege: *"ddl yakın, MRI yerine CT ile prelim sonuçları verelim"*. CT'de eğit, CT'de test et.
3. **Görev paylaşımı:** Barlas karaciğer (öncelikli), Oktay pankreas. Ario: *"Liver çıksın, en azından biri yeterli"*. İkisi de iyi çıkarsa ikisi de gönderilir.

**CT neden daha kolay:** HU değerleri standart (MRI yoğunlukları değil), veri bol, kesitler ince, solunum/kayıt sorunu yok.

---

## 3. Veri

### 3.1 AbdomenAtlas 3.0 Mini (ana veri seti)

- **Kaynak:** https://huggingface.co/datasets/AbdomenAtlas/AbdomenAtlas3.0Mini
- **Lisans:** CC-BY-NC-SA-4.0 → akademik yayın serbest, **ticari kullanım yasak** (Vivax ürün yol haritası için önemli)
- **İçerik:** 9.262 karın CT'si, 18 organ maskesi, karaciğer/böbrek/pankreas tümör maskeleri, damar maskeleri, radyoloji raporları

| Bölüm | Boyut |
|---|---|
| Görüntüler | ~571 GB (40 parça × ~14 GB, her parçada 232 vaka) |
| Maskeler | ~13 GB |
| Raporlar (PDF) | ~2 GB |
| Metadata CSV | 16 MB (`veri/AbdomenAtlas3.0MiniWithMeta.csv`) |
| Hazır ayrımlar | `veri/TrainTestIDS/` (IID ve OOD) |

### 3.2 Metadata analizinden çıkanlar (yapıldı)

| Bulgu | Değer |
|---|---|
| Karaciğer tümörlü hasta | **1.470** |
| Tümörsüz hasta | 7.792 (özgüllük ölçümü için bol kaynak) |
| IID test ayrımında | 131 tümörlü + 795 tümörsüz |
| Hasta başına lezyon sayısı | ortanca 1, maksimum 176 |
| En büyük lezyon çapı | <1 cm: 206 · 1–2 cm: 399 · 2–5 cm: 508 · ≥5 cm: 357 |
| Lezyon görünümü | %90 hipodans |
| Kontrast fazı | Hastaların %87'sinde kayıtlı **değil** → faza göre analiz yapılamaz |
| ID 5196 ve sonrası | RSNA Trauma verisi, karaciğer tümörü çok az |

Tümörlü vakalar ilk 22 parçaya (ID 1–5104) neredeyse eşit dağılmış, yani az parça indirip tümörlerin çoğunu almak mümkün değil.

| İndirme seçeneği | Boyut | Tümörlü (train/test) | Gereken disk |
|---|---|---|---|
| 6 parça | ~83 GB | 312 / 37 | ~300 GB |
| **12 parça (seçilen)** | **~167 GB** | **~683 / ~61** | **~500 GB** |
| 22 parça | ~306 GB | ~1.240 / ~128 | ~1 TB |

### 3.3 ⚠️ Veri sızıntısı: MSD dış doğrulama olamaz

AbdomenAtlas'ın ID 1–5195 aralığı, **MSD ve LiTS dahil 17 açık veri setinin birleşimi**. Yani MSD Liver hastaları eğitim verisinin içinde. Metadata'da kaynak veri setini gösteren sütun da yok, ayıklanamıyor.

Seçenekler: (a) dış doğrulamayı atlayıp yalnızca IID test sonucunu vermek — deadline için en makulü; (b) AbdomenAtlas'ta olmayan bir set bulmak (örn. TCIA / HCC-TACE-Seg, doğrulanmalı); (c) OOD ayrımını kullanmak (farklı hastaneler, ama karaciğer tümörlü vaka sayısı sınırlı).

### 3.4 ⚠️ Maske yapısı ve ızgara farkı (20 Eylül'de çözüldü)

Bir maske parçası indirilip incelendi. Yapı şöyle:

```
BDMAP_XXXXXXXX/segmentations/liver.nii.gz         (ikili, int8, 0/1)
BDMAP_XXXXXXXX/segmentations/liver_lesion.nii.gz  (ikili, int8, 0/1)
+ 40 kadar başka organ, damar ve karaciğer alt segment maskesi
```

**Kritik bulgu: maske hacmi CT ile aynı ızgarada olmayabiliyor.** Örnek: `BDMAP_00000001` için CT `(512, 512, 339)` iken maske `(511, 404, 339)`. Maske kırpılmış, farkı affine'in kaydırma kısmı taşıyor. nnU-Net görüntü ve etiketin birebir aynı boyutta olmasını şart koşar, bu yüzden dönüştürme betiği maskeyi affine'e bakarak CT ızgarasına geri oturtuyor. Voksel aralığı veya yönelim farklıysa vaka dönüştürülmüyor, raporda hata olarak işaretleniyor.

**Doğrulama:** `BDMAP_00000001` için maskeden hesaplanan karaciğer hacmi 1300,8 cm³, metadata'da yazan 1291,3 cm³ (%0,7 fark). Lezyon sayısı 27'ye karşı 25, en büyük çap 3,37 cm'e karşı 3,1 cm. Küçük farklar bağlantılılık (connectivity) tanımından geliyor, beklenen düzeyde.

### 3.5 Diğer veri setleri

- **PaNSegNet** (https://github.com/NUBagciLab/PaNSegNet): pankreas, Oktay'ın işi
- **MSD Liver**: yukarıdaki nedenle dış doğrulama olarak kullanılamaz

---

## 4. Modeller

### 4.1 Karar: JEPA sıfırdan eğitilmeyecek

Ario'nun "yeni mimari"si büyük ihtimalle JEPA tabanlı. 20 Eylül'de yapılan internet araştırmasının sonucu:

- **Karın CT'si üzerinde önceden eğitilmiş, indirilebilir hiçbir JEPA yok.**
- 3B CT'de JEPA ile segmentasyon yapıp nnU-Net'le karşılaştıran **hiçbir yayın yok** (fırsat, ama 3 günde riskli).

| JEPA seçeneği | Durum |
|---|---|
| **V-JEPA 2** (Meta, MIT lisans, açık) | En pratik JEPA yolu. CT kesitleri video karesi gibi verilir. **Decoder sıfırdan yazılmalı** → deadline için riskli |
| NeuroVFM | 3B, beyin MR/CT, başvuruyla erişim, ticari kullanım yasak |
| DALE-CT | Göğüs CT, 2B, erişim belirsiz |
| MedJEPA, Seg-JEPA, Rad-JEPA | Ağırlık yayımlanmamış |

### 4.2 Kullanılacak modeller

| Model | Rol | Notlar |
|---|---|---|
| **nnU-Net** | **Baseline** | Alanın standardı. Hakemin ilk soracağı kıyas |
| **Merlin** (Stanford, Nature 2026) | **Önerilen ikinci kol** | MIT lisans. nnU-Net'e takılan hazır trainer var (`Merlin-nnUNet`, `nnUNetTrainerMerlin`). Stanford verisiyle eğitilmiş → **sızıntı riski en düşük**. Az etiketle nnU-Net'i 4,7 Dice geçtiği raporlanmış |
| VoCo | Alternatif | nnU-Net entegrasyonu var, MSD Liver tümöründe 70,1 vs 67,4. **Ön eğitiminde AbdomenAtlas görüntüleri var**, raporda belirtilmeli |
| **SuPreM, AtlasNet** | ❌ **Kullanmayın** | Doğrudan bizim test görüntülerimizle eğitilmişler |

### 4.3 "Alibaba'nın modeli"

Büyük ihtimalle **DAMO RADAR** (Science, 18 Eylül 2026). Bir vizyon-dil sınıflandırıcısı, **maske üretmiyor** → karaciğer segmentasyonu için yedek olamaz. Karaciğer maskesi gerekirse TotalSegmentator kullanılır.

---

## 5. Hesaplama kaynakları

| Kaynak | Durum |
|---|---|
| **Lambda.ai** | **Şu anki plan.** Ario'nun birkaç yüz dolarlık kredisi var, erişim ondan isteniyor |
| **Azure** ("Vivax Azure subscription") | Rol: Katkıda bulunan. GPU kotaları 0'dı, 19 Eylül'de kota talebi açıldı (talep no `2609180050003354`). Basic destek + Severity C → iş saatlerinde bakılıyor, pazartesiye kalabilir |
| AWS pod'ları | GPU kota sorunu var |

**Talep edilen Azure kotaları (West Europe):** NC A100 v4 → 24 vCPU · NVADSA10v5 → 36 vCPU · toplam bölgesel → 60

**Lambda'nın Azure'dan farkları:**
- Makine **durdurulamaz**, yalnızca silinir. Var olduğu sürece ücret işler
- Makine silinince yerel disk **silinir** → veri ve modeller **persistent filesystem**'e yazılmalı (aynı bölgede)
- Lambda Stack ile PyTorch, CUDA ve sürücüler hazır gelir
- Ucuz makinede indirme/ön işleme yapıp yalnızca eğitim için A100 açmak krediyi korur

---

## 6. Deney tasarımı

### 6.1 Ayrım
Hasta düzeyinde (aynı hastanın tüm kesitleri tek bölümde). AbdomenAtlas'ın hazır **IID** listesi kullanılacak; herkes aynı listeyi kullanmalı.

### 6.2 Metrikler

| Tür | Metrik |
|---|---|
| Segmentasyon | Dice (karaciğer ve tümör ayrı), HD95 (mm) |
| Tespit, lezyon düzeyi | Duyarlılık, hasta başına yanlış pozitif, **boyuta göre duyarlılık** (<1 cm / 1–2 cm / >2 cm) |
| Tespit, hasta düzeyi | Duyarlılık, özgüllük, AUC |
| Girişimsel açı (opsiyonel) | Tümör merkezi kayması (mm) |

⚠️ **Test setine tümörsüz hastalar da girmeli**, yoksa özgüllük ölçülemez ve model her hastaya "tümör var" dese bile başarılı görünür.

### 6.3 Süre tahminleri (1× A100)

| Adım | Süre | GPU |
|---|---|---|
| Veri indirme (~170 GB) | 0,5–2 sa | Hayır |
| Açma + nnU-Net formatına dönüştürme | 1–2 sa | Hayır |
| nnU-Net ön işleme | 1–3 sa | Hayır |
| Eğitim (tek fold, ~250 epoch) | 6–10 sa | Evet |
| Eğitim (tek fold, 1000 epoch) | 1–2 gün | Evet |
| Test tahmini | 0,5–1 sa | Evet |
| Metrikler | dakikalar | Hayır |

**Kısaltma yolları:** tek fold (varsayılan 5 fold süreyi 5'e katlar), 250 epoch, GPU'suz adımları ucuz makinede yapmak.

---

## 7. Deadline planı (22 Eylül)

| Gün | İş |
|---|---|
| **20 Eylül (bugün)** | Lambda erişimi. Veri indirme, dönüştürme, nnU-Net ön işleme. Akşam eğitimi başlat |
| **21 Eylül** | İki eğitim paralel: nnU-Net baseline + Merlin. Bittikçe test tahmini ve metrikler |
| **22 Eylül** | Abstract yazımı ve gönderim. **Saat dilimini kontrol et** |

**Abstract'ın iddiası:** "Önceden eğitilmiş bir temel model, nnU-Net ile karşılaştırıldığında karaciğer tümörü tespit ve segmentasyonunda şu sonucu verdi." Sonuçlar Dice, HD95, lezyon duyarlılığı ve boyut kırılımıyla verilir.

**Abstract'tan çıkarılacak iddia:** "Sentetik/ikinci sekans segmentasyonu iyileştirir" — nnU-Net'te gerçek ikinci sekans bile yalnızca +0,0021 kazandırıyor (`proje-ogrenimi.md` §10.2).

---

## 8. Açık sorular (Ario'ya)

1. **22 Eylül'e JEPA sonucu şart mı?** Kamuya açık karın CT'si JEPA ağırlığı yok; 3 günde V-JEPA 2'ye decoder yazmak riskli. Öneri: nnU-Net + Merlin ile sonuç çıkarmak, JEPA'yı late-breaking'e bırakmak.
2. **Yeni mimarinin iddiası ne?** Daha az etiketle aynı başarı mı, daha yüksek doğruluk mu, küçük lezyonlarda daha iyi tespit mi? Cevap deney tasarımını değiştirir (örn. etiketin %10/%25/%100'üyle ayrı eğitimler).
3. **Hazır ağırlık var mı?** Varsa ince ayar yarım–bir gün; yoksa sıfırdan ön eğitim günler sürer ve krediyi tüketir.
4. Lambda erişimi ve hangi bölge.

**Ege'ye:** MSD dış doğrulama olarak kullanılamaz (yukarıdaki sızıntı), alternatif ne olsun?

---

## 9. Bu klasördeki dosyalar

| Dosya | Açıklama |
|---|---|
| `HANDOFF.md` | Bu dosya |
| `veri/karaciger_vaka_sec.py` | Metadata'dan karaciğer vakalarını seçer, `karaciger_vakalar.csv` ve `indirme_plani.csv` üretir. Kullanım: `python karaciger_vaka_sec.py --parca-sayisi 12` |
| `veri/AbdomenAtlas3.0MiniWithMeta.csv` | 9.262 vakanın metadata'sı (16 MB) |
| `veri/TrainTestIDS/` | Yazarların hazır IID ve OOD ayrım listeleri |
| `betikler/00_kurulum.sh` | GPU makinesinde ortam kurulumu (venv, nnU-Net, ortam değişkenleri) |
| `betikler/01_indir.sh` | Seçilen parçaları indirir ve açar. Disk için arşivi açtıktan sonra siler |
| `betikler/02_donustur.py` | Maskeleri `0/1/2` etiketine çevirir, ızgara farkını düzeltir, nnU-Net formatına yazar. Görüntüleri kopyalamaz, sembolik bağlantı kurar |
| `betikler/03_kalite_kontrol.py` | `envanter.csv` üretir: metadata tutarlılığı, HU kontrolleri, **kopya vaka tespiti** |
| `betikler/04_degerlendir.py` | Dice, HD95, lezyon duyarlılığı, yanlış pozitif, boyuta göre duyarlılık, hasta düzeyi AUC |
| `betikler/05_egit.sh` | nnU-Net ön işleme → eğitim → tahmin → metrikler zinciri |

**Durum:** 02, 03 ve 04 sentetik veriyle yerel olarak test edildi, çalışıyor. 01 ve 05 gerçek makinede ilk kez çalışacak.

### Çalıştırma sırası

```bash
bash betikler/00_kurulum.sh /mnt/veri
bash betikler/01_indir.sh  /mnt/veri 12
source /mnt/veri/ortam.sh
python veri/karaciger_vaka_sec.py --meta /mnt/veri/ham/AbdomenAtlas3.0MiniWithMeta.csv \
       --ids /mnt/veri/ham/TrainTestIDS --parca-sayisi 12
python betikler/02_donustur.py --ham /mnt/veri/ham --cikti /mnt/veri/nnUNet_raw \
       --vakalar karaciger_vakalar.csv
python betikler/03_kalite_kontrol.py --raw /mnt/veri/nnUNet_raw \
       --meta /mnt/veri/ham/AbdomenAtlas3.0MiniWithMeta.csv
bash betikler/05_egit.sh /mnt/veri
```

---

## 10. Kalite kontrol yaklaşımı

Binlerce vakayı elle incelemek yerine otomatik kontrollerle şüpheli vakalar işaretlenir. **Hiçbir dosya silinmez**, her vaka `uygun` / `incelenecek` / `dislandi` olarak etiketlenir ve `envanter.csv`'ye yazılır. Abstract'ta "n vaka şu nedenle dışlandı" yazmak hakem açısından olumludur.

**Otomatik kontroller:** dosya okunabilirliği · CT-etiket boyut uyumu · etiket değerlerinin 0/1/2 olması · **maskeden hesaplanan hacim ve lezyon sayısının metadata ile tutması** (sessiz dönüştürme hatalarını yakalar) · HU aralığı · karaciğer medyan HU'su · z aralığı · **kopya vaka tespiti**.

**Kopya vaka neden önemli:** AbdomenAtlas 17 açık veri setinin birleşimi. Aynı hasta iki ayrı BDMAP ID ile bulunabilir; biri eğitimde diğeri testte kalırsa model hastayı ezberler ve skorlar şişer. Betik her hacmi 16×16×16'ya indirip parmak izi çıkarıyor, çok benzer olanları aynı gruba koyuyor ve grup hem eğitimde hem testte görünüyorsa uyarı veriyor.

**Veri setleri arası hasta eşleştirme şu an gereksiz**, çünkü MSD ve LiTS'i eklemiyoruz; zaten AbdomenAtlas'ın içindeler. Bu iş ancak dış doğrulama için yeni bir veri seti eklenirse gerekir.

nnU-Net'in kendi `--verify_dataset_integrity` doğrulaması dosya bütünlüğü ve geometrik tutarlılığı zaten kontrol ediyor, `05_egit.sh` içinde açık.

---

## 11. Sıradaki somut adımlar

1. **Ario'ya mesaj:** Lambda erişimi + 8. bölümdeki 4 soru. SSH açık anahtarı ekle (`ssh-keygen -t ed25519`, sonra `cat ~/.ssh/id_ed25519.pub`; **yalnızca `.pub` dosyası paylaşılır**).
2. **Makine açılınca** yukarıdaki çalıştırma sırasını uygula.
3. **Merlin kolu:** `Merlin-nnUNet` reposu kurulup `05_egit.sh /mnt/veri nnUNetTrainerMerlin` ile ikinci eğitim başlatılır (tercihen ikinci bir makinede, paralel).
4. **GitHub:** tek repo, `main` + `liver` + `pancreas` branch'leri. `04_degerlendir.py` Oktay'ın pankreas modelinde de aynen kullanılabilir (yalnızca etiket adları değişir).
