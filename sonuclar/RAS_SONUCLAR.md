# Sonuclar

**Ic test (AbdomenAtlas)** — 317 vaka (129 tumorlu, 188 tumorsuz)

| Metrik | V-JEPA 2 (dondurulmus) | Rastgele kodlayici (ablasyon) |
|---|---|---|
| Tumor Dice | 0.443 | 0.357 |
| Karaciger Dice | 0.966 | 0.960 |
| Tumor HD95 (mm) | 42.6 | 48.5 |
| Karaciger HD95 (mm) | 4.5 | 7.6 |
| Lezyon duyarliligi | 0.536 | 0.449 |
| Hasta basina yanlis pozitif | 1.84 | 1.65 |
| Hasta duzeyi duyarlilik | 0.837 | 0.783 |
| Hasta duzeyi ozgulluk | 0.723 | 0.729 |
| Hasta duzeyi AUC | 0.825 | 0.822 |
| Tumor hacim hatasi (%) | 308.2 | 200.2 |

Boyuta gore lezyon duyarliligi:

| Boyut | V-JEPA 2 (dondurulmus) | Rastgele kodlayici (ablasyon) |
|---|---|---|
| <1cm | 0.316 (n=225) | 0.213 (n=225) |
| 1-2cm | 0.643 (n=199) | 0.548 (n=199) |
| >=2cm | 0.762 (n=126) | 0.714 (n=126) |

**Harici test (LiTS)** — 131 vaka (118 tumorlu, 13 tumorsuz)

| Metrik | V-JEPA 2 (dondurulmus) | Rastgele kodlayici (ablasyon) |
|---|---|---|
| Tumor Dice | 0.463 | 0.450 |
| Karaciger Dice | 0.959 | 0.957 |
| Tumor HD95 (mm) | 33.7 | 33.4 |
| Karaciger HD95 (mm) | 5.0 | 5.3 |
| Lezyon duyarliligi | 0.534 | 0.510 |
| Hasta basina yanlis pozitif | 2.04 | 2.16 |
| Hasta duzeyi duyarlilik | 0.839 | 0.831 |
| Hasta duzeyi ozgulluk | 0.692 | 0.769 |
| Hasta duzeyi AUC | 0.771 | 0.831 |
| Tumor hacim hatasi (%) | 53.2 | 54.7 |

Boyuta gore lezyon duyarliligi:

| Boyut | V-JEPA 2 (dondurulmus) | Rastgele kodlayici (ablasyon) |
|---|---|---|
| <1cm | 0.321 (n=246) | 0.272 (n=246) |
| 1-2cm | 0.527 (n=330) | 0.515 (n=330) |
| >=2cm | 0.726 (n=285) | 0.709 (n=285) |

## Ham degerler

```
           kol            set  vaka_sayisi  tumorlu_vaka  tumorsuz_vaka  dice_karaciger_ort  dice_tumor_ort_tumorlu_vakalarda  hd95_karaciger_ort_mm  hd95_tumor_ort_mm  tumor_hacim_hatasi_ort_yuzde  lezyon_duyarliligi  hasta_basina_yanlis_pozitif  hasta_duzeyi_duyarlilik  hasta_duzeyi_ozgulluk  hasta_duzeyi_auc
   kol_a_vjepa             ic          317           129            188              0.9662                            0.4426                   4.53              42.65                         308.2              0.5364                        1.836                   0.8372                 0.7234            0.8254
   kol_a_vjepa         ic_320          320           131            189              0.9663                            0.4417                   4.52              42.87                         304.3              0.5389                        1.825                   0.8397                 0.7249            0.8260
   kol_a_vjepa         ic_tta          317           129            188              0.9673                            0.4290                   4.11              40.95                         265.7              0.5109                        1.170                   0.7752                 0.7660            0.8380
   kol_a_vjepa           lits          131           118             13              0.9591                            0.4632                   5.00              33.69                          53.2              0.5343                        2.038                   0.8390                 0.6923            0.7715
   kol_a_vjepa       lits_tta          131           118             13              0.9596                            0.4640                   4.89              29.97                          57.7              0.5064                        1.573                   0.7881                 0.8462            0.7934
   kol_a_vjepa val_checkpoint          387           145            242              0.9633                            0.3853                   4.75              48.56                         142.1              0.5754                        1.155                   0.6966                 0.7727            0.7878
   kol_a_vjepa     val_en_iyi          387           145            242              0.9629                            0.3996                   4.89              48.09                         150.0              0.6102                        1.972                   0.7724                 0.7149            0.7845
kol_b_rastgele             ic          317           129            188              0.9604                            0.3575                   7.58              48.54                         200.2              0.4491                        1.650                   0.7829                 0.7287            0.8218
kol_b_rastgele         ic_320          320           131            189              0.9605                            0.3564                   7.60              48.96                         197.8              0.4503                        1.656                   0.7863                 0.7302            0.8239
kol_b_rastgele         ic_tta          317           129            188              0.9632                            0.3523                   5.50              44.94                         169.3              0.4127                        1.262                   0.7287                 0.8245            0.8194
kol_b_rastgele           lits          131           118             13              0.9570                            0.4502                   5.31              33.39                          54.7              0.5099                        2.160                   0.8305                 0.7692            0.8312
kol_b_rastgele       lits_tta          131           118             13              0.9583                            0.4498                   4.67              30.89                          60.6              0.5029                        1.679                   0.8136                 0.7692            0.8351
kol_b_rastgele val_checkpoint          387           145            242              0.9598                            0.3342                   5.85              51.25                         187.3              0.5128                        1.370                   0.6897                 0.7645            0.7889
kol_b_rastgele     val_en_iyi          387           145            242              0.9578                            0.3374                   6.81              51.71                         188.2              0.5406                        1.574                   0.7310                 0.7479            0.7912
```