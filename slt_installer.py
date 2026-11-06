#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT-Core Bootstrap & Environment Health Installer.
Verifies system requirements, creates virtualenv, installs packages, downloads models,
and executes self-diagnostics.
"""
import os
import sys
import platform
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def check_system():
    print(f"[*] Sistema Operativo: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"[*] Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        sys.exit("[ERROR] Se requiere Python 3.10 o superior (recomendado 3.12).")

def install():
    check_system()
    venv_dir = ROOT / ".venv"
    if not venv_dir.exists():
        print("[*] Creando entorno virtual...")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])

    py_bin = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python3")

    print("[*] Instalando dependencias desde requirements.txt...")
    subprocess.check_call([str(py_bin), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    subprocess.check_call([str(py_bin), "-m", "pip", "install", "-r", "requirements.txt", "--quiet"])
    subprocess.check_call([str(py_bin), "-m", "pip", "install", "-e", ".", "--quiet"])

    models_dir = ROOT / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    task_file = models_dir / "hand_landmarker.task"
    if not task_file.exists():
        print("[*] Descargando modelo oficial MediaPipe HandLandmarker...")
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        urllib.request.urlretrieve(url, task_file)

    model_file = models_dir / "slt_model.npz"
    if not model_file.exists():
        print("[*] Generando y entrenando modelo SLT...")
        subprocess.check_call([str(py_bin), "scripts/train_model.py"])

    print("\n[OK] Instalación y verificación completadas con éxito.")
    print("Para iniciar la aplicación:")
    if sys.platform == "win32":
        print(r"  .venv\Scripts\activate.bat")
    else:
        print("  source .venv/bin/activate")
    print("  python app.py")

if __name__ == "__main__":
    install()
