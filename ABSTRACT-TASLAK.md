# Abstract taslağı

**Durum:** Sayılar dolduruldu (22 Eylül 2026). Kaynak dosyalar: `sonuclar/SONUCLAR.md`, `sonuclar/A_vs_B.md`, `sonuclar/k4_vs_A.md`, `sonuclar/D_vs_A.md`.
**Format:** Structured abstract (Purpose / Materials and Methods / Results / Conclusion). Kongre ve kelime sınırı henüz teyit edilmedi; aşağıdaki metin ~330 kelime (başlıklar hariç).
**Sürüm:** YEDEK — yön düzeltmesiz hat. RAS hattı (`betikler/19_ras_hatti.sh`) zamanında biterse sayılar onunla değiştirilecek (önceden sabitlenen kural: skor artsa da düşse de RAS sonuçları raporlanır).
**Açık kalanlar:** (1) nnU-Net referans cümlesi — ekipteki skorlar gelince doldurulacak ya da cümle silinecek. (2) Kongre formatı.

---

## İngilizce metin

### Purpose

To determine whether a video-pretrained joint-embedding predictive architecture (V-JEPA 2), without medical pretraining, transfers to liver tumor segmentation and detection on CT, and to isolate the contribution of its pretraining.

### Materials and Methods

Public abdominal CT examinations from AbdomenAtlas 3.0 were split at the patient level into training (n = 2,197), validation (n = 387) and internal test (n = 320; 131 with tumors) cohorts. Records originating from LiTS were identified by geometry fingerprinting and excluded (n = 236), so that LiTS (n = 131; 118 with tumors) served as an external test set; corrupted header spacing in 20 LiTS volumes was corrected from the original DICOM source.

Axial slabs were encoded by a frozen V-JEPA 2 ViT-L encoder, and a lightweight three-dimensional decoder (4.6 M trainable parameters) predicted liver and tumor. Identically trained arms were: frozen V-JEPA 2; a randomly initialized encoder (ablation); last four blocks fine-tuned; and fused intermediate blocks. Checkpoints were selected on validation data. Arms were compared with paired patient-level bootstrap 95% confidence intervals (CI) and Wilcoxon tests.

### Results

On internal testing, frozen V-JEPA 2 outperformed the random encoder in per-case tumor Dice (0.427 vs 0.337; Δ 0.090, 95% CI 0.048–0.129; P < .001; global Dice 0.578 vs 0.476), lesion sensitivity (0.530 vs 0.439; Δ 0.090, 95% CI 0.040–0.140) and false positives per examination (1.40 vs 2.38); liver Dice was 0.961 and patient-level AUC 0.829. Sensitivity was 0.80, 0.65 and 0.27 for lesions ≥ 2 cm, 1–2 cm and < 1 cm. On external testing, pretraining improved per-case tumor Dice (0.475 vs 0.416; Δ 0.060, 95% CI 0.021–0.097; global 0.661 vs 0.583) and false positives (1.70 vs 2.49). Fine-tuning did not help (internal Dice 0.406). Linear probing located tumor information in intermediate blocks (average precision 0.82 at block 12 vs 0.44 at the final layer, comparable to random initialization at 0.45); fusing intermediate blocks raised external tumor Dice to 0.506 (Δ 0.031, 95% CI 0.004–0.058) (global 0.674).

### Conclusion

Video-pretrained JEPA representations transfer to CT without medical pretraining, significantly improving tumor segmentation and reducing false positives in internal and external testing. Tumor-relevant information resides in intermediate layers; sub-centimeter lesions remain the main limitation.

---

## Sayıların kaynağı ve kontrol listesi

