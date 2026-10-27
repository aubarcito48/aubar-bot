"""Bounded, local PCM capture. No stream is opened during device enumeration."""
from array import array
from dataclasses import dataclass
from threading import Event

import sounddevice as sd


class AudioError(Exception):
    pass


@dataclass(frozen=True)
class InputDevice:
    index: int
    name: str
    host: str
    is_default: bool = False

    @property
    def label(self):
        return f"{self.name} — {self.host} [{self.index}]"


@dataclass(frozen=True)
class Recording:
    pcm: bytes
    sample_rate: int

    @property
    def duration(self):
        return len(self.pcm) / (2 * self.sample_rate)


def available_inputs(backend=sd):
    try:
        hosts = backend.query_hostapis()
        default = backend.default.device[0]
        return [InputDevice(i, device['name'], hosts[device['hostapi']]['name'], i == default)
                for i, device in enumerate(backend.query_devices()) if device['max_input_channels'] > 0]
    except Exception as exc:
        raise AudioError("No se pudieron buscar micrófonos. Revisá la configuración de sonido de Windows.") from exc


class MicrophoneCapture:
    MAX_SECONDS = 10

    def __init__(self, backend=sd):
        self.backend = backend
        self.requested = Event()
        self.finished = Event()
        self.stream = None
        self.chunks = []
        self.frames = 0
        self.sample_rate = 16000
        self.level = 0.0
        self.limit_reached = False
        self.overflow = False

    @property
    def duration(self):
        return self.frames / self.sample_rate

    def arm(self):
        # Called from the UI before scheduling start, so an early release can
        # cancel a pending start without re-enabling capture in the worker.
        if self.stream is not None:
            raise AudioError("El micrófono todavía se está cerrando.")
        self.chunks = []
        self.frames = 0
        self.level = 0.0
        self.limit_reached = False
        self.overflow = False
        self.finished.clear()
        self.requested.set()

    def cancel(self):
        self.requested.clear()  # Callback rejects data immediately after release.

    def _callback(self, data, frames, timing, status):
        if not self.requested.is_set():
            return
        if status:
            self.overflow = True
        remaining = int(self.sample_rate*self.MAX_SECONDS) - self.frames
        chunk = bytes(data[:max(0, min(frames, remaining))*2])
        if chunk:
            self.chunks.append(chunk)
            self.frames += len(chunk)//2
            samples = array('h')
            samples.frombytes(chunk)
            self.level = min(1.0, max(abs(value) for value in samples)/32768)
        if self.frames >= self.sample_rate*self.MAX_SECONDS:
            self.limit_reached = True
            self.cancel()

    def start(self, device):
        if not self.requested.is_set():
            return False
        try:
            info = self.backend.query_devices(device, 'input')
            rate = 16000
            try:
                self.backend.check_input_settings(device=device, channels=1, dtype='int16', samplerate=rate)
            except Exception:
                rate = int(info['default_samplerate'])
                self.backend.check_input_settings(device=device, channels=1, dtype='int16', samplerate=rate)
            self.sample_rate = rate
            if not self.requested.is_set():
                return False
            self.stream = self.backend.RawInputStream(
                device=device, samplerate=rate, channels=1, dtype='int16',
                callback=self._callback, finished_callback=self.finished.set,
            )
            if not self.requested.is_set():
                self.stream.close()
                self.stream = None
                return False
            self.stream.start()
            return True
        except Exception as exc:
            self.cancel()
            self._close_stream()
            raise AudioError("No se pudo abrir el micrófono. Revisá los permisos de micrófono y el dispositivo elegido.") from exc

    def _close_stream(self):
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.abort()
            finally:
                stream.close()

    def finish(self):
        self.cancel()
        try:
            self._close_stream()
            return Recording(b''.join(self.chunks), self.sample_rate)
        except Exception as exc:
            raise AudioError("No se pudo cerrar la captura. Volvé a buscar los micrófonos.") from exc
        finally:
            self.chunks = []
            self.level = 0.0
