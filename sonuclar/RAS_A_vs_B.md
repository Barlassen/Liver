# kol_a_vjepa (A) vs kol_b_rastgele (B)

Eslestirilmis karsilastirma; %95 GA = hasta duzeyinde bootstrap (10000 tekrar); p = Wilcoxon isaretli sira testi. GA sifiri icermiyorsa fark anlamli.

## ic

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 129 | 0.443 | 0.358 | +0.085 | +0.047 … +0.122 | <0.0001 | evet, A iyi |
| Tumor HD95 mm (tumorlu vakalar) | 105 | 38.566 | 46.686 | -8.120 | -15.216 … -1.029 | 0.00019 | evet, A iyi |
| Karaciger Dice | 317 | 0.966 | 0.960 | +0.006 | +0.004 … +0.007 | <0.0001 | evet, A iyi |
| Yanlis pozitif / hasta | 317 | 1.836 | 1.650 | +0.186 | -0.082 … +0.451 | 0.07 | hayir |
| Lezyon duyarliligi | 550 | 0.536 | 0.449 | +0.087 | +0.050 … +0.122 | — | evet, A iyi |
| Hasta duzeyi AUC | 317 | 0.825 | 0.822 | +0.004 | -0.038 … +0.045 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 76, yalniz B buldu 28

## lits

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 118 | 0.463 | 0.450 | +0.013 | -0.021 … +0.048 | 0.28 | hayir |
| Tumor HD95 mm (tumorlu vakalar) | 99 | 32.517 | 33.368 | -0.851 | -7.101 … +5.319 | 0.75 | hayir |
| Karaciger Dice | 131 | 0.959 | 0.957 | +0.002 | -0.000 … +0.004 | <0.0001 | hayir |
| Yanlis pozitif / hasta | 131 | 2.038 | 2.160 | -0.122 | -0.794 … +0.573 | 0.96 | hayir |
| Lezyon duyarliligi | 861 | 0.534 | 0.510 | +0.024 | -0.013 … +0.059 | — | hayir |
| Hasta duzeyi AUC | 131 | 0.772 | 0.831 | -0.060 | -0.182 … +0.048 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 96, yalniz B buldu 75

## ic_tta

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 129 | 0.429 | 0.352 | +0.077 | +0.045 … +0.110 | <0.0001 | evet, A iyi |
| Tumor HD95 mm (tumorlu vakalar) | 102 | 36.756 | 44.579 | -7.823 | -14.949 … -0.002 | 0.00095 | evet, A iyi |
| Karaciger Dice | 317 | 0.967 | 0.963 | +0.004 | +0.003 … +0.005 | <0.0001 | evet, A iyi |
| Yanlis pozitif / hasta | 317 | 1.170 | 1.262 | -0.091 | -0.322 … +0.129 | 0.34 | hayir |
| Lezyon duyarliligi | 550 | 0.511 | 0.413 | +0.098 | +0.055 … +0.139 | — | evet, A iyi |
| Hasta duzeyi AUC | 317 | 0.838 | 0.819 | +0.019 | -0.015 … +0.052 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 76, yalniz B buldu 22

## lits_tta

| Metrik | n | A | B | A − B | %95 GA | p | Anlamli? |
|---|---|---|---|---|---|---|---|
| Tumor Dice (tumorlu vakalar) | 118 | 0.464 | 0.450 | +0.014 | -0.018 … +0.047 | 0.41 | hayir |
| Tumor HD95 mm (tumorlu vakalar) | 97 | 29.735 | 30.948 | -1.214 | -6.845 … +4.571 | 0.19 | hayir |
| Karaciger Dice | 131 | 0.960 | 0.958 | +0.001 | -0.001 … +0.003 | <0.0001 | hayir |
| Yanlis pozitif / hasta | 131 | 1.573 | 1.679 | -0.107 | -0.664 … +0.573 | 0.18 | hayir |
| Lezyon duyarliligi | 861 | 0.506 | 0.503 | +0.003 | -0.027 … +0.034 | — | hayir |
| Hasta duzeyi AUC | 131 | 0.793 | 0.835 | -0.042 | -0.139 … +0.065 | — | hayir |

Lezyon duyarliligi: yalniz A buldu 73, yalniz B buldu 70