| Cümle | Değer | Kaynak |
|---|---|---|
| Eğitim / doğrulama / iç test | 2.197 / 387 / 320 | Dönüştürülüp QC'den geçen `.npz` sayısı (manifest 2.232 / 393 diyor; farkı dönüştürme/QC dışlaması) |
| İç test tümörlü | 131 hasta, 553 lezyon | Maskeden sayım (metadata 129 diyor) |
| LiTS tümörlü | 118 hasta, 861 lezyon | Maskeden sayım, 1,5 mm ızgarada 26-komşuluk; orijinal çözünürlükte 819 |
| Dışlanan LiTS kökenli | 236 kayıt | `veri_seti/lits_kokenli.csv` (131 LiTS hacminin tüm geometri adayları) |
| A vs B | Dice Δ 0,090 (0,048–0,129) iç; 0,060 (0,021–0,097) LiTS | `sonuclar/A_vs_B.md` |
| Lezyon duyarlılığı LiTS'te A vs B | 0,518 vs 0,487, **anlamlı değil** | Metinde bu yüzden LiTS için anılmadı |
| Hasta düzeyi AUC LiTS'te | 0,767 vs 0,762, **anlamlı değil** | LiTS'te yalnız 13 tümörsüz hasta var |
| Boyuta göre duyarlılık | 0,802 / 0,653 / 0,267 | `SONUCLAR.md`, iç test, Kol A |
| İnce ayar | 0,406 iç (A'dan farkı anlamlı değil), 0,446 LiTS (A'dan kötü) | `sonuclar/D_vs_A.md` |
| Doğrusal sonda | AP 0,816 blok 12; 0,441 son çıktı; rastgele son çıktı 0,446 | `sonuclar/dogrusal_sonda.json` (80 eğitim / 40 doğrulama hastası, token düzeyinde) |
| Global Dice (tüm vokseller) | A 0,578 / B 0,476 iç; A 0,661 / B 0,583 / k4 0,674 LiTS | vaka_bazli.csv'den: Σ kesişim / Σ hacim. Hasta başına Dice ile BİRLİKTE, etiketli raporlanır |
| k4 vs A, LiTS | Dice 0,506 vs 0,475, Δ 0,031 (0,004–0,058) | `sonuclar/k4_vs_A.md` |

## Metinde bilerek YAZILMAYANLAR

- **IRCAD:** Ayrı bir dış test değil, LiTS 28–47'nin kendisi. Bağımsız doğrulama gibi sunulamaz.
- **"Sızıntı olmadığı kanıtlandı":** Kanıt geometri düzeyinde (boyut + voksel aralığı), piksel/hash düzeyinde değil. Metin "fingerprinting ile tespit edilip dışlandı" diyor, bu kadarını söylüyor.
- **k4 ana yöntem değil:** Doğrulamada önceden belirlenen +0,02 eşiğini geçemedi (+0,012). Bu yüzden ablasyon eski reçeteyle yapıldı; k4 keşif analizi olarak raporlanıyor.
- **Tümör hacim hatası:** İç testte ortalama %471, küçük tümörlerin şişirdiği anlamsız bir ortalama.
- **Eşik ayarı:** Doğrulamada duyarlılığı ~3 puan artırdı; abstract'a girecek kadar önemli değil.

## Sınırlılıklar (tam metin / sunum için)

1. **Kol B tek rastgele tohumla eğitildi.** Rastgele başlangıç sonucu etkiliyor (geçersiz sayılan ilk B koşusunun eğitim eğrisi daha yüksekti). 2–3 tohum ideal.
2. Tümör etiketlerinin bir kısmı AbdomenAtlas'ın yapay zekâ destekli üretimi; LiTS uzman etiketli olduğu için dış test ayrıca değerli.
3. Eğitimde sol-sağ ayna artırması kullanıldı (karaciğer asimetrisi nedeniyle tartışmalı); bütün kollara eşit uygulandı, karşılaştırmayı bozmaz.
4. nnU-Net ile doğrudan karşılaştırma bu veri bölünmesinde yapılmadı.
5. Kontrast fazı vakaların çoğunda kayıtlı değil.
6. **Görüntü yönü (yedek sürüm için):** AbdomenAtlas vakaları farklı yönlerde (RAS %45, LAS %25, LPS %20, IPL %8); bu sürümde kanonik yöne çevrilmedi. Tümü kollara eşit etki eder. RAS hattı bitince bu madde kalkar.
7. AbdomenAtlas lisansı CC-BY-NC-SA: akademik kullanım serbest, ticari kullanım değil.

## İsteğe bağlı nnU-Net cümlesi (ekip skorları gelirse)

> For reference, nnU-Net trained on the same split achieved a tumor Dice of [X] on internal testing.

Bu cümle ancak nnU-Net **aynı** 2.197 / 387 / 320 bölünmesiyle eğitilip aynı test setinde ölçüldüyse eklenebilir. Farklı bölünmedeki bir skor yan yana konamaz.
