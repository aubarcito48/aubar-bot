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
lines = ['#pragma once', '#include "avatar_types.h"',
         '// Generated from avatar-original/kirby.avatar.json.']
for key, value in [('BODY', definition['colors']['body']),
                   ('EYES', definition['colors']['eyes']),
                   ('BACKGROUND', '#0d1117')]:
    lines.append(f'constexpr uint16_t AVATAR_{key} = 0x{rgb565(value):04X};')
for key, value in [('WIDTH', body['primary']['width']),
                   ('HEIGHT', body['primary']['height'])]:
    lines.append(f'constexpr float AVATAR_{key} = {number(value)};')
lines.append('constexpr AvatarExpression AVATAR_EXPRESSIONS[] = {')
# The enum order in avatar_types.h must match this list. These are frontal
# adaptations; head perspective and web animation keyframes are not exported.
for label, source, blinks in [('neutral', 'neutral', True),
                              ('contento', 'joyful-wide', True),
                              ('sorprendido', 'surprised-wide-left', True),
                              ('dormido', 'eyes-closed', False)]:
    eyes = definition['expressions'][source]['eyes']
    shapes = []
    for side in ('left', 'right'):
        shapes.append('{' + ', '.join(number(eyes[side][key])
                                      for key in ('width', 'height', 'x', 'y', 'angle')) + '}')
    lines.append(f'  // {source}')
    lines.append('  {"' + label + '", ' + ', '.join(shapes) + ', ' +
                 number(eyes['spacing']) + ', ' + str(blinks).lower() + '},')
lines += ['};',
          'static_assert(sizeof(AVATAR_EXPRESSIONS) / sizeof(AVATAR_EXPRESSIONS[0]) ==',
          '              static_cast<uint8_t>(AvatarExpressionId::Count), "Expression count mismatch");',
          'constexpr const AvatarExpression& avatarExpression(AvatarExpressionId id) {',
          '  return AVATAR_EXPRESSIONS[static_cast<uint8_t>(id)];',
          '}']
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
