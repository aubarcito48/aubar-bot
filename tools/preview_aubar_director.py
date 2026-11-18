"""Review Aubar's own gestures with Onyx; no Groq, playback, microphone or USB."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pc.aubar_control.aubar_director import direct_reply
from pc.aubar_control.catalog import CATALOG

CASES = [
    ('neutral-es', 'Hablá normalmente, sin actuar una emoción.', '¡Hola, Nahuel! Decime qué necesitás y lo vemos juntos.'),
    ('angry-es', 'Decime enojado: "¡Bien, Nahuel! Estoy bien. Decime qué necesitás y lo vemos juntos."', '¡Bien, Nahuel! Estoy bien. Decime qué necesitás y lo vemos juntos.'),
    ('sad-es', 'Respondé con tristeza: "Buenos días, Nahuel. Decime qué necesitás y lo vemos juntos."', 'Buenos días, Nahuel. Decime qué necesitás y lo vemos juntos.'),
    ('angry-en', 'Reply angrily: "Good morning, Nahuel. Tell me what you need, and we will work on it together."', 'Good morning, Nahuel. Tell me what you need, and we will work on it together.'),
    ('mention-es', 'Explicame qué significa estar enojado.', 'El enojo es una emoción. Mencionarlo no me pide que lo actúe.'),
]
# Existing clip ranges from portrait_routes.h; this review never replaces firmware routes.
CLIPS = {
    'angry': ('tramo-02-emociones', 'emociones', 96, 112),
    'sad': ('tramo-02-emociones', 'emociones', 136, 160),
    'happy': ('tramo-03-gestos-restantes', 'gestos', 188, 204),
    'scared': ('tramo-02-emociones', 'emociones', 168, 192),
    'confused': ('tramo-02-emociones', 'emociones', 64, 88),
    'suspicious': ('tramo-02-emociones', 'emociones', 16, 40),
    'shy': ('tramo-02-emociones', 'emociones', 208, 222),
    'bored': ('tramo-03-gestos-restantes', 'gestos', 20, 44),
    'surprised': ('tramo-03-gestos-restantes', 'gestos', 56, 88),
    'proud': ('tramo-03-gestos-restantes', 'gestos', 100, 120),
    'laughing': ('tramo-03-gestos-restantes', 'gestos', 128, 168),
    'excited': ('tramo-03-gestos-restantes', 'gestos', 172, 196),
    'playful': ('tramo-03-gestos-restantes', 'gestos', 204, 224),
    'celebrate': ('tramo-03-gestos-restantes', 'gestos', 172, 208),
    'curious': ('tramo-01-base-miradas', 'vertical', 108, 144),
    'neutral': ('tramo-01-base-miradas', 'vertical', 0, 23),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', action='store_true', help='Synthesize local Onyx WAVs without playing them')
    args = parser.parse_args()
    output = ROOT/'tmp/aubar-director-v1'
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    engine = None
    if args.audio:
        import numpy as np
        import onnxruntime as ort
        from kokoro_onnx import Kokoro
        from pc.aubar_control.tts_assets import ASSETS, MODEL_DIR, VOICE
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(str(MODEL_DIR/ASSETS[0][0]), sess_options=options,
                                       providers=['CPUExecutionProvider'])
        engine = Kokoro.from_session(session, str(MODEL_DIR/ASSETS[1][0]))
    for identifier, question, text in CASES:
        started = time.perf_counter()
        result = direct_reply(text, question)
        row = {'id': identifier, 'question': question, 'text': result.reply.text,
               'action': result.reply.action.argument, 'origin': result.origin,
               'predicted': result.label, 'confidence': result.confidence,
               'director_ms': (time.perf_counter()-started)*1000, 'frames': [], 'audio': None}
        segment = result.reply.segments[0] if result.reply.segments else None
        row['controls'] = {'speed': segment.speed if segment else 1., 'energy': segment.energy if segment else 1.,
                           'pause_ms': segment.pause_ms if segment else 0}
        clip = CLIPS[row['action']]
        source = ROOT/'newAUBAR'/clip[0]/'frames-preparados'/clip[1]/'sin-fondo'
        for frame in range(clip[2], clip[3]+1):
            path = source/f'{frame:03d}.webp'
            if not path.is_file():
                raise ValueError(f'Missing own Aubar frame: {path}')
            destination = output/'frames'/row['action']/path.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            row['frames'].append(destination.relative_to(output).as_posix())
        if engine:
            from pc.aubar_control.speech_pronunciation import pronunciation_language, speech_speed
            language = pronunciation_language(row['text'])
            audio, rate = engine.create(row['text'], voice=VOICE['id'], lang=language,
                                         speed=speech_speed(0)*row['controls']['speed'])
            audio = np.clip(audio*row['controls']['energy'], -.98, .98)
            audio = np.concatenate((audio, np.zeros(round(rate*row['controls']['pause_ms']/1000))))
            pcm = (audio*32767).astype('<i2')
            path = output/f'{identifier}.wav'
            with wave.open(str(path), 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(rate); wav.writeframes(pcm.tobytes())
            row.update(audio=path.name, duration_s=len(audio)/rate, language=language)
        rows.append(row)
        print(identifier, row['action'], row['origin'], round(row['confidence'], 3), flush=True)
    data = {'catalog': CATALOG, 'cases': rows, 'voice': 'am_onyx', 'scope': 'gesture selection and Onyx controls; not phoneme lip sync'}
    (output/'review.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # JSON is encoded as a JS string to keep all test text inert.
    script_data = json.dumps(json.dumps(data, ensure_ascii=True)).replace('<', '\\u003c')
    html = '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aubar Director · prueba local</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f3f8;color:#302d40;font:17px/1.6 "Segoe UI",sans-serif}main{max-width:1000px;margin:auto;padding:30px}h1{margin:0}select,button{font:inherit;padding:10px;border:1px solid #c6bed1;border-radius:8px;background:white;color:inherit}select{max-width:100%}.review{display:grid;grid-template-columns:240px 1fr;gap:28px;padding:24px;background:white;border:1px solid #dcd4e6;border-radius:12px}.portrait{background:#102939;border-radius:12px;text-align:center}img{width:180px;height:320px;object-fit:contain;display:block;margin:auto}audio{width:100%}pre{white-space:pre-wrap;font-size:14px;background:#f5f3f8;padding:12px;border-radius:8px}.scope{padding:12px;border-left:4px solid #b36a90}label{display:block;margin:20px 0}blockquote{margin:0;padding:12px;border-left:3px solid #d5a4c1}@media(max-width:640px){.review{grid-template-columns:1fr}.portrait{max-width:240px;margin:auto}}
</style><main><h1>Aubar Director</h1><p>Prueba local con el catálogo de Aubar y Kokoro · Onyx.</p><p class="scope">Esta prueba compara elección de gesto y controles de voz. La animación mostrada es el gesto original; todavía no representa fonemas ni reproduce la composición de boca del ESP32. El porcentaje del clasificador no mide sincronización labial.</p><label>Ejemplo <select id="cases"></select></label><section class="review"><div class="portrait"><img id="portrait" alt="Gesto original de Aubar"></div><div><h2 id="action"></h2><p id="request"></p><blockquote id="words"></blockquote><p><button id="restart">Reproducir desde el inicio</button></p><audio id="audio" controls></audio><pre id="details"></pre></div></section></main><script>
const data=JSON.parse(DATA);const selector=document.getElementById('cases'),audio=document.getElementById('audio'),portrait=document.getElementById('portrait');let current=data.cases[0];
for(const [i,row] of data.cases.entries()){const option=document.createElement('option');option.value=i;option.textContent=row.id;selector.append(option)}
function choose(){audio.pause();current=data.cases[+selector.value];document.getElementById('action').textContent=current.action;document.getElementById('request').textContent=current.question;document.getElementById('words').textContent=current.text;document.getElementById('details').textContent=JSON.stringify({origin:current.origin,predicted:current.predicted,confidence:current.confidence,controls:current.controls,director_ms:current.director_ms},null,2);if(current.audio)audio.src=current.audio;else audio.removeAttribute('src');portrait.src=current.frames[0]}
selector.addEventListener('change',choose);document.getElementById('restart').addEventListener('click',()=>{audio.currentTime=0;if(current.audio)audio.play().catch(()=>{})});function draw(){if(current.frames.length&&!audio.paused){const tick=Math.floor(audio.currentTime*24);portrait.src=current.frames[Math.min(tick,current.frames.length-1)]}requestAnimationFrame(draw)}choose();draw();
</script></html>'''.replace('JSON.parse(DATA)', 'JSON.parse('+script_data+')')
    (output/'index.html').write_text(html, encoding='utf-8')
    print(output/'index.html', flush=True)


if __name__ == '__main__':
    main()
