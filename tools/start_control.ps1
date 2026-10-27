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
& $kirbyPython -c 'import serial, sounddevice, vosk, kokoro_onnx, dotenv, sys; from importlib.metadata import version; assert serial.VERSION == str(3.5); assert version(sys.argv[1]) == sys.argv[2]; assert version(sys.argv[3]) == sys.argv[4]' kokoro-onnx 0.4.7 python-dotenv 1.2.4
if ($LASTEXITCODE -ne 0) {
    & $kirbyPython -m pip install -r (Join-Path $kirbyRoot 'pc\requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias. Revisa la conexion a internet.' }
}

& $kirbyPython (Join-Path $kirbyRoot 'tools\install_voice_model.py')
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar el modelo local de espanol.' }

& $kirbyPython (Join-Path $kirbyRoot 'tools\install_tts_model.py')
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la voz local de Dora.' }

# This is the interactive application requested by the user; pythonw avoids
# a separate console while leaving the desktop window visible.
$kirbyWindowPython = Join-Path $kirbyEnv 'Scripts\pythonw.exe'
Start-Process -FilePath $kirbyWindowPython -ArgumentList '-m', 'pc.aubar_control' -WorkingDirectory $kirbyRoot -WindowStyle Normal
