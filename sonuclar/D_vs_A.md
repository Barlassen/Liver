# kol_d_inceayar (A) vs kol_a_vjepa (B)

Eslestirilmis karsilastirma; %95 GA = hasta duzeyinde bootstrap (10000 tekrar); p = Wilcoxon isaretli sira testi. GA sifiri icermiyorsa fark anlamli.

## ic

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 131 | 0.406 | 0.427 | -0.021 | -0.051 … +0.009 | 0.037 | hayir |
| Tumor HD95 mm (tumorlu vakalar) | 118 | 44.740 | 43.453 | +1.287 | -6.791 … +9.149 | 0.1 | hayir |
| Karaciger Dice | 320 | 0.964 | 0.961 | +0.003 | +0.001 … +0.006 | <0.0001 | evet, A iyi |
| Yanlis pozitif / hasta | 320 | 2.925 | 1.397 | +1.528 | +1.131 … +1.959 | <0.0001 | evet, B iyi |
| Lezyon duyarliligi | 553 | 0.526 | 0.530 | -0.004 | -0.044 … +0.031 | — | hayir |
| Hasta duzeyi AUC | 320 | 0.827 | 0.829 | -0.002 | -0.038 … +0.033 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 46, yalniz B buldu 48

## lits

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 118 | 0.446 | 0.475 | -0.030 | -0.056 … -0.003 | 0.0065 | evet, B iyi |
| Tumor HD95 mm (tumorlu vakalar) | 98 | 31.895 | 34.735 | -2.840 | -9.992 … +3.594 | 0.66 | hayir |
| Karaciger Dice | 131 | 0.958 | 0.958 | -0.000 | -0.002 … +0.001 | 0.62 | hayir |
| Yanlis pozitif / hasta | 131 | 2.229 | 1.695 | +0.534 | +0.092 … +1.023 | 0.022 | evet, B iyi |
| Lezyon duyarliligi | 861 | 0.489 | 0.518 | -0.029 | -0.061 … +0.009 | — | hayir |
| Hasta duzeyi AUC | 131 | 0.797 | 0.767 | +0.031 | -0.031 … +0.101 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 55, yalniz B buldu 80

## ircad

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 15 | 0.303 | 0.318 | -0.015 | -0.061 … +0.038 | 0.33 | hayir |
| Tumor HD95 mm (tumorlu vakalar) | 12 | 45.916 | 42.943 | +2.973 | -8.101 … +13.881 | 0.52 | hayir |
| Karaciger Dice | 20 | 0.934 | 0.925 | +0.009 | -0.001 … +0.020 | 0.18 | hayir |
| Yanlis pozitif / hasta | 20 | 2.950 | 1.400 | +1.550 | +0.850 … +2.350 | 0.0016 | evet, B iyi |
| Lezyon duyarliligi | 113 | 0.487 | 0.478 | +0.009 | -0.086 … +0.087 | — | hayir |
| Hasta duzeyi AUC | 20 | 0.667 | 0.613 | +0.053 | +0.000 … +0.167 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 12, yalniz B buldu 11
