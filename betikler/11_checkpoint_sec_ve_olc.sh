#!/usr/bin/env bash
# Her kol icin: checkpoint secimi (DOGRULAMA setinde, tam hacim) -> ic test + LiTS olcumu
#
# Neden: egitim sirasindaki dogrulama slab ornekleriyle yapiliyor ve gurultulu.
# Kol A'da "en iyi" secilen epoch 23 checkpoint'i, tam hacim olcumunde son epoch
# checkpoint'inin gerisinde kaldi (tumor Dice 0.327 vs 0.341). Bu yuzden secim
# dogrulama setinde tam hacimde yapilir. Test setine bakarak secim YAPILMAZ.
#
# Kullanim: bash 11_checkpoint_sec_ve_olc.sh <kol_adi> [modele ek bayraklar...]
#   ornek: bash 11_checkpoint_sec_ve_olc.sh kol_d_inceayar --coz-son-blok 4
set -e
source ~/veri/ortam.sh
cd ~/kod

KOL=$1; shift
EK=("$@")                      # modele ozel bayraklar (--coz-son-blok 4, --rastgele-kodlayici)
CIKTI=${CIKTI_KOK:-~/Liver/cikti}/$KOL
VERI=${VERI:-~/veri/veri15}          # buyuk veri icin: VERI=~/veri/veri22
LITS=${LITS:-~/veri/harici_lits15}

olc_bir () {                   # $1=checkpoint adi  $2=veri klasoru  $3=etiket -> tumor Dice yazar
  local ck=$1 yol=$2 etiket=$3
  python mimari/tahmin.py --vakalar "$yol" --checkpoint "$CIKTI/$ck.pt" \
    --cikti "$CIKTI/${etiket}_$ck" "${EK[@]}" > /dev/null 2>&1
  python betikler/04_degerlendir.py --gt "$yol" --tahmin "$CIKTI/${etiket}_$ck" \
    --cikti "$CIKTI/metrik_${etiket}_$ck" --isler 10 > /dev/null 2>&1
  python -c "import json;print(json.load(open('$CIKTI/metrik_${etiket}_$ck/ozet.json'))['dice_tumor_ort_tumorlu_vakalarda'])"
}

echo "[$(date +%H:%M)] $KOL: checkpoint secimi (dogrulama seti, tam hacim)"
A=$(olc_bir en_iyi "$VERI/val" val)
B=$(olc_bir checkpoint "$VERI/val" val)
SECILEN=$(python -c "print('en_iyi' if $A >= $B else 'checkpoint')")
echo "  en_iyi: $A | son: $B | secilen: $SECILEN"
python - <<PY
import json, pathlib
pathlib.Path("$CIKTI/secim.json").write_text(json.dumps(
    {"secilen": "$SECILEN", "dogrulama_tumor_dice": {"en_iyi": $A, "checkpoint": $B}}, indent=2))
PY

for s in "ic:$VERI/test" "lits:$LITS"; do
  ad=${s%%:*}; yol=${s#*:}
  [ -d "$yol" ] || { echo "  $ad seti yok, atlaniyor"; continue; }
  echo "[$(date +%H:%M)] $KOL: $ad setinde olcum"
  python mimari/tahmin.py --vakalar "$yol" --checkpoint "$CIKTI/$SECILEN.pt" \
    --cikti "$CIKTI/tahmin_$ad" "${EK[@]}" > /dev/null 2>&1
  python betikler/04_degerlendir.py --gt "$yol" --tahmin "$CIKTI/tahmin_$ad" \
    --cikti "$CIKTI/metrik_$ad" --isler 10 > /dev/null 2>&1
  python -c "
import json; o=json.load(open('$CIKTI/metrik_$ad/ozet.json'))
print('  {}: tumor Dice {:.3f} | karaciger {:.3f} | lezyon duyarlilik {:.3f} | FP/vaka {:.2f}'.format(
  '$ad', o['dice_tumor_ort_tumorlu_vakalarda'], o['dice_karaciger_ort'],
  o['lezyon_duyarliligi'], o['hasta_basina_yanlis_pozitif']))"
done
echo "[$(date +%H:%M)] $KOL OLCUM TAMAM"
