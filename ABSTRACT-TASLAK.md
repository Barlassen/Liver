# Abstract taslağı

**Sürüm:** SON — RAS hattı (yön düzeltmeli), sızıntısız iç test (317), önceden sabitlenmiş TTA ayarı. 22 Eylül 2026.
**Kaynak dosyalar:** `sonuclar/RAS_A_vs_B.md`, `sonuclar/RAS_SONUCLAR.md`, `sonuclar/dogrusal_sonda_ras.json`.
**Önceki sürüm (yön düzeltmesiz hat):** `sonuclar/ABSTRACT-eski-hat-yon-duzeltmesiz.md` — kayıt için saklanıyor, KULLANILMAYACAK.
**Açık kalanlar:** (1) Kongre formatı ve kelime sınırı. (2) nnU-Net cümlesi yalnızca aynı bölünmeyle eğitildiyse.

---

## İngilizce metin

### Purpose

To determine whether a video-pretrained joint-embedding predictive architecture (V-JEPA 2), without medical pretraining, transfers to liver tumor segmentation and detection on CT, and to isolate the contribution of its pretraining.

### Materials and Methods

Public abdominal CT examinations from AbdomenAtlas 3.0 were reoriented to a canonical orientation and split at the patient level into training (n = 2,197), validation (n = 387) and internal test (n = 317; 129 with tumors) cohorts. LiTS-derived records (n = 236) and cross-split duplicates (n = 3) were identified by fingerprinting and excluded, so that LiTS (n = 131; 118 with tumors) served as an external test set; corrupted header spacing in 20 LiTS volumes was corrected from the original DICOM source.

Axial slabs were encoded by a frozen V-JEPA 2 ViT-L encoder, and a lightweight three-dimensional decoder (4.6 M trainable parameters) predicted liver and tumor. The pretrained encoder was compared with an identically trained, randomly initialized encoder (ablation). Checkpoints and inference settings were fixed on validation data before testing. Arms were compared with paired patient-level bootstrap 95% confidence intervals (CI) and Wilcoxon tests; linear probes quantified tumor information in each encoder block.

### Results

On internal testing, the pretrained encoder outperformed the random encoder in per-case tumor Dice (0.429 vs 0.352; Δ 0.077, 95% CI 0.045–0.110; P < .001; global Dice 0.560 vs 0.419) and lesion sensitivity (0.511 vs 0.413; Δ 0.098, 95% CI 0.055–0.139) at similar false positives per examination (1.17 vs 1.26); liver Dice was 0.967. Sensitivity was 0.75, 0.61 and 0.29 for lesions ≥ 2 cm, 1–2 cm and < 1 cm. On external testing, differences were not significant (tumor Dice 0.464 vs 0.450; Δ 0.014, 95% CI −0.018 to 0.047; global Dice 0.619 vs 0.596). Linear probing located tumor information in intermediate blocks (average precision 0.81 at block 12 vs 0.52 at the final layer and 0.42 with random initialization).

### Conclusion

Frozen video-pretrained JEPA representations significantly improved liver tumor segmentation and detection over random initialization on internal testing, but the benefit did not reach significance on external testing. Tumor-relevant information resides in intermediate rather than final layers, motivating multi-layer decoding, fine-tuning and CT-domain pretraining.

---

## Sayıların kaynağı ve kontrol listesi

