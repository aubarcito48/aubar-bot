"""Probe local Whisper on explicit WAVs; no microphone, network, Groq or actions."""
import argparse
import json
from pathlib import Path
import sys
import time
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files',nargs='+',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'tmp/whisper-probe/report.json')
    args=parser.parse_args()
    if not 1<=len(args.files)<=10: parser.error('Usa entre 1 y 10 WAVs.')
    from pc.aubar_control.audio import Recording
    from pc.aubar_control.whisper_recognition import WhisperRecognizer
    recognizer=WhisperRecognizer()
    started=time.perf_counter();recognizer.prepare();loaded=time.perf_counter()-started
    rows=[]
    for path in args.files:
        with wave.open(str(path),'rb') as audio:
            if audio.getsampwidth()!=2 or audio.getnchannels()!=1 or audio.getnframes()/audio.getframerate()>12:
                raise ValueError('Usá WAV mono PCM16 de hasta 12 segundos.')
            recording=Recording(audio.readframes(audio.getnframes()),audio.getframerate())
        started=time.perf_counter();result=recognizer.recognize(recording)
        rows.append({'file':path.name,'duration_s':round(recording.duration,3),
            'transcribe_s':round(time.perf_counter()-started,3),'text':result.text,
            'accepted':bool(result.query or result.action or result.youtube)})
    report=({'engine':'whisper','load_s':round(loaded,3),'clips':rows})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Informe local:',args.output)


if __name__=='__main__': main()
