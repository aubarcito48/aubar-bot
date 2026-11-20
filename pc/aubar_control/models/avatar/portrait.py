"""Desktop playback of the ESP32's existing indexed frame bank.

No generated replacement artwork, downloads or Qt dependency. Geometry, palette,
frame offsets, catalog routes and speech faces are read from the firmware files.
Frame timing/compositing mirrors portrait_player.h for desktop visual review;
this is not a hardware/display timing emulator.
"""
from collections import OrderedDict
from pathlib import Path
import re
import time
import zlib

import numpy as np

from ...paths import PROJECT_ROOT
from .catalog import CATALOG


class PortraitBank:
    def __init__(self, folder=None):
        folder = Path(folder or PROJECT_ROOT/'firmware/KirbyPantalla')
        header = (folder/'src/portrait/portrait_assets.h').read_text(encoding='utf-8')
        self.constants = {name: int(value, 0) for name, value in re.findall(
            r'\b(PORTRAIT_[A-Z_]+)\s*=\s*(0x[0-9a-fA-F]+|\d+)', header)}
        self.width = self.constants['PORTRAIT_WIDTH']
        self.height = self.constants['PORTRAIT_HEIGHT']
        self.count = self.constants['PORTRAIT_FRAME_COUNT']
        self.blob = (folder/'portrait_assets.dat').read_bytes()
        self.arrays = {}
        for key in ('DELTA', 'OFFSETS', 'LENGTHS', 'PALETTE'):
            match = re.search(r'PORTRAIT_'+key+r'\[\]\s*=\s*\{([^}]+)\}', header)
            if match is None:
                raise ValueError('El banco de Aubar no tiene sus tablas completas.')
            self.arrays[key] = np.array([int(v.strip(), 0) for v in match[1].split(',') if v.strip()], dtype=np.uint32)
        if any(len(self.arrays[k]) != self.count for k in ('DELTA', 'OFFSETS', 'LENGTHS')):
            raise ValueError('Las tablas del retrato no coinciden.')
        self.cache = OrderedDict()
        routes = (folder/'src/portrait/portrait_routes.h').read_text(encoding='utf-8')
        expressions = re.search(r'poses\[\]\s*=\s*\{([^}]+)\}', routes)[1]
        animations = re.search(r'scenes\[\]\s*=\s*\{([^}]+)\}', routes)[1]
        self.expressions = dict(zip((v['id'] for v in CATALOG['expressions']), re.findall(r'PortraitScene::(\w+)', expressions)))
        self.animations = dict(zip((v['id'] for v in CATALOG['animations']), re.findall(r'PortraitScene::(\w+)', animations)))
        enum = (folder/'src/avatar/avatar_data.h')
        # Explicit C++ expression overrides use enum names; order is catalog order.
        if not enum.exists():
            enum = folder/'src/avatar/avatar_types.h'
        enum_text = '\n'.join(p.read_text(encoding='utf-8') for p in (folder/'src/avatar').glob('*.h'))
        ids = re.search(r'enum class AvatarExpressionId[^\{]*\{([^}]+)\}', enum_text)
        names = [v.strip().split('=')[0].strip() for v in ids[1].split(',')] if ids else []
        lookup = dict(zip(names, (v['id'] for v in CATALOG['expressions'])))
        expression_section = routes.split('constexpr PortraitScene portraitAnimationScene')[0]
        for cases, scene in re.findall(r'((?:case AvatarExpressionId::\w+:\s*)+)return PortraitScene::(\w+);', expression_section):
            for name in re.findall(r'AvatarExpressionId::(\w+)', cases):
                if name in lookup:
                    self.expressions[lookup[name]] = scene
        rig = (folder/'src/portrait/portrait_speech_face.h').read_text(encoding='utf-8')
        self.faces = {}
        for cases, frame, x, y in re.findall(r'((?:case PortraitScene::\w+:\s*)+)return\s*\{([^,]+),(\d+),(\d+)\};', rig):
            for scene in re.findall(r'PortraitScene::(\w+)', cases):
                self.faces[scene] = (self.number(frame), int(x), int(y))

    def number(self, expression):
        return sum(self.constants[p.strip()] if p.strip() in self.constants else int(p.strip(), 0)
                   for p in expression.split('+'))

    def decode(self, frame):
        if not 0 <= frame < self.count:
            raise ValueError('Cuadro fuera del banco del retrato.')
        if frame in self.cache:
            self.cache.move_to_end(frame)
            return self.cache[frame]
        key = frame
        while self.arrays['DELTA'][key]:
            key -= 1
        pixels = None
        for index in range(key, frame+1):
            if index in self.cache:
                pixels = self.cache[index]
                continue
            offset, size = int(self.arrays['OFFSETS'][index]), int(self.arrays['LENGTHS'][index])
            raw = zlib.decompress(self.blob[offset:offset+size])
            if len(raw) != self.width*self.height:
                raise ValueError('Cuadro del retrato incompleto.')
            decoded = np.frombuffer(raw, dtype=np.uint8).reshape(self.height, self.width)
            pixels = np.bitwise_xor(pixels, decoded) if self.arrays['DELTA'][index] else decoded.copy()
            pixels.setflags(write=False)
            self.cache[index] = pixels
            while len(self.cache) > 32:
                self.cache.popitem(last=False)
        return pixels

    def frame(self, scene, elapsed):
        tick = int(max(0, elapsed)*24)
        c = self.constants
        fixed = {'Front': ('STILLS', 0), 'Computer': ('STILLS', 1), 'Thinking': ('STILLS', 2),
                 'Sleeping': ('STILLS', 3), 'MouthHalf': ('STILLS', 4), 'MouthOpen': ('STILLS', 5), 'Smile': ('VERTICAL', 222)}
        if scene in fixed:
            group, offset = fixed[scene]
            return c['PORTRAIT_'+group]+offset
        if scene in ('IdleVideo', 'SearchVideo'):
            return c['PORTRAIT_VERTICAL' if scene == 'IdleVideo' else 'PORTRAIT_HORIZONTAL']+tick % 240
        loops = {'ListeningVideo': ('VERTICAL', 0, 90), 'HappyVideo': ('VERTICAL', 192, 47),
                 'UpVideo': ('VERTICAL', 108, 36), 'Laughing': ('GESTURES', 128, 40),
                 'Excited': ('GESTURES', 172, 24), 'Playful': ('GESTURES', 204, 20), 'Celebrate': ('GESTURES', 172, 36)}
        if scene in loops:
            group, base, span = loops[scene]
            phase = tick % (span*2)
            return c['PORTRAIT_'+group]+base+(phase if phase <= span else 2*span-phase)
        poses = {'Left': ('VERTICAL', 90, -18), 'Right': ('VERTICAL', 24, 18),
                 'Down': ('VERTICAL', 178, -22), 'Up': ('VERTICAL', 108, 18),
                 'Suspicious': ('EMOTIONS', 16, 24), 'Confused': ('EMOTIONS', 64, 24),
                 'Angry': ('EMOTIONS', 96, 16), 'Sad': ('EMOTIONS', 136, 24),
                 'Scared': ('EMOTIONS', 168, 24), 'Shy': ('EMOTIONS', 208, 14),
                 'Bored': ('GESTURES', 20, 24), 'Surprised': ('GESTURES', 56, 32),
                 'Proud': ('GESTURES', 100, 20), 'Joyful': ('GESTURES', 188, 16)}
        group, base, end = poses.get(scene, ('STILLS', 0, 0))
        return c['PORTRAIT_'+group]+base+min(tick, abs(end))*(1 if end >= 0 else -1)


