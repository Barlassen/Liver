# Sonuclar

**Ic test (AbdomenAtlas)** — 320 vaka (131 tumorlu, 189 tumorsuz)

| Metrik | V-JEPA 2 (dondurulmus) | V-JEPA 2 (son 4 blok ince ayar) | Rastgele kodlayici (ablasyon) | kol_a_k4 |
|---|---|---|---|---|
| Tumor Dice | 0.427 | 0.406 | 0.337 | 0.456 |
| Karaciger Dice | 0.961 | 0.964 | 0.950 | 0.962 |
| Tumor HD95 (mm) | 44.2 | 45.7 | 60.6 | 40.5 |
| Karaciger HD95 (mm) | 6.0 | 4.9 | 10.7 | 6.0 |
| Lezyon duyarliligi | 0.530 | 0.526 | 0.439 | 0.526 |
| Hasta basina yanlis pozitif | 1.40 | 2.92 | 2.38 | 1.50 |
| Hasta duzeyi duyarlilik | 0.824 | 0.885 | 0.863 | 0.847 |
| Hasta duzeyi ozgulluk | 0.698 | 0.609 | 0.481 | 0.688 |
| Hasta duzeyi AUC | 0.829 | 0.827 | 0.763 | 0.844 |
| Tumor hacim hatasi (%) | 471.4 | 240.8 | 525.4 | 371.5 |

Boyuta gore lezyon duyarliligi:

| Boyut | V-JEPA 2 (dondurulmus) | V-JEPA 2 (son 4 blok ince ayar) | Rastgele kodlayici (ablasyon) | kol_a_k4 |
|---|---|---|---|---|
| <1cm | 0.267 (n=225) | 0.351 (n=225) | 0.164 (n=225) | 0.293 (n=225) |
| 1-2cm | 0.653 (n=202) | 0.584 (n=202) | 0.584 (n=202) | 0.614 (n=202) |
| >=2cm | 0.802 (n=126) | 0.746 (n=126) | 0.698 (n=126) | 0.802 (n=126) |

**Harici test (LiTS)** — 131 vaka (118 tumorlu, 13 tumorsuz)

| Metrik | V-JEPA 2 (dondurulmus) | V-JEPA 2 (son 4 blok ince ayar) | Rastgele kodlayici (ablasyon) | kol_a_k4 |
|---|---|---|---|---|
| Tumor Dice | 0.475 | 0.446 | 0.416 | 0.506 |
| Karaciger Dice | 0.958 | 0.958 | 0.949 | 0.959 |
| Tumor HD95 (mm) | 34.7 | 37.2 | 47.1 | 33.0 |
| Karaciger HD95 (mm) | 5.7 | 4.4 | 8.4 | 5.4 |
| Lezyon duyarliligi | 0.518 | 0.489 | 0.487 | 0.554 |
| Hasta basina yanlis pozitif | 1.70 | 2.23 | 2.49 | 1.14 |
| Hasta duzeyi duyarlilik | 0.831 | 0.814 | 0.864 | 0.848 |
| Hasta duzeyi ozgulluk | 0.692 | 0.769 | 0.615 | 0.692 |
| Hasta duzeyi AUC | 0.767 | 0.797 | 0.762 | 0.817 |
| Tumor hacim hatasi (%) | 50.4 | 56.1 | 85.2 | 55.9 |

Boyuta gore lezyon duyarliligi:

| Boyut | V-JEPA 2 (dondurulmus) | V-JEPA 2 (son 4 blok ince ayar) | Rastgele kodlayici (ablasyon) | kol_a_k4 |
|---|---|---|---|---|
| <1cm | 0.256 (n=246) | 0.285 (n=246) | 0.240 (n=246) | 0.305 (n=246) |
| 1-2cm | 0.521 (n=330) | 0.458 (n=330) | 0.458 (n=330) | 0.554 (n=330) |
| >=2cm | 0.740 (n=285) | 0.702 (n=285) | 0.733 (n=285) | 0.768 (n=285) |

## Ham degerler

