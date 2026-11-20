"""Prepare the only supported local speech recognizer."""
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    subprocess.run([sys.executable, str(Path(__file__).with_name('install_whisper_model.py'))], check=True)
