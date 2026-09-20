# Mimari Planı — Kaggle Kısıtlarına Göre

**Tarih:** 20 Eylül 2026 · **Durum:** Taslak, Ario'nun onayı bekleniyor

---

## 1. Kaggle neyi mümkün kılıyor, neyi kılmıyor

| Kaynak | Kaggle'da | Sonucu |
|---|---|---|
| GPU | P100 16 GB **veya** 2× T4 (toplam 32 GB) | Büyük 3B modeller sığmaz. ViT için T4 tercih edilmeli (fp16 hızlı), P100'de fp16 avantajı yok |
| Haftalık kota | ~30 saat | Tek bir tam nnU-Net eğitimi (1–2 gün) **imkânsız** |
| Tek oturum | En fazla 9 saat | Eğitim bölünmeli, **checkpoint'ten devam** şart |
| Disk | Çalışma alanı ~20 GB kalıcı, geçici alan ~60 GB civarı | **167 GB'lık 12 parça imkânsız** |
| İnternet | Açılabiliyor (telefon doğrulaması sonrası) | HuggingFace'ten indirme mümkün ama disk sınırı bağlayıcı |

### Bunun zorladığı üç değişiklik

1. **Veri küçülmeli.** 12 parça yerine 2–3 parça (~500 vaka) ve önceden küçültülmüş hacimler.
   Öneri: karaciğer çevresine kırp, 2×2×3 mm'ye yeniden örnekle, int16 sakla → vaka başına ~15–25 MB, 500 vaka ≈ 10 GB. Kaggle Dataset olarak bir kez yüklenir, sonra her oturumda hazır gelir.
2. **Ön işleme ayrı yapılmalı.** Kırpma ve yeniden örnekleme GPU istemiyor; Kaggle'ın CPU oturumlarında ya da Colab'da parça parça yapılıp çıktı Kaggle Dataset'e yazılır.
3. **Eğitim 9 saatlik dilimlere bölünmeli.** Her dilimin sonunda checkpoint `/kaggle/working`'e yazılır, sonraki oturum oradan devam eder.

---

## 2. Mimari seçenekleri

Ortak hedef: girdi CT, çıktı voksel başına `0 = arka plan, 1 = karaciğer, 2 = tümör`.

### Seçenek A — nnU-Net (küçültülmüş) · *baseline*

Kıyas için gerekli, yenilik iddiası yok. Kaggle'da `3d_lowres` ya da `2d` yapılandırmasıyla, 250 epoch yerine ~100 epoch. Tek işi karşılaştırma sayısı üretmek.

### Seçenek B — Dondurulmuş V-JEPA 2 kodlayıcı + hafif 3B çözücü · *önerilen yenilik kolu*

```
CT hacmi
   │ eksenel dilimler, 16'lı gruplar (slab), 256×256
   ▼
V-JEPA 2 ViT (Meta, MIT lisans) ─ DONDURULMUŞ, gradyan yok
   │ çıktı: 8 × 16 × 16 token, 1024 boyut
   ▼
Hafif 3B çözücü (UNETR tarzı)  ◄── ham görüntüden gelen yüksek çözünürlüklü atlama bağlantıları
   │
   ▼
16 × 256 × 256 maske (0/1/2)
```

**Neden bu:**
- V-JEPA 2 ağırlıkları **açık ve MIT lisanslı**, indirilmesi serbest
- Kodlayıcı donduğu için eğitilen parametre sayısı ~5–10 M → 16 GB GPU'ya rahat sığar, 9 saatlik dilime uyar
- Kodlayıcı çıktıları bir kez hesaplanıp önbelleğe alınabilir. Token'ları 2× havuzlarsak vaka başına ~12 MB, 500 vaka ≈ 6 GB → Kaggle diskine sığar. Sonraki epoch'lar kodlayıcıyı hiç çalıştırmaz, çok hızlanır
- **Literatürde boşluk:** 3B CT'de JEPA kodlayıcısıyla segmentasyon yapıp nnU-Net'le karşılaştıran yayın bulunamadı

**Riskleri:**
- ViT 16×16 yamalarla çalışır, küçük lezyonlarda (<1 cm) çözünürlük kaybı olur. Atlama bağlantıları bunu telafi etmek için var
- V-JEPA 2 doğal videoyla eğitildi, CT'ye alan kayması var. Pencerelenmiş (windowed) HU ile 3 kanala kopyalamak standart çözüm
- Sonucun nnU-Net'in altında kalması **olası**. Abstract bunu dürüstçe raporlayabilir; asıl katkı "JEPA kodlayıcısı 3B CT'de ne yapıyor" sorusunun ilk kez yanıtlanması olur

### Seçenek C — Önceden eğitilmiş CT kodlayıcısı (Merlin / VoCo) + nnU-Net

