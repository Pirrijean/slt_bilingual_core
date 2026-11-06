#!/usr/bin/env bash
set -e

echo "===================================================="
echo "   SLT BILINGUAL CORE - INSTALADOR LINUX / MACOS"
echo "===================================================="
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] Python 3 no está instalado."
    exit 1
fi

python3 --version

if [ ! -d ".venv" ]; then
    echo "[*] Creando entorno virtual .venv..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "[*] Actualizando pip..."
python -m pip install --upgrade pip --quiet

echo "[*] Instalando dependencias..."
python -m pip install -r requirements.txt --quiet

echo "[*] Instalando paquete en modo editable..."
python -m pip install -e . --quiet

mkdir -p models

if [ ! -f "models/hand_landmarker.task" ]; then
    echo "[*] Descargando modelo oficial MediaPipe HandLandmarker..."
    curl -L "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" -o "models/hand_landmarker.task"
fi

if [ ! -f "models/slt_model.npz" ]; then
    echo "[*] Entrenando modelo de reconocimiento SLT..."
    python scripts/train_model.py
fi

echo ""
echo "[*] Verificando dependencias..."
python -c "import cv2, numpy, mediapipe, PySide6; print('[OK] Módulos principales validados')"

echo ""
echo "===================================================="
echo "   [OK] INSTALACIÓN COMPLETADA EXITOSAMENTE"
echo "===================================================="
echo "Ejecuta:"
echo "  source .venv/bin/activate"
echo "  python app.py"
