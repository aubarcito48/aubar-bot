"""Offline, unrestricted Spanish transcription followed by exact intent matching."""
from array import array
from dataclasses import dataclass
import json
from pathlib import Path

from .voice_commands import VoiceAction, match_command

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

    def recognize(self, recording):
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
        confidences = [float(word.get('conf', 0)) for word in words]
        if not confidences or min(confidences) < 0.35 or sum(confidences)/len(confidences) < 0.45:
            return RecognitionResult(text, None, 'La voz no se reconoció con claridad. Repetí el comando.')
        action = match_command(text)
        return RecognitionResult(text, action, action.label if action else 'Frase no reconocida como comando.')
