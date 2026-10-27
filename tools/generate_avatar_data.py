"""Generate the complete firmware and PC catalogs from the original avatar."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
definition = json.loads((ROOT/'avatar-original/kirby.avatar.json').read_text(encoding='utf-8'))
primary=definition['body']['primary']
assert all(primary[k]==240 for k in ('width','height','depth')), 'Renderer requires the exported 240-unit sphere'
assert len(definition['body']['nodes'])==2, 'Renderer requires the two exported arm nodes'
LEGACY = [('neutral','neutral','Neutral','Neutral'),('contento','joyful-wide','Happy','Contento'),
          ('sorprendido','surprised-wide-left','Surprised','Sorprendido'),
          ('dormido','eyes-closed','Sleeping','Dormido'),('enojado','angry-right','Angry','Enojado')]
LABELS = [
 'Mirada lateral arriba','Mirada abajo','Escéptico derecha','Atento pequeño','Mirada amplia abajo',
 'Sorpresa izquierda','Somnoliento','Curioso izquierda','Asimétrico abajo derecha','Atento izquierda',
 'Alegre abajo derecha','Escéptico izquierda','Mirada derecha','Enojado izquierda','Juguetón derecha',
 'Asimétrico arriba izquierda','Mirada suave abajo','Mirada amplia abajo izquierda','Adormilado',
 'Sospechoso derecha','Tímido','Cejas enojadas','Inquieto izquierda']
ANIMATION_LABELS = ['Dormir','Despertar','Reposo','Escuchar','Pensar','Buscar','Trabajar',
 'Entusiasmarse','Aburrirse','Sospechar','Enojarse','Adormecerse','Alegría','Curiosear',
 'Confundirse','Sorprenderse','Orgullo','Timidez','Tristeza','Reír','Asustarse','Jugar','Celebrar']

def enum(name):
    return ''.join(x.capitalize() for x in name.split('-'))
def num(value):
    return f'{float(value):.6f}f'
def rgb(value):
    r,g,b=bytes.fromhex(value.removeprefix('#'))
    return ((r>>3)<<11)|((g>>2)<<5)|(b>>3)
def boolean(value):
    return str(bool(value)).lower()
def write(path,content):
    (ROOT/path).write_text(content+'\n',encoding='utf-8')

used={x[1] for x in LEGACY}
remaining=[n for n in definition['expressionOrder'] if n not in used]
assert len(remaining)==len(LABELS)
entries=LEGACY+[(n,n,enum(n),label) for n,label in zip(remaining,LABELS)]
source_ids={source:i for i,(_,source,_,_) in enumerate(entries)}
animations=list(definition['animationOrder'])
write('firmware/KirbyPantalla/avatar_ids.h',
 '#pragma once\n#include <stdint.h>\n// Generated; preserve the first five expression IDs.\n'
 +'enum class AvatarExpressionId : uint8_t { '+', '.join(x[2] for x in entries)+', Count };\n'
 +'enum class AvatarAnimationId : uint8_t { '+', '.join(enum(n) for n in animations)+', Count, None = 255 };')
lines=['#pragma once','#include "avatar_types.h"','// Generated from avatar-original/kirby.avatar.json.']
for k,v in [('BODY',definition['colors']['body']),('EYES',definition['colors']['eyes']),('BACKGROUND','#0d1117')]:
    lines.append(f'constexpr uint16_t AVATAR_{k} = 0x{rgb(v):04X};')
for key in ('width','height'):
    lines.append(f'constexpr float AVATAR_{key.upper()} = {num(definition["body"]["primary"][key])};')
lines.append('constexpr AvatarExpression AVATAR_EXPRESSIONS[] = {')
for name,source,identifier,label in entries:
    expression=definition['expressions'][source]
    eyes=expression['eyes']
    shapes=['{'+', '.join(num(eyes[side][k]) for k in ('width','height','x','y','angle'))+'}' for side in ('left','right')]
    colors={**definition['colors'],**expression.get('colors',{})}
    motion=lambda key: {'none':'None','shake':'Shake','slowDrift':'SlowDrift'}[expression['motion'][key]]
    blinks=source not in ('eyes-closed','drowsy-closed','sleepy-squint')
    values=['"'+name+'"',*shapes,num(eyes['spacing']),boolean(blinks),
            *(num(expression['head'][k]) for k in ('x','y','z')),
            f'0x{rgb(colors["body"]):04X}',f'0x{rgb(colors["eyes"]):04X}',
            'AvatarMotion::'+motion('body'),'AvatarMotion::'+motion('eyes'),num(expression['perspective'])]
    lines+=['  // '+source,'  {'+', '.join(values)+'},']
lines+=['};','constexpr const AvatarExpression& avatarExpression(AvatarExpressionId id) {',
        '  return AVATAR_EXPRESSIONS[static_cast<uint8_t>(id)];','}',
        'struct AvatarNode { float x, y, width, height, angle, z, depth; };',
        'constexpr AvatarNode AVATAR_NODES[] = {']
for node in definition['body']['nodes']:
    assert node['rotation'][:2]==[0,0]
    vals=[*node['position'][:2],node['surface']['width'],node['surface']['height'],
          node['rotation'][2],node['position'][2],node['surface']['depth']]
    lines.append('  {'+', '.join(num(v) for v in vals)+'},')
lines+=['};']
write('firmware/KirbyPantalla/avatar_data.h','\n'.join(lines))
steps=[]; configs=[]
for name in animations:
    a=definition['animations'][name]
    assert a['playbackMode']=='loop'
    start=len(steps)
    for step in a['steps']:
        assert step['transition']=='smooth'
        steps.append((source_ids[step['expression']],step['holdMs'],step['transitionMs']))
    b=a['blink']
    configs.append((name,start,len(a['steps']),b))
lines=['#pragma once','#include "avatar_data.h"','// Original sequence order, transitions, holds and blink ranges.',
       'struct AvatarAnimationStep { AvatarExpressionId expression; uint32_t holdMs, transitionMs; };',
       'struct AvatarBlinkConfig { bool enabled; uint32_t initialDelayMs, minIntervalMs, maxIntervalMs, durationMs; };',
       'struct AvatarAnimation { const char* name; uint16_t first; uint8_t count; AvatarBlinkConfig blink; };',
       'constexpr AvatarAnimationStep AVATAR_STEPS[] = {']
for i,hold,transition in steps:
    lines.append(f'  {{AvatarExpressionId::{entries[i][2]}, {hold}, {transition}}},')
lines+=['};','constexpr AvatarAnimation AVATAR_ANIMATIONS[] = {']
for name,first,count,b in configs:
    blink=', '.join([boolean(b['enabled']),*(str(b[k]) for k in ('initialDelayMs','minIntervalMs','maxIntervalMs','durationMs'))])
    lines.append(f'  {{"{name}", {first}, {count}, {{{blink}}}}},')
lines+=['};','constexpr const AvatarAnimation& avatarAnimation(AvatarAnimationId id) {',
        '  return AVATAR_ANIMATIONS[static_cast<uint8_t>(id)];','}']
write('firmware/KirbyPantalla/animation_data.h','\n'.join(lines))
catalog={'expressions':[dict(id=n,source=s,label=label) for n,s,_,label in entries],
         'animations':[dict(id=n,label=label) for n,label in zip(animations,ANIMATION_LABELS)]}
write('pc/aubar_control/avatar_catalog.json',json.dumps(catalog,ensure_ascii=False,indent=2))
print(f'Generated {len(entries)} expressions, {len(animations)} animations and {len(steps)} steps.')
