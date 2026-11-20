param([string]$PythonExecutable = '')

$ErrorActionPreference = 'Stop'
$kirbyRoot = Split-Path $PSScriptRoot -Parent
$kirbyEnv = Join-Path $kirbyRoot '.venv'
$kirbyPython = Join-Path $kirbyEnv 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $kirbyPython)) {
    if ($PythonExecutable) {
        & $PythonExecutable -m venv $kirbyEnv
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $kirbyEnv
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $kirbyEnv
    }
    else { throw 'Instala Python 3.11 o superior con tkinter antes de abrir la herramienta.' }
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de Python.' }
}

& $kirbyPython -c 'import sys; assert sys.version_info >= (3, 11); import tkinter'
if ($LASTEXITCODE -ne 0) { throw 'Se necesita Python 3.11 o superior con tkinter.' }
& $kirbyPython -c 'import serial, sounddevice, faster_whisper, kokoro_onnx, dotenv, yt_dlp, sys; from importlib.metadata import version; assert all(version(sys.argv[i]) == sys.argv[i+1] for i in range(1, len(sys.argv), 2))' pyserial 3.5 kokoro-onnx 0.4.7 python-dotenv 1.2.4 yt-dlp 2026.10.26 faster-whisper 1.2.1 ctranslate2 4.9.0 av 19.0.2
if ($LASTEXITCODE -ne 0) {
    & $kirbyPython -m pip install -r (Join-Path $kirbyRoot 'pc\requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias. Revisa la conexion a internet.' }
}

& $kirbyPython (Join-Path $kirbyRoot 'tools\recognition\prepare_recognizer.py')
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar el modelo local de espanol.' }

& $kirbyPython (Join-Path $kirbyRoot 'tools\speech\install_tts_model.py')
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la voz local de Kokoro.' }

& $kirbyPython -c 'import sys; from importlib.metadata import version; assert version(sys.argv[1]) == sys.argv[2]' tokenizers 0.23.3
if ($LASTEXITCODE -ne 0) {
    & $kirbyPython -m pip install -r (Join-Path $kirbyRoot 'pc\requirements-director.txt')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar las dependencias de Aubar Director.' }
}
& $kirbyPython (Join-Path $kirbyRoot 'tools\avatar\director\install_director_model.py')
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar Aubar Director local.' }

# This is the interactive application requested by the user; pythonw avoids
# a separate console while leaving the desktop window visible.
$kirbyWindowPython = Join-Path $kirbyEnv 'Scripts\pythonw.exe'
Start-Process -FilePath $kirbyWindowPython -ArgumentList '-m', 'pc.aubar_control' -WorkingDirectory $kirbyRoot -WindowStyle Normal
