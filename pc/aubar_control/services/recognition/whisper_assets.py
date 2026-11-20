"""Pinned multilingual Whisper small weights; downloaded only by the installer."""
from pc.aubar_control.paths import PROJECT_ROOT
from pathlib import Path

MODEL_DIR=PROJECT_ROOT/'models/faster-whisper-small'
REPOSITORY='Systran/faster-whisper-small'
REVISION='536b0662742c02347bc0e980a01041f333bce120'
ASSETS=(
    ('config.json',2370,'b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828'),
    ('tokenizer.json',2203239,'fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab'),
    ('vocabulary.txt',459861,'34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913'),
    ('model.bin',483546902,'3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671'),
)
