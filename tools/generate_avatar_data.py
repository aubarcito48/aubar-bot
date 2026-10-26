"""Generate firmware geometry from the original Avatar Lab JSON (stdlib only)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
definition = json.loads((ROOT / 'avatar-original/kirby.avatar.json').read_text(encoding='utf-8'))

def rgb565(value):
    red, green, blue = bytes.fromhex(value.removeprefix('#'))
    return ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)

def number(value):
    return f'{float(value):.6f}f'

body = definition['body']
eyes = definition['expressions']['neutral']['eyes']
lines = ['#pragma once', '// Generated from avatar-original/kirby.avatar.json.']
for key, value in [('BODY', definition['colors']['body']),
                   ('EYES', definition['colors']['eyes']),
                   ('BACKGROUND', '#0d1117')]:
    lines.append(f'constexpr uint16_t AVATAR_{key} = 0x{rgb565(value):04X};')
for key, value in [('WIDTH', body['primary']['width']),
                   ('HEIGHT', body['primary']['height']),
                   ('EYE_GAP', eyes['spacing'])]:
    lines.append(f'constexpr float AVATAR_{key} = {number(value)};')
for side in ('left', 'right'):
    for key in ('width', 'height', 'y'):
        lines.append(f'constexpr float AVATAR_{side.upper()}_{key.upper()} = {number(eyes[side][key])};')
lines += ['struct AvatarNode { float x, y, width, height, angle; };',
          'constexpr AvatarNode AVATAR_NODES[] = {']
for node in body['nodes']:
    values = [*node['position'][:2], node['surface']['width'],
              node['surface']['height'], node['rotation'][2]]
    lines.append('  {' + ', '.join(map(number, values)) + '},')
lines.append('};')
target = ROOT / 'firmware/KirbyPantalla/avatar_data.h'
target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Generated {target}')
