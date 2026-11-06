@echo off
setlocal
title SLT Bilingual Core Installer
echo ====================================================
echo   SLT BILINGUAL CORE - INSTALADOR OFICIAL WINDOWS
echo ====================================================
echo.

where py >nul 2>nul
if %errorlevel% neq 0 (
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] No se encontro Python instalado.
        echo Por favor instale Python 3.12 de 64 bits desde python.org.
        pause
        exit /b 1
    )
    set PY_CMD=python
) else (
    set PY_CMD=py -3.12
)

echo [*] Utilizando interprete: %PY_CMD%
%PY_CMD% --version
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.12 no esta disponible.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [*] Creando entorno virtual .venv...
    %PY_CMD% -m venv .venv
    if %errorlevel% neq 0 goto error
)

call .venv\Scripts\activate.bat

echo [*] Actualizando pip...
python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 goto error

echo [*] Instalando dependencias desde requirements.txt...
python -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 goto error

echo [*] Instalando paquete en modo editable...
python -m pip install -e . --quiet
if %errorlevel% neq 0 goto error

if not exist "models" (
    mkdir models
)

if not exist "models\hand_landmarker.task" (
    echo [*] Descargando modelo oficial MediaPipe HandLandmarker...
    curl.exe -L "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" -o "models\hand_landmarker.task"
    if %errorlevel% neq 0 goto error
)

if not exist "models\slt_model.npz" (
    echo [*] Entrenando modelo de reconocimiento SLT...
    python scripts\train_model.py
    if %errorlevel% neq 0 goto error
)

echo.
echo [*] Verificando integracion del sistema...
python -c "import numpy, cv2, mediapipe, PySide6; print('[OK] Modulos principales validados')"
if %errorlevel% neq 0 goto error

echo.
echo ====================================================
echo   [OK] INSTALACION COMPLETADA EXITOSAMENTE
echo ====================================================
echo.
echo Para iniciar el traductor bilingue:
echo   call .venv\Scripts\activate.bat
echo   python app.py
echo.
pause
exit /b 0

:error
echo.
echo [ERROR] Ocurrio un fallo durante la instalacion.
echo Revise los mensajes de error superiores.
echo.
pause
exit /b 1
