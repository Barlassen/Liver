# Abstract taslağı

**Durum:** Sayılar eğitim bitince doldurulacak. `[X]` yerleri sonuçlardan gelecek.
**Format:** Structured abstract (Purpose / Materials and Methods / Results / Conclusion), 250–350 kelime.

---

## İngilizce taslak

### Purpose

To evaluate whether a **video-pretrained joint-embedding predictive architecture (V-JEPA 2)**,
used as a frozen encoder, can support **liver tumor detection and segmentation on abdominal CT**,
and to quantify how much of its performance derives from large-scale self-supervised pretraining.

### Materials and Methods

Retrospective analysis of **[918]** publicly available contrast-varied abdominal CT examinations
from AbdomenAtlas 3.0. Cases originating from LiTS/MSD Task03 were identified by volume-geometry
fingerprinting and **excluded from all training and internal testing**; LiTS was reserved as an
independent external test set with expert annotations (**131** examinations, **118** with tumors,
**819** lesions). Data were split **at the patient level** into training (**651**), validation
(**114**) and internal test (**153**, **61** with tumors) cohorts, and included tumor-free
examinations to permit specificity estimation.

Axial slabs of 16 slices (1.5 × 1.5 × 2.0 mm) were encoded by a frozen V-JEPA 2 ViT-L encoder;
a lightweight three-dimensional decoder with high-resolution skip connections predicted
voxel-wise labels (background / liver / tumor). Three arms were trained identically:
(a) **frozen V-JEPA 2**, (b) the **same architecture with a randomly initialized encoder**
(ablation isolating the contribution of pretraining), and (c) **V-JEPA 2 with the last four
transformer blocks fine-tuned**. **nnU-Net** served as the reference baseline.

Segmentation was assessed with Dice and 95th-percentile Hausdorff distance; detection with
lesion-level sensitivity, false positives per examination, size-stratified sensitivity
(<1 cm, 1–2 cm, ≥2 cm) and patient-level sensitivity, specificity and AUC.

### Results

*(Doldurulacak)*

- Internal test, tumor Dice: frozen **[X]**, fine-tuned **[X]**, random-init **[X]**, nnU-Net **[X]**
- Internal test, liver Dice: **[X]** / **[X]** / **[X]** / **[X]**
- Lesion sensitivity **[X]** at **[X]** false positives per examination
- Size-stratified sensitivity: <1 cm **[X]**, 1–2 cm **[X]**, ≥2 cm **[X]**
- Patient-level AUC **[X]** (sensitivity **[X]**, specificity **[X]**)
- External LiTS test: tumor Dice **[X]**, lesion sensitivity **[X]**

### Conclusion

*(Sonuca göre yazılacak — üç olası yön aşağıda)*

---

## Sonuca göre üç olası çerçeve

| Durum | Ana mesaj |
|---|---|
| **V-JEPA > rastgele** ve nnU-Net'e yakın | "Doğal videoyla yapılan ön eğitim, hiç tıbbi görüntü görmeden 3B BT'ye anlamlı şekilde aktarılıyor." En güçlü sonuç |
| **V-JEPA ≈ rastgele** | "Video ön eğitimi bu alana aktarılmıyor; kazanç mimariden geliyor." Negatif ama yayınlanabilir; literatürde bu karşılaştırma yok |
| **İkisi de nnU-Net'in belirgin altında** | Tespit tarafı öne çıkarılır: "segmentasyon geride kalsa da lezyon tespiti ve hasta düzeyi ayrım klinik olarak anlamlı seviyede" |

Hangi durum çıkarsa çıksın **ablasyon kolu sonucu taşır**: ölçtüğümüz şey "JEPA ön eğitimi 3B BT'de ne kazandırıyor" sorusunun ilk doğrudan cevabı.

---

## Yöntem bölümünde mutlaka geçmesi gerekenler

1. **Hasta düzeyinde bölünme** — sızıntı önlemi
2. **LiTS/MSD dışlaması** — AbdomenAtlas bu veri setlerini içeriyor; parmak iziyle tespit edilip çıkarıldı
3. **Veri seti içi kopyalar** — LiTS taramalarının çoğu AbdomenAtlas'ta iki ayrı BDMAP ID ile bulunuyor (97 çiftin 92'sinde karaciğer hacmi farkı %2'nin altında); her iki kopya da dışlandı
4. **Tümörsüz vakaların dahil edilmesi** — özgüllük ölçümü için
5. **Kalite kontrol** — maskeden hesaplanan hacimler metadata ile karşılaştırıldı (ortanca fark %0,4); uyumsuz vakalar işaretlendi
6. **Oblik affine düzeltmesi** — voksel aralığı affine köşegeninden okunduğunda bazı vakalarda sıfır çıkıyor ve hacimler bozuluyor; sütun normu kullanıldı

Bu maddeler hem yöntemin sağlamlığını gösterir hem de hakemin "veri sızıntısını nasıl ele aldınız" sorusunu baştan cevaplar.

---

## Sınırlılıklar (Conclusion'da bir cümle)

- Tümör etiketlerinin bir kısmı AbdomenAtlas'ın kendi üretimi; LiTS harici testi bu nedenle ayrıca değerli
- Tek merkez değil ama tek veri seti ailesi; ileri çalışmada bağımsız hastane verisi gerekir
- Kontrast fazı vakaların %87'sinde kayıtlı değil, faza göre alt analiz yapılamadı
- AbdomenAtlas lisansı CC-BY-NC-SA: akademik kullanım serbest, ticari kullanım değil
