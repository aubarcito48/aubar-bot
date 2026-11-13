"""Prepare supplied vertical clips, keeping native 24 fps and original sources."""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image
from prepare_aubar_frames import ROOT, cut_background, contact

def main(ffmpeg, stage='speech'):
    folder, name, video = {
        'speech': ('tramo-04-hablar', 'hablar', 'botbar-hablando.mp4'),
        'emotions': ('tramo-02-emociones', 'emociones', 'gemini_generated_video_dda76b2e.mp4'),
        'gestures': ('tramo-03-gestos-restantes', 'gestos', 'gemini_generated_video_fec8b636.mp4'),
    }[stage]
    source = ROOT / 'newAUBAR' / folder
    work = source / 'revision-video' / name
    output = source / 'frames-preparados' / name
    work.mkdir(parents=True, exist_ok=True)
    for variant in ('con-fondo', 'sin-fondo'):
        (output / variant).mkdir(parents=True, exist_ok=True)
    settings = json.loads((ROOT / 'newAUBAR/tramo-01-base-miradas/aubar-assets.json').read_text())['clips'][1]['matte']
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
        '-threads', '1', '-i', str(source / 'videos' / video), '-an',
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
        'source': 'videos/'+video, 'fps': 24, 'frameCount': 240,
        'size': [180, 320], 'matte': settings,
        'note': 'Continuous native frames with the approved vertical silhouette matte.'
    }, indent=2) + '\n')
    print(f'Prepared 240 {name} frames at 24 fps.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--stage', choices=('speech','emotions','gestures'), default='speech')
    args=parser.parse_args()
    main(args.ffmpeg, args.stage)