En güvenli yol, sonuç alma olasılığı en yüksek. Ama JEPA değil, yani Ario'nun "yeni mimari" beklentisini karşılamayabilir. Merlin MIT lisanslı ve hazır nnU-Net trainer'ı var; VoCo'nun ön eğitiminde AbdomenAtlas görüntüleri olduğu için raporda belirtilmesi gerekir.

### Seçenek D — Kendi JEPA ön eğitimimiz

Etiketsiz CT slab'leri üzerinde maskeli latent tahmini. **Kaggle'ın 30 saatlik kotasıyla ciddi bir ön eğitim yapılamaz.** Ancak küçük bir ViT ile "kavram kanıtı" ölçeğinde denenebilir. Deadline için uygun değil.

---

## 3. Önerilen kurgu

| Kol | Model | Rol | Tahmini GPU süresi |
|---|---|---|---|
| 1 | nnU-Net `3d_lowres`, ~100 epoch | Baseline | ~8–10 saat |
| 2 | V-JEPA 2 (dondurulmuş) + 3B çözücü | Yenilik | Özellik çıkarma ~2 saat + çözücü eğitimi ~3–4 saat |

İkisi de aynı veriyle, aynı hasta düzeyi ayrımıyla, aynı metriklerle ölçülür (`04_degerlendir.py` hazır). Haftalık 30 saatlik kotaya sığar.

---

## 4. Kod (yazıldı, sahte veriyle test edildi)

| Dosya | İşi | Durum |
|---|---|---|
| `mimari/veri.py` | Slab örnekleyici: 16 dilimlik gruplar, HU pencereleme (karaciğer + geniş pencere), artırma, tümörlü bölgeden ağırlıklı örnekleme | ✅ |
| `mimari/kodlayici.py` | V-JEPA 2 yükleme ve dondurma, token'ların `(B, C, t, h, w)` biçimine katlanması. Ayrıca `SahteKodlayici`: ağırlık indirmeden boru hattını test etmek için | ✅ |
| `mimari/cozucu.py` | 3B çözücü + ham görüntüden atlama bağlantıları, Dice + ağırlıklı CE kaybı (tümör ağırlığı 3×) | ✅ |
| `mimari/egit.py` | Eğitim döngüsü, AMP, **süre sınırı dolunca checkpoint yazıp çıkar, tekrar çalıştırınca devam eder** | ✅ |
| `mimari/tahmin.py` | Örtüşen slab'lerle tüm hacimde çıkarım, logit ortalaması, nnU-Net adlandırmasıyla kayıt | ✅ |
| `betikler/06_kaggle_hazirla.py` | Karaciğer çevresine kırpma, 2×2×3 mm'ye örnekleme, `.npz` çıktısı, train/val/test ayrımı | ✅ |

Değerlendirme `betikler/04_degerlendir.py` ile yapılır, yeniden yazılmadı.

**Test sonucu:** Sentetik veriyle uçtan uca çalıştırıldı. Kayıp düşüyor, 2 epoch sonunda doğrulama karaciğer Dice 0,84. Çözücü ~4,6 M parametre (gerçek kodlayıcıyla ~7 M), 16 GB GPU'ya rahat sığar.

---

## 4b. Kaggle akışı

**Hazırlık (bir kez):**
1. Veri başka bir yerde (Colab ya da herhangi bir makine) `01` → `02` → `03` → `06` betikleriyle hazırlanır.
2. `kaggle/` klasörü (~10 GB) Kaggle Dataset olarak yüklenir.

**Her oturumda:**
```python
# Kaggle notebook
!pip install -q transformers
!python mimari/egit.py --egitim /kaggle/input/liver/train --dogrulama /kaggle/input/liver/val \
        --cikti /kaggle/working/vjepa --epoch 40 --sure-siniri 8.0
```
- V-JEPA 2 ağırlıkları ilk oturumda HuggingFace'ten iner (~1,2 GB). Notebook'ta internet açık olmalı.
- Oturum bitince `/kaggle/working/vjepa/checkpoint.pt` çıktı olarak kalır. Sonraki oturumda bu klasör girdi olarak bağlanır ve eğitim kaldığı yerden devam eder.
- Kotayı boşa harcamamak için ilk denemeyi `--sahte-kodlayici --epoch 1` ile yapıp boru hattını doğrula.

---

## 5. Ario'ya sorular

1. **"Yeni mimari" bu mu, yoksa elinde başka bir tasarım mı var?** Varsa kodu/ağırlıkları paylaşsın, biz Kaggle'a uyarlayalım.
2. Dondurulmuş V-JEPA 2 + çözücü kurgusu kabul mü, yoksa kodlayıcının da (LoRA ile) eğitilmesini mi istiyor?
3. Sonuç nnU-Net'in altında kalırsa abstract yine de gönderilsin mi? (Bize göre evet: "JEPA kodlayıcısı 3B CT segmentasyonunda nerede duruyor" sorusu kendi başına yeni.)
