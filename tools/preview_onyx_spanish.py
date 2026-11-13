"""Render short ES/EN Onyx samples locally using one CPU thread."""
import argparse
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pc.aubar_control.tts_assets import MODEL_DIR, ASSETS, VOICE
from pc.aubar_control.speech_pronunciation import pronunciation_language, speech_speed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--play', action='store_true')
    args = parser.parse_args()
    import numpy as np
    import onnxruntime as ort
    from kokoro_onnx import Kokoro

    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session = ort.InferenceSession(str(MODEL_DIR / ASSETS[0][0]),
        sess_options=options, providers=['CPUExecutionProvider'])
    engine = Kokoro.from_session(session, str(MODEL_DIR / ASSETS[1][0]))
    output = ROOT / 'tmp/voice-preview'
    output.mkdir(parents=True, exist_ok=True)
    for name, text in [
        ('onyx-es-adaptado.wav', '¡Hola, Nahuel! ¿Cómo andás? Soy Aubar. Decime qué necesitás y lo vemos juntos.'),
        ('onyx-en-adaptado.wav', "Hi, Nahuel! I'm Aubar. Tell me what you need, and let's get started."),
    ]:
        language = pronunciation_language(text)
        print(f'Generating {name}: {language}, speed={speech_speed(0)}', flush=True)
        audio, rate = engine.create(text, voice=VOICE['id'], lang=language, speed=speech_speed(0))
        assert len(audio) and np.isfinite(audio).all(), 'Invalid audio'
        pcm = (np.clip(audio, -1, 1) * 32767).astype('<i2')
        path = output / name
        with wave.open(str(path), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(rate)
            stream.writeframes(pcm.tobytes())
        print(f'Saved {path} ({len(audio)/rate:.1f}s)', flush=True)
        if args.play:
            import sounddevice as sd
            try:
                sd.play(audio * .8, rate)
                sd.wait()
            finally:
                sd.stop()


if __name__ == '__main__':
    main()
