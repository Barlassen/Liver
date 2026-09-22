#!/usr/bin/env bash
# RAS hatti son olcum: sizinti dislanmis ic test (317) + LiTS
#   1) TTA'siz: mevcut tahminlerle yalnizca metrik yeniden hesaplanir
#   2) TTA + ortusme 8: dogrulama setinde (eski hat Kol A) secilen ayar, IKI KOLA AYNEN
# Checkpoint secimi degismez (secim.json, dogrulama seti, tam hacim).
source ~/veri/ortam.sh; cd ~/kod
C=${CIKTI_KOK:-~/Liver/cikti_ras}; IC=~/veri/veri22ras/test; LITS=~/veri/harici_lits15

olc () {
  local kol=$1; shift
  local ck
  ck=$(python -c "import json;print(json.load(open('$C/$kol/secim.json'))['secilen'])")
  # 1) TTA'siz, 317 vaka: tahmin klasoru 320 vakayi icerir, 04 GT klasorunu (317) dolasir
  if [ -d "$C/$kol/metrik_ic" ] && [ ! -d "$C/$kol/metrik_ic_320" ]; then
    mv "$C/$kol/metrik_ic" "$C/$kol/metrik_ic_320"
  fi
  python betikler/04_degerlendir.py --gt "$IC" --tahmin "$C/$kol/tahmin_ic" \
    --cikti "$C/$kol/metrik_ic" --isler 6 > /dev/null 2>&1
  # 2) TTA + ortusme 8
  for s in "ic:$IC" "lits:$LITS"; do
    ad=${s%%:*}; yol=${s#*:}
    python mimari/tahmin.py --vakalar "$yol" --checkpoint "$C/$kol/$ck.pt" \
      --cikti "$C/$kol/tahmin_${ad}_tta" --tta --ortusme 8 "$@" > "$C/$kol/${ad}_tta.log" 2>&1 \
      || { echo "$kol $ad TAHMIN HATASI"; return 1; }
    python betikler/04_degerlendir.py --gt "$yol" --tahmin "$C/$kol/tahmin_${ad}_tta" \
      --cikti "$C/$kol/metrik_${ad}_tta" --isler 6 > /dev/null 2>&1
  done
  echo "[$(date +%H:%M)] $kol tamam"
}

olc kol_a_vjepa &
olc kol_b_rastgele --rastgele-kodlayici &
wait
python betikler/16_kol_karsilastir.py --a "$C/kol_a_vjepa" --b "$C/kol_b_rastgele" \
  --setler ic lits ic_tta lits_tta --hedef "$C/A_vs_B.md" > /dev/null 2>&1
python betikler/10_sonuc_tablosu.py --cikti "$C" --hedef "$C/SONUCLAR.md" > /dev/null 2>&1
echo "SON OLCUM TAMAM"
