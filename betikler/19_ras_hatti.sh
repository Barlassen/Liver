#!/usr/bin/env bash
# RAS hatti: veri RAS'a cevrilir, Kol A ve Kol B ayni recete ile yeniden egitilir ve olculur.
# Onceden sabitlenen kural: bu hat metodolojik olarak dogru olandir; zamaninda biterse
# skorlar artsa da dusse de bu sonuclar raporlanir.
set -e
source ~/veri/ortam.sh; cd ~/kod
export VERI=$HOME/veri/veri22ras
export LITS=$HOME/veri/harici_lits15          # LiTS hacimlerinin hepsi zaten RAS
export IRCAD=$HOME/veri/YOK_ircad_atlaniyor   # IRCAD bagimsiz dis test degil, olculmez
export CIKTI_KOK=$HOME/Liver/cikti_ras
C=$CIKTI_KOK; mkdir -p "$C"
EPOCH=60; ADIM=400; BATCH=8

if [ ! -f "$VERI/ras_rapor.csv" ]; then
  echo "[$(date +%H:%M)] === veri RAS'a cevriliyor ==="
  python betikler/18_ras_yeniden_hazirla.py --eski ~/veri/veri22 --raw ~/veri/nnUNet_raw22 \
    --cikti "$VERI" --aralik 1.5 1.5 2.0 --isler 24
fi
for b in train val test; do
  n_eski=$(ls ~/veri/veri22/$b/*.npz | wc -l); n_yeni=$(ls "$VERI"/$b/*.npz | wc -l)
  echo "  $b: eski $n_eski, yeni $n_yeni"
  [ "$n_eski" -eq "$n_yeni" ] || { echo "HATA: $b vaka sayisi tutmuyor"; exit 1; }
done

egit () {
  local kol=$1; shift
  echo "[$(date +%H:%M)] === $kol EGITIM (RAS) ==="
  python mimari/egit.py --egitim "$VERI/train" --dogrulama "$VERI/val" --cikti "$C/$kol" \
    --epoch $EPOCH --adim $ADIM --batch $BATCH --sure-siniri 10 "$@" > "$C/${kol}_egitim.log" 2>&1
  echo "[$(date +%H:%M)] $kol egitim bitti"
}
egit kol_a_vjepa &
egit kol_b_rastgele --rastgele-kodlayici --kodlayici-tohumu 0 &
wait

bash betikler/11_checkpoint_sec_ve_olc.sh kol_a_vjepa
bash betikler/11_checkpoint_sec_ve_olc.sh kol_b_rastgele --rastgele-kodlayici
python betikler/16_kol_karsilastir.py --a "$C/kol_a_vjepa" --b "$C/kol_b_rastgele" --setler ic lits \
  --hedef "$C/A_vs_B.md" > /dev/null 2>&1
python betikler/10_sonuc_tablosu.py --cikti "$C" --hedef "$C/SONUCLAR.md" > /dev/null 2>&1
echo "[$(date +%H:%M)] === RAS HATTI TAMAM ==="
