"""Local Whisper CPU decoder with the existing command/query contract."""
from array import array
import hashlib
import math

from .recognition import RecognitionError,RecognitionResult
from .voice_commands import match_command,normalize, normalize
from ...integrations.youtube import match_youtube_command
from ...integrations.whatsapp import parse_send,WhatsAppError
from .whisper_assets import MODEL_DIR,ASSETS


class WhisperRecognizer:
    label='Whisper small · español · CPU local'

    def __init__(self,*,backend=None,model_path=MODEL_DIR):
        self.backend=backend
        self.model_path=model_path
        self.model=None

    def prepare(self):
        if self.model is not None: return
        if self.backend is None:
            for name,size,checksum in ASSETS:
                path=self.model_path/name
                if not path.is_file() or path.stat().st_size!=size:
                    raise RecognitionError('Falta Whisper local. Cerrá el panel y usá tools/start_control.ps1.')
                with path.open('rb') as stream:
                    if hashlib.file_digest(stream,'sha256').hexdigest()!=checksum:
                        raise RecognitionError('Los archivos de Whisper no coinciden con el modelo verificado.')
            try:
                from faster_whisper import WhisperModel
                self.backend=WhisperModel
            except ImportError:
                raise RecognitionError('Faltan las dependencias de Whisper. Abrí el panel con start_control.ps1.') from None
        try:
            self.model=self.backend(str(self.model_path),device='cpu',compute_type='int8',
                cpu_threads=4,num_workers=1,local_files_only=True)
        except Exception:
            raise RecognitionError('No se pudo preparar Whisper local. Revisá la instalación del modelo.') from None

    @staticmethod
    def _samples(recording):
        import numpy as np
        samples=np.frombuffer(recording.pcm,dtype='<i2')
        if recording.sample_rate==16000:
            return samples.astype(np.float32)/32768
        # PyAV/FFmpeg's resampler filters before downsampling; interpolation
        # alone would alias high-frequency microphone noise into speech bands.
        import av
        frame=av.AudioFrame.from_ndarray(samples.reshape(1,-1),format='s16',layout='mono')
        frame.sample_rate=recording.sample_rate
        resampler=av.AudioResampler(format='fltp',layout='mono',rate=16000)
        frames=resampler.resample(frame)+resampler.resample(None)
        return np.concatenate([part.to_ndarray().reshape(-1) for part in frames])

    def recognize_automatic(self,recording):
        return self.recognize(recording,automatic=True)

    def recognize(self,recording,*,automatic=False):
        if (not recording.pcm or len(recording.pcm)%2 or type(recording.sample_rate) is not int
            or not 8000<=recording.sample_rate<=192000 or recording.duration>12):
            raise RecognitionError('La captura no tiene un formato de audio válido.')
        samples=array('h');samples.frombytes(recording.pcm)
        if max(abs(value) for value in samples)<150:
            return RecognitionResult('',None,'No se detectó voz. Revisá el micrófono y hablá de nuevo.')
        self.prepare()
        try:
            segments,_=self.model.transcribe(self._samples(recording),language='es',task='transcribe',
                beam_size=5,temperature=0,condition_on_previous_text=False,
                word_timestamps=True,vad_filter=True,vad_parameters={'min_silence_duration_ms':300})
            segments=list(segments)
            if len(segments)>64: raise ValueError
            text=' '.join(segment.text.strip() for segment in segments).strip()
            if not text:
                return RecognitionResult('',None,'No se entendió la voz. Repetí la frase.')
            if len(text)>1000 or '\x00' in text:
                return RecognitionResult('',None,'La consulta es demasiado larga. Probá una frase más breve.')
            probabilities=[word.probability for segment in segments for word in (segment.words or [])]
            valid=bool(probabilities) and all(math.isfinite(p) and 0<=p<=1 for p in probabilities)
            valid=valid and all(math.isfinite(segment.avg_logprob) and segment.avg_logprob>=-1
                and math.isfinite(segment.no_speech_prob) and segment.no_speech_prob<=.6
                and math.isfinite(segment.compression_ratio) and segment.compression_ratio<=2.4
                for segment in segments)
            if not valid or min(probabilities)<.2 or sum(probabilities)/len(probabilities)<.55:
                return RecognitionResult(text,None,'La voz no se reconoció con claridad. Repetí la frase.')
            if normalize(text) in ('aubar','au bar','a un bar'):
                return RecognitionResult(text,None,'Decí un comando o una pregunta, no solamente el nombre.')
            action=match_command(text)
            youtube=match_youtube_command(text)
            try: sending=parse_send(text) is not None
            except WhatsAppError: sending=False
            # Keep conservative gates for actions, especially external sends.
            if action is not None or youtube is not None or sending:
                if min(probabilities)<.6 or sum(probabilities)/len(probabilities)<.8:
                    return RecognitionResult(text,None,'La voz no se reconoció con claridad. Repetí la orden.')
            if action is not None:
                return RecognitionResult(text,action,action.label)
            if youtube is not None:
                return RecognitionResult(text,None,'Comando de YouTube reconocido.',youtube=youtube)
            return RecognitionResult(text,None,'Consulta reconocida con Whisper local.',query=text)
        except RecognitionError:
            raise
        except Exception:
            raise RecognitionError('No se pudo transcribir con Whisper local. Repetí la frase.') from None
