#!/usr/bin/env bash
# nnU-Net baseline: on isleme -> egitim -> tahmin -> metrikler
# Kullanim: bash 05_egit.sh /mnt/veri [trainer]
#   trainer varsayilan: nnUNetTrainer_250epochs  (deadline icin kisa egitim)
#   tam egitim icin: nnUNetTrainer  (1000 epoch, 1-2 gun)
#   Merlin icin:     nnUNetTrainerMerlin  (once Merlin-nnUNet reposu kurulmali)
set -euo pipefail

KOK="${1:-/mnt/veri}"
TRAINER="${2:-nnUNetTrainer_250epochs}"
# shellcheck disable=SC1091
source "$KOK/ortam.sh"

VS=1                     # Dataset001_LiverTumor
YAPI=3d_fullres
FOLD=0                   # tek fold. Varsayilan 5 fold sureyi 5'e katlar.
CIKTI="$KOK/cikti/${TRAINER}"

echo "== 1/4 On isleme (dogrulama dahil)"
nnUNetv2_plan_and_preprocess -d $VS -c $YAPI --verify_dataset_integrity

echo "== 2/4 Egitim ($TRAINER, fold $FOLD)"
nnUNetv2_train $VS $YAPI $FOLD -tr "$TRAINER" --npz

echo "== 3/4 Test setinde tahmin"
mkdir -p "$CIKTI/tahmin"
nnUNetv2_predict \
  -i "$nnUNet_raw/Dataset001_LiverTumor/imagesTs" \
  -o "$CIKTI/tahmin" \
  -d $VS -c $YAPI -f $FOLD -tr "$TRAINER" \
  --disable_tta            # TTA kapali: ~4 kat hizli, sonuc cok az duser

echo "== 4/4 Metrikler"
python "$(dirname "$0")/04_degerlendir.py" \
  --gt "$nnUNet_raw/Dataset001_LiverTumor/labelsTs" \
  --tahmin "$CIKTI/tahmin" \
  --cikti "$CIKTI/metrik"

echo
echo "Sonuclar: $CIKTI/metrik/ozet.json"
