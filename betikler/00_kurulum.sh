#!/usr/bin/env bash
# Lambda / Azure GPU makinesinde ortam kurulumu.
# Kullanim: bash 00_kurulum.sh /mnt/veri
# /mnt/veri -> kalici depolama (persistent filesystem). Makine silinince yerel disk gider!
set -euo pipefail

KOK="${1:-/mnt/veri}"
mkdir -p "$KOK"/{ham,nnUNet_raw,nnUNet_preprocessed,nnUNet_results,cikti}

# --- Python ortami -----------------------------------------------------------
# Lambda Stack'te PyTorch + CUDA zaten kurulu. Sanal ortami --system-site-packages
# ile acip mevcut torch'u yeniden indirmekten kaciniyoruz.
if [ ! -d "$KOK/venv" ]; then
  python3 -m venv --system-site-packages "$KOK/venv"
fi
# shellcheck disable=SC1091
source "$KOK/venv/bin/activate"

pip install -q --upgrade pip
pip install -q nnunetv2 nibabel scipy pandas scikit-image "huggingface_hub[cli]" tqdm

# --- nnU-Net ortam degiskenleri ---------------------------------------------
cat > "$KOK/ortam.sh" <<EOF
source "$KOK/venv/bin/activate"
export nnUNet_raw="$KOK/nnUNet_raw"
export nnUNet_preprocessed="$KOK/nnUNet_preprocessed"
export nnUNet_results="$KOK/nnUNet_results"
export VERI_KOK="$KOK"
EOF

echo
echo "Kurulum bitti. Her yeni oturumda su satiri calistir:"
echo "  source $KOK/ortam.sh"
echo
python3 -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'YOK')" || true
df -h "$KOK" | tail -1
