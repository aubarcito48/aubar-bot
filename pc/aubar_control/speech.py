"""Asynchronous local Spanish TTS. Text is independent of avatar commands."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from threading import Lock


class SpeechError(Exception):
    """Actionable output error; callers can keep using the panel and USB."""


@dataclass(frozen=True)
class SpeechVoice:
    id: str
    name: str
    language: str


class SapiBackend:
    def __init__(self, process_factory=subprocess.Popen):
        self._factory = process_factory
        self._process = None
        self._lock = Lock()
        self._closed = False

    def _request(self, payload, timeout=30):
        if os.name != 'nt':
            raise SpeechError('La voz local de esta versión requiere Windows con SAPI.')
        helper = Path(__file__).with_name('sapi_speech.ps1')
        executable = Path(os.environ.get('SystemRoot', r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        try:
            with self._lock:
                if self._closed:
                    raise SpeechError('El motor de voz está cerrado.')
                process = self._factory(
                    [str(executable), '-NoLogo', '-NoProfile', '-NonInteractive',
                     '-ExecutionPolicy', 'Bypass', '-File', str(helper)],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW,
                )
                self._process = process
            stdout, _ = process.communicate(json.dumps(payload, ensure_ascii=False), timeout=timeout)
            with self._lock:
                if self._closed:
                    raise SpeechError('Se canceló la reproducción al cerrar el motor de voz.')
            try:
                response = json.loads(stdout)
            except (ValueError, TypeError) as exc:
                raise SpeechError('El motor de voz no devolvió una respuesta válida.') from exc
            if not isinstance(response, dict):
                raise SpeechError('El motor de voz devolvió una respuesta inválida.')
            if not response.get('ok'):
                if response.get('code')=='NO_SPANISH_VOICE':
                    raise SpeechError('No hay una voz SAPI en español disponible. Instalá una voz española compatible en Windows y probá nuevamente.')
                raise SpeechError('No se pudo reproducir la voz. Revisá la salida de audio y las voces de Windows.')
            if process.returncode != 0:
                raise SpeechError('El motor de voz terminó con un error.')
            return response
        except subprocess.TimeoutExpired as exc:
            try:
                process.kill()
            except OSError:
                pass
            process.communicate()
            raise SpeechError('La reproducción de voz excedió el tiempo de espera y se detuvo.') from exc
        except OSError as exc:
            raise SpeechError('No se pudo iniciar la voz local de Windows.') from exc
        finally:
            with self._lock:
                self._process = None

    def voices(self):
        response = self._request({'action':'voices'})
        try:
            voices = [SpeechVoice(**voice) for voice in response['voices']]
            if not voices or any(not voice.language.startswith('es') for voice in voices):
                raise ValueError('No Spanish voice')
            return voices
        except (KeyError, TypeError, ValueError) as exc:
            raise SpeechError('No se pudo consultar una voz española compatible.') from exc

    def speak(self, text, volume=100, rate=0):
        response = self._request(
            {'action':'speak','text':text,'volume':volume,'rate':rate},
            timeout=max(30, min(300, len(text)*.3+15)),
        )
        try:
            voice = SpeechVoice(**response['voice'])
            if not voice.language.startswith('es'):
                raise ValueError('Not Spanish')
            return voice
        except (KeyError, TypeError, ValueError) as exc:
            raise SpeechError('El motor no confirmó una voz española válida.') from exc

    def close(self):
        with self._lock:
            self._closed = True
            process = self._process
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass


class SpeechEngine:
    """Submit work from Tk; consume Future results without waiting in Tk."""
    MAX_TEXT_LENGTH = 2000

    def __init__(self, backend=None):
        self.backend = backend or SapiBackend()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='aubar-speech')
        self._lock = Lock()
        self._closed = False
        self._future = None

    @property
    def busy(self):
        with self._lock:
            return self._future is not None and not self._future.done()

    def _submit(self, operation):
        with self._lock:
            if self._closed:
                raise SpeechError('El motor de voz está cerrado.')
            if self._future is not None and not self._future.done():
                raise SpeechError('El motor de voz está ocupado. Esperá a que termine.')
            self._future = self._executor.submit(operation)
            return self._future

    def voices(self):
        return self._submit(self.backend.voices)

    def speak(self, text, *, volume=100, rate=0):
        if not isinstance(text, str) or not text.strip() or len(text)>self.MAX_TEXT_LENGTH or '\x00' in text:
            raise SpeechError('El texto de voz debe tener entre 1 y 2000 caracteres y no contener NUL.')
        if type(volume) is not int or not 0<=volume<=100 or type(rate) is not int or not -10<=rate<=10:
            raise SpeechError('El volumen debe estar entre 0 y 100 y la velocidad entre -10 y 10.')
        return self._submit(lambda:self.backend.speak(text,volume,rate))

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self.backend.close()
        finally:
            self._executor.shutdown(wait=False, cancel_futures=True)
