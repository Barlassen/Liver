# kol_a_k4 (A) vs kol_a_vjepa (B)

Eslestirilmis karsilastirma; %95 GA = hasta duzeyinde bootstrap (10000 tekrar); p = Wilcoxon isaretli sira testi. GA sifiri icermiyorsa fark anlamli.

## ic

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 131 | 0.456 | 0.427 | +0.030 | +0.000 … +0.061 | 0.48 | evet, A iyi |
| Tumor HD95 mm (tumorlu vakalar) | 117 | 38.890 | 42.207 | -3.318 | -9.939 … +3.219 | 0.39 | hayir |
| Karaciger Dice | 320 | 0.962 | 0.961 | +0.002 | -0.000 … +0.004 | 0.036 | hayir |
| Yanlis pozitif / hasta | 320 | 1.503 | 1.397 | +0.106 | -0.100 … +0.325 | 0.32 | hayir |
| Lezyon duyarliligi | 553 | 0.526 | 0.530 | -0.004 | -0.045 … +0.035 | — | hayir |
| Hasta duzeyi AUC | 320 | 0.844 | 0.829 | +0.014 | -0.018 … +0.048 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 39, yalniz B buldu 41

## lits

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 118 | 0.506 | 0.475 | +0.031 | +0.004 … +0.058 | 0.028 | evet, A iyi |
| Tumor HD95 mm (tumorlu vakalar) | 99 | 31.371 | 35.019 | -3.649 | -10.154 … +2.247 | 0.28 | hayir |
| Karaciger Dice | 131 | 0.959 | 0.958 | +0.001 | -0.001 … +0.002 | 0.22 | hayir |
| Yanlis pozitif / hasta | 131 | 1.137 | 1.695 | -0.557 | -0.947 … -0.214 | 0.0065 | evet, A iyi |
| Lezyon duyarliligi | 861 | 0.554 | 0.518 | +0.036 | +0.011 … +0.064 | — | evet, A iyi |
| Hasta duzeyi AUC | 131 | 0.817 | 0.767 | +0.050 | -0.013 … +0.122 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 68, yalniz B buldu 37

## ircad

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 15 | 0.332 | 0.318 | +0.014 | -0.030 … +0.066 | 0.93 | hayir |
| Tumor HD95 mm (tumorlu vakalar) | 12 | 51.847 | 42.943 | +8.904 | -0.310 … +19.797 | 0.57 | hayir |
| Karaciger Dice | 20 | 0.933 | 0.925 | +0.008 | +0.003 … +0.013 | 0.014 | evet, A iyi |
| Yanlis pozitif / hasta | 20 | 1.300 | 1.400 | -0.100 | -0.650 … +0.400 | 0.78 | hayir |
| Lezyon duyarliligi | 113 | 0.469 | 0.478 | -0.009 | -0.100 … +0.043 | — | hayir |
| Hasta duzeyi AUC | 20 | 0.573 | 0.613 | -0.040 | -0.194 … +0.060 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 7, yalniz B buldu 8
