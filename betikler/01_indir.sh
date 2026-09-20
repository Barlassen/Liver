#!/usr/bin/env bash
# AbdomenAtlas 3.0 Mini'den secilen parcalari indirir ve acar.
# Kullanim: bash 01_indir.sh /mnt/veri 12      (ilk 12 parca ~167 GB goruntu + ~4 GB maske)
#
# Her parcada 232 vaka var. Karaciger tumorlu vakalar ilk 22 parcaya (ID 1-5104)
# esit dagilmis; ID 5196 ve sonrasi RSNA Trauma verisi, tumor neredeyse yok.
set -euo pipefail

#   bash 01_indir.sh /mnt/veri "5 6 7 8 18 20"   -> yalnizca bu parcalar
#   (parca numaralari veri_seti/indirme_plani.csv dosyasinda)
KOK="${1:-/mnt/veri}"
IKINCI="${2:-12}"
if [[ "$IKINCI" =~ ^[0-9]+$ ]]; then
  PARCALAR=$(seq 0 $((IKINCI - 1)))
else
  PARCALAR="$IKINCI"
fi
REPO="AbdomenAtlas/AbdomenAtlas3.0Mini"
HAM="$KOK/ham"
mkdir -p "$HAM"
cd "$HAM"

# shellcheck disable=SC1091
[ -f "$KOK/ortam.sh" ] && source "$KOK/ortam.sh"

dosya_adi() {  # $1 = parca indeksi (0 tabanli), $2 = images|masks
  local bas=$(( $1 * 232 + 1 ))
  local son=$(( ($1 + 1) * 232 )); [ "$son" -gt 9262 ] && son=9262
  printf "AbdomenAtlas3_%s_BDMAP_BDMAP_%08d_BDMAP_%08d.tar.gz" "$2" "$bas" "$son"
}

echo "== Metadata ve ayrim listeleri"
huggingface-cli download "$REPO" --repo-type dataset --local-dir "$HAM" \
  --include "AbdomenAtlas3.0MiniWithMeta.csv" "TrainTestIDS/*"

for k in $PARCALAR; do
  for tur in masks images; do
    ad=$(dosya_adi "$k" "$tur")
    klasor="$HAM/$tur"
    mkdir -p "$klasor"
    if [ -f "$klasor/.acildi_$ad" ]; then
      echo "== $ad zaten acilmis, atlaniyor"
      continue
    fi
    if [ "$tur" = masks ]; then dizin=mask_only; else dizin=image_only; fi
    echo "== Indiriliyor: $dizin/$ad"
    huggingface-cli download "$REPO" --repo-type dataset --local-dir "$HAM" \
      --include "$dizin/$ad"

    kaynak="$HAM/$dizin/$ad"
    echo "== Aciliyor: $ad"
    tar xzf "$kaynak" -C "$klasor"
    touch "$klasor/.acildi_$ad"
    # Disk yerini korumak icin arsivi sil (tekrar gerekirse yeniden indirilir).
    rm -f "$kaynak"
  done
done

echo
echo "Bitti. Vaka klasorleri:"
echo "  goruntuler: $HAM/images/BDMAP_XXXXXXXX/ct.nii.gz"
echo "  maskeler  : $HAM/masks/BDMAP_XXXXXXXX/segmentations/liver.nii.gz, liver_lesion.nii.gz"
du -sh "$HAM"/images "$HAM"/masks 2>/dev/null || true