def mix565(source, target, weight):
    source = np.asarray(source, dtype=np.uint32)
    target = np.asarray(target, dtype=np.uint32)
    r = ((source >> 11)*(256-weight)+(target >> 11)*weight) >> 8
    g = (((source >> 5)&63)*(256-weight)+((target >> 5)&63)*weight) >> 8
    b = ((source&31)*(256-weight)+(target&31)*weight) >> 8
    return (r << 11) | (g << 5) | b


class PortraitPlayer:
    def __init__(self, bank=None, clock=time.monotonic):
        self.bank = bank or PortraitBank()
        self.clock = clock
        self.scene = 'IdleVideo'
        self.started = clock()
        self.speech_started = self.started
        self.speaking = False
        self.previous = None
        self.pixels = None
        self.signature = None
        self.frame_id = 0

    def select(self, action):
        if action.command == 'EXPRESSION':
            scene = self.bank.expressions.get(action.argument, 'Front')
        elif action.command == 'ANIMATION':
            scene = self.bank.animations.get(action.argument, 'Front')
        elif action.command == 'LOOK':
            scene = {'izquierda': 'Left', 'derecha': 'Right', 'centro': 'Front'}[action.argument]
        elif action.command == 'MODE':
            scene = 'IdleVideo' if action.argument == 'auto' else 'Front'
        else:
            return
        if action.look:
            scene = {'izquierda': 'Left', 'derecha': 'Right', 'centro': 'Front'}[action.look]
        self.scene = scene
        self._transition()

    def _transition(self):
        self.previous = self.pixels.copy() if self.pixels is not None else None
        self.started = self.clock()
        self.signature = None

    def set_speaking(self, value):
        value = bool(value)
        if value != self.speaking:
            self.speaking = value
            if value:
                self.speech_started = self.clock()
            self._transition()

    def render(self):
        now, bank = self.clock(), self.bank
        elapsed = now-self.started
        face = bank.faces.get(self.scene) if self.speaking else None
        track = self.speaking and (face or self.scene in ('Front', 'IdleVideo', 'ListeningVideo', 'SearchVideo'))
        if track:
            span = bank.constants['PORTRAIT_SPEECH_COUNT']-1
            phase = int((now-self.speech_started)*24) % (span*2)
            frame = bank.constants['PORTRAIT_SPEECH']+(phase if phase <= span else span*2-phase)
        else:
            frame = bank.frame(self.scene, elapsed)
        blend = min(256, int(max(0, elapsed)*256/.220)) if self.previous is not None else 256
        signature = (self.scene, frame, face, blend)
        if signature == self.signature:
            return None
        palette = bank.arrays['PALETTE']
        indices = bank.decode(frame)
        target = palette[bank.decode(face[0]) if face else indices].copy()
        if face:
            _, x, y = face
            yy, xx = np.mgrid[-10:11, -15:16]
            edge = np.minimum(16-np.abs(xx), 11-np.abs(yy))
            weight = np.minimum(256, edge*64).astype(np.uint32)
            target[y-10:y+11, x-15:x+16] = mix565(target[y-10:y+11, x-15:x+16], palette[indices[132:153, 75:106]], weight)
        self.pixels = mix565(self.previous, target, blend) if blend != 256 else target
        rgba = np.empty((bank.height, bank.width, 4), dtype=np.uint8)
        rgba[..., 0] = ((self.pixels >> 11)*255//31)
        rgba[..., 1] = (((self.pixels >> 5)&63)*255//63)
        rgba[..., 2] = ((self.pixels&31)*255//31)
        rgba[..., 3] = np.where(self.pixels == bank.constants['PORTRAIT_BACKGROUND'], 0, 255)
        self.signature, self.frame_id = signature, frame
        return rgba.tobytes()
