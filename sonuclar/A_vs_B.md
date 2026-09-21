# kol_a_vjepa (A) vs kol_b_rastgele (B)

Eslestirilmis karsilastirma; %95 GA = hasta duzeyinde bootstrap (10000 tekrar); p = Wilcoxon isaretli sira testi. GA sifiri icermiyorsa fark anlamli.

## ic

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 131 | 0.427 | 0.337 | +0.090 | +0.048 … +0.129 | <0.0001 | evet, A iyi |
| Tumor HD95 mm (tumorlu vakalar) | 115 | 42.546 | 58.868 | -16.321 | -25.005 … -7.768 | <0.0001 | evet, A iyi |
| Karaciger Dice | 320 | 0.961 | 0.950 | +0.011 | +0.007 … +0.014 | <0.0001 | evet, A iyi |
| Yanlis pozitif / hasta | 320 | 1.397 | 2.381 | -0.984 | -1.319 … -0.666 | <0.0001 | evet, A iyi |
| Lezyon duyarliligi | 553 | 0.530 | 0.439 | +0.090 | +0.040 … +0.140 | — | evet, A iyi |
| Hasta duzeyi AUC | 320 | 0.829 | 0.763 | +0.067 | +0.023 … +0.111 | — | evet, A iyi |

Lezyon duyarliligi: yalniz A buldu 74, yalniz B buldu 24

## lits

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 118 | 0.475 | 0.416 | +0.060 | +0.021 … +0.097 | <0.0001 | evet, A iyi |
| Tumor HD95 mm (tumorlu vakalar) | 97 | 35.134 | 41.184 | -6.050 | -14.520 … +2.588 | 0.00019 | hayir |
| Karaciger Dice | 131 | 0.958 | 0.949 | +0.009 | +0.006 … +0.012 | <0.0001 | evet, A iyi |
| Yanlis pozitif / hasta | 131 | 1.695 | 2.489 | -0.794 | -1.435 … -0.137 | 0.0023 | evet, A iyi |
| Lezyon duyarliligi | 861 | 0.518 | 0.487 | +0.031 | -0.007 … +0.068 | — | hayir |
| Hasta duzeyi AUC | 131 | 0.767 | 0.762 | +0.005 | -0.096 … +0.107 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 92, yalniz B buldu 65

## ircad

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 15 | 0.318 | 0.330 | -0.012 | -0.074 … +0.040 | 0.59 | hayir |
| Tumor HD95 mm (tumorlu vakalar) | 12 | 42.943 | 56.352 | -13.409 | -41.253 … +10.713 | 0.27 | hayir |
| Karaciger Dice | 20 | 0.925 | 0.924 | +0.001 | -0.009 … +0.011 | 1 | hayir |
| Yanlis pozitif / hasta | 20 | 1.400 | 3.950 | -2.550 | -4.050 … -1.250 | 0.00083 | evet, A iyi |
| Lezyon duyarliligi | 113 | 0.478 | 0.425 | +0.053 | -0.025 … +0.135 | — | hayir |
| Hasta duzeyi AUC | 20 | 0.613 | 0.707 | -0.093 | -0.233 … +0.008 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 15, yalniz B buldu 9
