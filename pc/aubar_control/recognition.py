"""Offline Spanish transcription, verified activation, and command/query routing."""
from array import array
from dataclasses import dataclass
import json
import math
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
    query: str | None = None


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
        if action is not None:
            return RecognitionResult(text,action,action.label)
        activated=self._automatic_result(recording,text,words)
        if activated.query is not None:
            return activated
        # Holding the manual button is explicit activation. A missed proper
        # name must not reject an otherwise clear question in push-to-talk.
        # Keep the full transcript if the name cannot be verified; no aliases.
        if normalize(text) in ('aubar','au bar','a un bar'):
            return activated
        if (any(not math.isfinite(value) or not 0<=value<=1 for value in confidences)
            or min(confidences)<.35 or sum(confidences)/len(confidences)<.55):
            return RecognitionResult(text,None,'La voz no se reconoció con claridad. Repetí la frase.')
        if len(text)>1000:
            return RecognitionResult(text,None,'La consulta es demasiado larga. Probá una frase más breve.')
        return RecognitionResult(text,None,'Consulta reconocida. Todavía no se envía a Groq.',query=text)

    def _automatic_result(self, recording, text, words):
        rejected = RecognitionResult(text, None,
            'Sin acción ni consulta. Decí «Aubar» seguido de un comando o una pregunta.')
        # Both commands and queries must come from unrestricted transcription.
        # The focused decoder verifies only the activation sound and its boundary.
        tokens = text.split()
        if len(words)!=len(tokens) or normalize(text) in ('aubar','au bar','a un bar'):
            return rejected
        for first in range(min(4,len(tokens))):
            suffix = ' '.join(tokens[first:])
            if normalize(tokens[first]) in ('aubar','kirby'):
                if first==0:
                    continue
                return rejected
            if normalize(' '.join(tokens[:first]))=='aubar':
                wake = all(float(word.get('conf',0))>=.6 for word in words[:first])
            else:
                start = float(words[first].get('start',0))
                wake_end=float(words[first-1].get('end',start)) if first else None
                # Unrestricted ASR may omit the name entirely. It may only be
                # recovered from verified sound before the first transcribed word.
                wake = self._detect_aubar(recording,start,wake_end,allow_pause=first==0) if .15<=start<=2.2 else False
            if wake:
                action=match_command(suffix)
                confidence=[float(word.get('conf',0)) for word in words[first:]]
                floor=.55 if action is not None else .35
                if (any(not math.isfinite(value) or not 0<=value<=1 for value in confidence)
                    or min(confidence)<floor or sum(confidence)/len(confidence)<(.65 if action is not None else .55)):
                    return RecognitionResult(text,None,'La voz no se reconoció con claridad. Repetí la frase.')
                if action is not None:
                    return RecognitionResult(text,action,action.label)
                if len(suffix)>1000:
                    return RecognitionResult(text,None,'La consulta es demasiado larga. Probá una frase más breve.')
                return RecognitionResult(text,None,'Consulta reconocida. Todavía no se envía a Groq.',query=suffix)
        return rejected

    def _detect_aubar(self, recording, command_start, wake_end=None, allow_pause=False):
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
        if names[:2]!=['au','bar'] or any(name!='[unk]' for name in names[2:]):
            return False
        au, bar = words[:2]
        if min(float(au.get('conf',0)),float(bar.get('conf',0)))<.75:
            return False
        start, end = float(au.get('start',0)), float(bar.get('end',0))
        # Match the end of the transcribed prefix, not the next word's start:
        # a natural pause after the name must not discard or swallow query words.
        boundary=command_start if wake_end is None else wake_end
        aligned=abs(end-boundary)<=.15 or (allow_pause and wake_end is None)
        if not (start<=.6 and .15<=end-start<=1.5 and aligned
                and -.15<=command_start-end<=.6):
            return False
        if float(bar.get('start',0))-float(au.get('end',0))>.15:
            return False
        # Boundary frames can be emitted as one or several unknown pieces.
        # Admit at most 100 ms total, right at the start of the command.
        tail=words[2:]
        return not tail or (
            sum(float(word.get('end',0))-float(word.get('start',0)) for word in tail)<=.10
            and float(tail[0].get('start',0))>=end-.02
            and float(tail[-1].get('end',0))<=command_start+.06)
