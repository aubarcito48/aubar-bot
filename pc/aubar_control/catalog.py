"""Shared generated catalog; IDs match the firmware, labels are for the panel."""
import json
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name('avatar_catalog.json').read_text(encoding='utf-8'))
EXPRESSIONS = {item['id']: item['label'] for item in CATALOG['expressions']}
ANIMATIONS = {item['id']: item['label'] for item in CATALOG['animations']}
