"""Replay an unchanged, in-memory microphone sample for input diagnosis."""
from array import array
from threading import Event, Lock

import sounddevice as sd

from .audio import AudioError


class MicrophoneProbe:
    def __init__(self, backend=sd):
        self.backend=backend
        self.cancel=Event()
        self.lock=Lock()

    def arm(self):
        with self.lock:
            self.cancel.clear()

    def stop(self):
        with self.lock:
            self.cancel.set()
            try:
                self.backend.stop()
            except Exception:
                pass

    def play(self, recording):
        samples=array('h');samples.frombytes(recording.pcm)
        if not samples:
            raise AudioError('No se capturó audio para escuchar.')
        peak=max(abs(value) for value in samples)/32768
        clipped=sum(abs(value)>=32112 for value in samples)/len(samples)
        message=f'Prueba terminada. Pico de entrada: {peak:.0%}. '
        message+=('La entrada está saturando; bajá la ganancia del micrófono.' if clipped>=.01 else
                  'La entrada es muy baja; revisá el nivel del micrófono o Sonar.' if peak<.015 else
                  'Si te oís con claridad y se transcribe mal, revisaremos el reconocedor.')
        try:
            with self.lock:
                if self.cancel.is_set():
                    return 'Prueba detenida.'
                # No gain, filtering, resampling or saved audio: hear the input itself.
                self.backend.play(samples,samplerate=recording.sample_rate,blocking=False)
                stream=self.backend.get_stream()
            while stream.active and not self.cancel.wait(.02):
                pass
            return 'Prueba detenida.' if self.cancel.is_set() else message
        except Exception:
            raise AudioError('No se pudo reproducir la prueba. Revisá los parlantes de Windows.') from None
        finally:
            try:
                self.backend.stop()
            except Exception:
                pass
