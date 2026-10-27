"""Offline, unrestricted Spanish transcription followed by exact intent matching."""
from array import array
from dataclasses import dataclass
import json
from pathlib import Path

from .voice_commands import VoiceAction, match_command, normalize

MODEL_PATH = Path(__file__).resolve().parents[2] / 'models/vosk-model-small-es-0.42'


class RecognitionError(Exception):
    pass


@dataclass(frozen=True)
class RecognitionResult:
    text: str
    action: VoiceAction | None
    message: str


class LocalRecognizer:
    def __init__(self, model_path=MODEL_PATH, backend=None):
        self.model_path = Path(model_path)
        self.backend = backend
        self.model = None

    def recognize_automatic(self, recording):
        return self.recognize(recording, require_wake=True)

    def recognize(self, recording, require_wake=False):
        if not recording.pcm or len(recording.pcm) % 2 or recording.sample_rate <= 0:
            raise RecognitionError('La captura no tiene un formato de audio válido.')
        samples = array('h')
        samples.frombytes(recording.pcm)
        if max(abs(value) for value in samples) < 150:
            return RecognitionResult('', None, 'No se detectó voz. Revisá el micrófono y hablá de nuevo.')
        if self.backend is None:
            if not (self.model_path / 'am/final.mdl').is_file():
                raise RecognitionError('Falta el modelo de español. Cerrá el panel y abrilo con start_control.ps1.')
            import vosk
            self.backend = vosk
            self.backend.SetLogLevel(-1)
        try:
            if self.model is None:
                self.model = self.backend.Model(str(self.model_path))
            decoder = self.backend.KaldiRecognizer(self.model, recording.sample_rate)
            decoder.SetWords(True)
            parts = []
            for offset in range(0, len(recording.pcm), 8000):
                if decoder.AcceptWaveform(recording.pcm[offset:offset+8000]):
                    parts.append(json.loads(decoder.Result()))
            parts.append(json.loads(decoder.FinalResult()))
        except Exception as exc:
            raise RecognitionError('No se pudo reconocer la captura. Revisá el micrófono y repetí la frase.') from exc
        text = ' '.join(part.get('text', '').strip() for part in parts).strip()
        words = [word for part in parts for word in part.get('result', [])]
        if not text:
            return RecognitionResult('', None, 'No se entendió la voz. Acercate al micrófono y repetí la frase.')
        if require_wake:
            return self._automatic_result(recording, text, words)
        confidences = [float(word.get('conf', 0)) for word in words]
        if not confidences or min(confidences) < 0.35 or sum(confidences)/len(confidences) < 0.45:
            return RecognitionResult(text, None, 'La voz no se reconoció con claridad. Repetí el comando.')
        action = match_command(text)
        return RecognitionResult(text, action, action.label if action else 'Frase no reconocida como comando.')

    def _automatic_result(self, recording, text, words):
        rejected = RecognitionResult(text, None, 'Sin acción. Decí «Aubar» seguido de un comando, por ejemplo «Aubar, contento».')
        # The command must be present in unrestricted transcription. A focused
        # wake decoder is never allowed to invent the command from arbitrary audio.
        tokens = text.split()
        if len(words)!=len(tokens):
            return rejected
        for first in range(1, min(4,len(tokens))):
            suffix = ' '.join(tokens[first:])
            if normalize(tokens[first]) in ('aubar','kirby'):
                continue
            action = match_command(suffix)
            if action is None:
                continue
            confidence = [float(word.get('conf',0)) for word in words[first:]]
            if min(confidence)<.55 or sum(confidence)/len(confidence)<.65:
                continue
            if normalize(' '.join(tokens[:first]))=='aubar':
                wake = all(float(word.get('conf',0))>=.6 for word in words[:first])
            else:
                start = float(words[first].get('start',0))
                wake = self._detect_aubar(recording, start) if .15<=start<=2.2 else False
            if wake:
                return RecognitionResult(text, action, action.label)
        return rejected

    def _detect_aubar(self, recording, command_start):
        # "Aubar" is absent from the shipped Spanish dictionary. Its spoken
        # sounds can be decoded as the existing tokens "au bar". Keep [unk]
        # available, require both tokens and reject any other leading speech.
        # See https://alphacephei.com/vosk/adaptation (runtime vocabulary).
        decoder = self.backend.KaldiRecognizer(
            self.model, recording.sample_rate, json.dumps(['au bar','[unk]']))
        decoder.SetWords(True)
        end = int((command_start+.04)*recording.sample_rate)*2
        decoder.AcceptWaveform(recording.pcm[:end])
        result = json.loads(decoder.FinalResult())
        words = result.get('result',[])
        names = [word.get('word') for word in words]
        if names not in (['au','bar'],['au','bar','[unk]']):
            return False
        au, bar = words[:2]
        if min(float(au.get('conf',0)),float(bar.get('conf',0)))<.75:
            return False
        start, end = float(au.get('start',0)), float(bar.get('end',0))
        if not (start<=.6 and .15<=end-start<=1.5 and abs(end-command_start)<=.15):
            return False
        if float(bar.get('start',0))-float(au.get('end',0))>.15:
            return False
        return len(words)==2 or float(words[2].get('end',0))-float(words[2].get('start',0))<=.10
