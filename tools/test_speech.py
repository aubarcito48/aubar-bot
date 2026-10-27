"""Audible TK21 check. Does not open the microphone or require the ESP32."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pc.aubar_control.speech import SpeechEngine, SpeechError, SapiBackend


def main():
    parser=argparse.ArgumentParser(description='Probar la voz local en español de Aubar.')
    parser.add_argument('--list-voices',action='store_true')
    parser.add_argument('--engine',choices=('kokoro','sapi'),default='kokoro')
    parser.add_argument('--text',default='Hola, soy Aubar. Esta es mi voz en español.')
    args=parser.parse_args()
    engine=SpeechEngine(SapiBackend()) if args.engine=='sapi' else SpeechEngine()
    try:
        if args.list_voices:
            for voice in engine.voices().result():
                print(f'{voice.name} ({voice.language})')
        else:
            voice=engine.speak(args.text).result()
            print(f'Reproducción finalizada: {voice.name} ({voice.language}).')
        return 0
    except SpeechError as error:
        print(str(error),file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    finally:
        engine.close()


if __name__=='__main__':
    raise SystemExit(main())
