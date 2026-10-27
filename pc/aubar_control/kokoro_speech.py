"""One hidden worker per request: local synthesis/playback, killed on stop.

Only JSON is written to stdout. No network, shell commands or audio files.
"""
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pc.aubar_control.tts_assets import ASSETS, MODEL_DIR, VOICE


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
        from kokoro_onnx import Kokoro
        import sounddevice as sd
    except ImportError:
        return {'ok':False,'code':'DEPENDENCY_MISSING'}
    # Model/tokenizer libraries may log; stdout must remain a single JSON result.
    with redirect_stdout(sys.stderr):
        engine=Kokoro(str(MODEL_DIR/ASSETS[0][0]),str(MODEL_DIR/ASSETS[1][0]))
        samples,sample_rate=engine.create(text,voice=VOICE['id'],
            speed=max(.5,min(2.0,.95*2**(rate/10))),lang='es')
        try:
            sd.play(samples*(volume/100),sample_rate)
            sd.wait()
        finally:
            sd.stop()
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
