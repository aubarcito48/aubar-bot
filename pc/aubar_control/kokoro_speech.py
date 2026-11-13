"""One hidden worker per request: local synthesis/playback, killed on stop.

Only JSON is written to stdout. No network, shell commands or audio files.
"""
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pc.aubar_control.tts_assets import ASSETS, MODEL_DIR, VOICE
from pc.aubar_control.speech_pronunciation import pronunciation_language, speech_speed
from pc.aubar_control.ai_avatar import parse_segments


def execute(request):
    if not isinstance(request,dict) or request.get('action') not in ('voices','speak'):
        return {'ok':False,'code':'INVALID_REQUEST'}
    if any(not (MODEL_DIR/name).is_file() or (MODEL_DIR/name).stat().st_size!=size
           for name,size,_ in ASSETS):
        return {'ok':False,'code':'MODEL_MISSING'}
    if request['action']=='voices':
        return {'ok':True,'voices':[VOICE]}
    text=request.get('text')
    volume=request.get('volume');rate=request.get('rate')
    if (not isinstance(text,str) or not text.strip() or len(text)>2000 or '\x00' in text
        or type(volume) is not int or not 0<=volume<=100
        or type(rate) is not int or not -10<=rate<=10):
        return {'ok':False,'code':'INVALID_REQUEST'}
    try:
        segments=parse_segments(request['segments'],text) if 'segments' in request else ()
    except (ValueError,TypeError):
        return {'ok':False,'code':'INVALID_REQUEST'}
    try:
        from kokoro_onnx import Kokoro
        import sounddevice as sd
    except ImportError:
        return {'ok':False,'code':'DEPENDENCY_MISSING'}
    # Model/tokenizer libraries may log; stdout must remain a single JSON result.
    with redirect_stdout(sys.stderr):
        engine=Kokoro(str(MODEL_DIR/ASSETS[0][0]),str(MODEL_DIR/ASSETS[1][0]))
        timeline=[]
        if segments:
            import numpy as np
            parts=[];offset=0
            for segment in segments:
                samples,sample_rate=engine.create(segment.text,voice=VOICE['id'],
                    speed=max(.5,min(2.0,speech_speed(rate)*segment.speed)),lang=pronunciation_language(segment.text))
                spoken=len(samples)/sample_rate
                pause=segment.pause_ms/1000
                parts.append(np.clip(samples*segment.energy,-.98,.98))
                parts.append(np.zeros(round(sample_rate*pause),dtype=np.float32))
                timeline.append({'from':offset,'speech_end':offset+spoken,'until':offset+spoken+pause,
                    'avatar_type':'animation' if segment.action.command=='ANIMATION' else 'expression',
                    'avatar_id':segment.action.argument,'delivery':segment.delivery})
                offset+=spoken+pause
            samples=np.concatenate(parts)
        else:
            samples,sample_rate=engine.create(text,voice=VOICE['id'],
                speed=speech_speed(rate),lang=pronunciation_language(text))
        try:
            sd.play(samples*(volume/100),sample_rate)
            marker = request.get('playback_state')
            if marker:
                started = time.monotonic()
                Path(marker).write_text(json.dumps({'start': started,
                    'end': started + len(samples)/sample_rate,'timeline':timeline}), encoding='utf-8')
            sd.wait()
        finally:
            sd.stop()
            if request.get('playback_state'):
                Path(request['playback_state']).write_text('{}', encoding='utf-8')
    return {'ok':True,'voice':VOICE}


def main():
    try:
        response=execute(json.load(sys.stdin))
    except Exception:
        response={'ok':False,'code':'SPEECH_FAILED'}
    print(json.dumps(response,ensure_ascii=False),flush=True)
    return 0 if response.get('ok') else 1


if __name__=='__main__':
    raise SystemExit(main())
