#!/usr/bin/env bash
# Duzeltilmis LiTS setinde (28-47 gercek olcekte) tum buyuk veri kollarini yeniden olcer.
# Checkpoint secimi DOGRULAMA setinde yapilmisti (secim.json) ve degismiyor.
# Eski olcumler *_sahte_baslik klasorlerine tasinir, silinmez.
source ~/veri/ortam.sh; cd ~/kod
C=${CIKTI_KOK:-~/Liver/cikti22}; L=${LITS:-~/veri/harici_lits15}

olc () {
  local kol=$1; shift
  local ck
  ck=$(python -c "import json;print(json.load(open('$C/$kol/secim.json'))['secilen'])")
  for d in tahmin_lits metrik_lits; do
    if [ -d "$C/$kol/$d" ] && [ ! -d "$C/$kol/${d}_sahte_baslik" ]; then
      mv "$C/$kol/$d" "$C/$kol/${d}_sahte_baslik"
    fi
  done
  python mimari/tahmin.py --vakalar "$L" --checkpoint "$C/$kol/$ck.pt" \
    --cikti "$C/$kol/tahmin_lits" "$@" > "$C/$kol/lits_yeniden.log" 2>&1 \
    || { echo "$kol TAHMIN HATASI"; return 1; }
  python betikler/04_degerlendir.py --gt "$L" --tahmin "$C/$kol/tahmin_lits" \
    --cikti "$C/$kol/metrik_lits" --isler 6 > /dev/null 2>&1
  python - "$C/$kol" "$kol" "$ck" <<'PY'
import json, sys
k, ad, ck = sys.argv[1:]
o = json.load(open(f"{k}/metrik_lits/ozet.json"))
e = json.load(open(f"{k}/metrik_lits_sahte_baslik/ozet.json"))
f = lambda d, a: d[a]
print(f"{ad} ({ck}): tumor Dice {o['dice_tumor_ort_tumorlu_vakalarda']:.3f} "
      f"(once {e['dice_tumor_ort_tumorlu_vakalarda']:.3f}) | lezyon duy "
      f"{o['lezyon_duyarliligi']:.3f} (once {e['lezyon_duyarliligi']:.3f}) | FP "
      f"{o['hasta_basina_yanlis_pozitif']:.2f} (once {e['hasta_basina_yanlis_pozitif']:.2f}) | "
      f"vaka {o['vaka_sayisi']}", flush=True)
PY
}

olc kol_a_vjepa &
olc kol_b_rastgele --rastgele-kodlayici &
wait
olc kol_a_k4 --katman-sayisi 4 &
olc kol_d_inceayar --coz-son-blok 4 &
wait
python betikler/16_kol_karsilastir.py --a "$C/kol_a_vjepa" --b "$C/kol_b_rastgele" --hedef "$C/A_vs_B.md" > /dev/null 2>&1
python betikler/16_kol_karsilastir.py --a "$C/kol_a_k4" --b "$C/kol_a_vjepa" --hedef "$C/k4_vs_A.md" > /dev/null 2>&1
python betikler/16_kol_karsilastir.py --a "$C/kol_d_inceayar" --b "$C/kol_a_vjepa" --hedef "$C/D_vs_A.md" > /dev/null 2>&1
python betikler/10_sonuc_tablosu.py --cikti "$C" --hedef "$C/SONUCLAR.md" > /dev/null 2>&1
echo "YENIDEN OLCUM TAMAM"