```
           kol               set  vaka_sayisi  tumorlu_vaka  tumorsuz_vaka  dice_karaciger_ort  dice_tumor_ort_tumorlu_vakalarda  hd95_karaciger_ort_mm  hd95_tumor_ort_mm  tumor_hacim_hatasi_ort_yuzde  lezyon_duyarliligi  hasta_basina_yanlis_pozitif  hasta_duzeyi_duyarlilik  hasta_duzeyi_ozgulluk  hasta_duzeyi_auc
      kol_a_k4                ic          320           131            189              0.9622                            0.4562                   5.98              40.51                         371.5              0.5262                        1.503                   0.8473                 0.6878            0.8436
      kol_a_k4             ircad           20            15              5              0.9329                            0.3322                   9.87              53.33                          66.3              0.4690                        1.300                   0.8000                 0.4000            0.5733
      kol_a_k4              lits          131           118             13              0.9588                            0.5064                   5.39              32.95                          55.9              0.5540                        1.137                   0.8475                 0.6923            0.8168
      kol_a_k4 lits_sahte_baslik          131           118             13              0.9568                            0.4999                   6.76              34.40                          56.0              0.5401                        1.397                   0.8475                 0.7692            0.8377
      kol_a_k4    val_checkpoint          387           145            242              0.9584                            0.3958                   6.06              47.36                         153.7              0.5870                        1.176                   0.7655                 0.7727            0.8217
      kol_a_k4        val_en_iyi          387           145            242              0.9572                            0.4153                   7.13              46.82                         307.9              0.6311                        1.525                   0.7862                 0.7190            0.8098
   kol_a_vjepa                ic          320           131            189              0.9607                            0.4266                   5.97              44.20                         471.4              0.5298                        1.397                   0.8244                 0.6984            0.8293
   kol_a_vjepa             ircad           20            15              5              0.9250                            0.3183                  18.72              42.94                          73.9              0.4779                        1.400                   0.8000                 0.6000            0.6133
   kol_a_vjepa              lits          131           118             13              0.9581                            0.4755                   5.73              34.70                          50.4              0.5180                        1.695                   0.8305                 0.6923            0.7666
   kol_a_vjepa lits_sahte_baslik          131           118             13              0.9560                            0.4741                   6.64              37.28                          51.1              0.5110                        1.947                   0.8475                 0.6923            0.7927
   kol_a_vjepa    val_checkpoint          387           145            242              0.9568                            0.3781                   7.15              47.90                          85.0              0.5684                        1.214                   0.7517                 0.7934            0.8166
   kol_a_vjepa        val_en_iyi          387           145            242              0.9570                            0.4034                   7.23              50.18                         134.1              0.5963                        1.540                   0.8000                 0.6777            0.8023
kol_b_rastgele                ic          320           131            189              0.9497                            0.3370                  10.68              60.59                         525.4              0.4394                        2.381                   0.8626                 0.4815            0.7627
kol_b_rastgele             ircad           20            15              5              0.9242                            0.3305                  18.14              62.82                          67.2              0.4248                        3.950                   1.0000                 0.2000            0.7067
kol_b_rastgele              lits          131           118             13              0.9493                            0.4157                   8.40              47.08                          85.2              0.4866                        2.489                   0.8644                 0.6154            0.7617
kol_b_rastgele lits_sahte_baslik          131           118             13              0.9468                            0.4083                   9.65              47.25                          86.2              0.4692                        2.603                   0.8475                 0.6923            0.8012
kol_b_rastgele    val_checkpoint          387           145            242              0.9508                            0.2774                   8.58              58.21                         196.6              0.4292                        1.527                   0.7172                 0.6446            0.7382
kol_b_rastgele        val_en_iyi          387           145            242              0.9456                            0.3216                  10.84              62.53                         655.9              0.5081                        2.568                   0.8345                 0.4793            0.7273
kol_d_inceayar                ic          320           131            189              0.9637                            0.4059                   4.87              45.66                         240.8              0.5262                        2.925                   0.8855                 0.6085            0.8271
kol_d_inceayar             ircad           20            15              5              0.9340                            0.3029                  14.54              54.81                          75.3              0.4867                        2.950                   0.8667                 0.6000            0.6667
kol_d_inceayar              lits          131           118             13              0.9580                            0.4458                   4.40              37.17                          56.1              0.4890                        2.229                   0.8136                 0.7692            0.7973
kol_d_inceayar lits_sahte_baslik          131           118             13              0.9562                            0.4383                   5.09              37.79                          55.9              0.4855                        2.786                   0.8136                 0.7692            0.8396
kol_d_inceayar    val_checkpoint          387           145            242              0.9586                            0.3784                   6.29              47.15                         178.5              0.5476                        1.173                   0.7103                 0.7479            0.7808
kol_d_inceayar        val_en_iyi          387           145            242              0.9587                            0.4029                   6.39              47.01                         191.1              0.6357                        2.920                   0.7931                 0.5661            0.7821
```