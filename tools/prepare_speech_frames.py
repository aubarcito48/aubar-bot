"""Prepare the supplied speech clip, keeping native 24 fps and original sources."""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image
from prepare_aubar_frames import ROOT, cut_background, contact

def main(ffmpeg):
    source = ROOT / 'newAUBAR/tramo-04-hablar'
    work = source / 'revision-video/hablar'
    output = source / 'frames-preparados/hablar'
    work.mkdir(parents=True, exist_ok=True)
    for name in ('con-fondo', 'sin-fondo'):
        (output / name).mkdir(parents=True, exist_ok=True)
    settings = json.loads((ROOT / 'newAUBAR/tramo-01-base-miradas/aubar-assets.json').read_text())['clips'][1]['matte']
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
        '-threads', '1', '-i', str(source / 'videos/botbar-hablando.mp4'), '-an',
        '-vf', 'scale=180:320:flags=lanczos', '-filter_threads', '1',
        '-fps_mode', 'passthrough', '-frames:v', '240', '-start_number', '0',
        str(work / '%03d.png')], check=True, timeout=120)
    frames = []
    for i in range(240):
        with Image.open(work / f'{i:03d}.png') as im:
            im = im.convert('RGB')
        frame = cut_background(im, settings)
        im.save(output / 'con-fondo' / f'{i:03d}.webp', lossless=True)
        frame.save(output / 'sin-fondo' / f'{i:03d}.webp', lossless=True)
        frames.append(frame)
    contact(frames, output / 'revision-sin-fondo.jpg', list(range(0, 240, 6)))
    (source / 'frames-preparados/manifest.json').write_text(json.dumps({
        'source': 'videos/botbar-hablando.mp4', 'fps': 24, 'frameCount': 240,
        'size': [180, 320], 'matte': settings,
        'note': 'Continuous native frames; audio playback controls the firmware speech overlay.'
    }, indent=2) + '\n')
    print('Prepared 240 speech frames at 24 fps.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', required=True)
    main(parser.parse_args().ffmpeg)