| Cümle | Değer | Kaynak / not |
|---|---|---|
| Eğitim / doğrulama / iç test | 2.197 / 387 / 317 | `veri22ras/*`; iç testten 3 sızıntı vakası çıkarıldı (`veri_seti/sizinti_dislanan_test.csv`) |
| İç test tümörlü | 129 hasta, 550 lezyon | Maskeden sayım (sızıntılı 3 vakanın 2'si tümörlüydü) |
| LiTS | 131 hasta, 118 tümörlü, 861 lezyon | 1,5 mm ızgarada 26-komşuluk; orijinal çözünürlükte 819 |
| Dışlanan | 236 LiTS kökenli + 3 kopya | Geometri parmak izi (LiTS); içerik parmak izi, 16³ kosinüs benzerliği (kopyalar) |
| İç test A vs B (TTA'lı, birincil) | Dice 0,429 vs 0,352; Δ 0,077 (0,045–0,110), p<0,0001 | `RAS_A_vs_B.md` → `ic_tta` |
| Global Dice iç test | 0,560 vs 0,419 | vaka_bazli.csv: Σ kesişim / Σ hacim |
| Lezyon duyarlılığı iç test | 0,511 vs 0,413; Δ 0,098 (0,055–0,139) | `ic_tta` |
| Yanlış pozitif / hasta iç test | 1,17 vs 1,26; **anlamlı değil** | "similar" diye yazıldı |
| Hasta düzeyi AUC iç test | 0,838 vs 0,819; **anlamlı değil** | Metne alınmadı |
| Boyuta göre duyarlılık (A) | 0,754 / 0,608 / 0,289 | `ic_tta` |
| LiTS A vs B | 0,464 vs 0,450; Δ 0,014 (−0,018…0,047), p=0,41 | `lits_tta` |
| Global Dice LiTS | 0,619 vs 0,596 | — |
| Sonda (RAS verisi) | AP 0,809 blok 12; 0,521 son çıktı; rastgele 0,416 | `dogrusal_sonda_ras.json`; 80 eğitim / 40 doğrulama hastası, token düzeyi |

### Duyarlılık analizi: TTA'sız (aynı modeller)

| | A | B | Fark |
|---|---|---|---|
| İç test tümör Dice | 0,443 | 0,358 | +0,085 (0,047–0,122) ✅ |
| İç test lezyon duyarlılığı | 0,536 | 0,449 | +0,087 ✅ |
| LiTS tümör Dice | 0,463 | 0,450 | +0,013 ❌ |

Sonuç yönü TTA'dan bağımsız. TTA (sol-sağ ayna ortalaması + slab örtüşmesi 8) eski hattın doğrulama setinde seçilmişti; RAS modellerinde iç test Dice'ını biraz düşürdü, yanlış pozitifi azalttı. Önceden sabitlendiği için birincil sonuç TTA'lı.

## Metinde bilerek YAZILMAYANLAR

- **k4 ve Kol D:** Yalnızca yön düzeltmesiz hatta eğitildiler; RAS sonuçlarıyla yan yana konamaz.
- **Yön düzeltmesinin etkisi:** Düzeltmeden önce LiTS farkı anlamlı görünüyordu (Δ 0,060). Düzeltmeden sonra kayboldu: rastgele kodlayıcı LiTS'te 0,416 → 0,450'ye çıktı, V-JEPA değişmedi. Yorum: eski dış test avantajının bir kısmı ön eğitimli özelliklerin karışık yönlü veriye dayanıklılığından geliyordu. Tam metin / sunum için önemli; abstract'ta yer yok.
- **IRCAD:** LiTS 28–47'nin kendisi, bağımsız test değil.
- **"Sızıntı olmadığı kanıtlandı":** Kanıt parmak izi düzeyinde, hash düzeyinde değil.

## Sınırlılıklar (tam metin / sunum için)

1. **Kol B tek rastgele tohumla eğitildi.** 2–3 tohum ideal.
2. Tümör etiketlerinin bir kısmı AbdomenAtlas'ın yapay zekâ destekli üretimi; kopya çiftlerinde aynı taramaya farklı tümör etiketi verildiği görüldü (ör. 19 cm³ vs 1 cm³).
3. Eğitimde sol-sağ ayna artırması kullanıldı; yön düzeltilmiş veride anatomik olarak gerçekçi değil. İki kola eşit uygulandı.
4. Kaydedilen voksel aralığı hedef değer; yeniden örneklemedeki yuvarlama nedeniyle ulaşılan değer en fazla yarım voksel farklı.
5. nnU-Net ile doğrudan karşılaştırma bu bölünmede yapılmadı.
6. Kaynak veri seti, tarayıcı (%90) ve kontrast fazı (%70) çoğu vakada kayıtsız.
7. AbdomenAtlas lisansı CC-BY-NC-SA: akademik kullanım serbest, ticari kullanım değil.

## İsteğe bağlı nnU-Net cümlesi

> For reference, nnU-Net trained on the same split achieved a tumor Dice of [X] on internal testing.

Yalnızca nnU-Net **aynı** 2.197 / 387 / 317 bölünmesiyle eğitilip aynı test setinde ölçüldüyse.
