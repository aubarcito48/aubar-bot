"""Pinned, local Kokoro v1.0 CPU assets. No downloads during speech."""
from pathlib import Path

MODEL_DIR=Path(__file__).resolve().parents[2]/'models/kokoro-v1.0'
BASE_URL='https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
ASSETS=(
    ('kokoro-v1.0.onnx',325532387,'7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5'),
    ('voices-v1.0.bin',28214398,'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d'),
)
VOICE={'id':'ef_dora','name':'Dora · Kokoro local','language':'es'}
