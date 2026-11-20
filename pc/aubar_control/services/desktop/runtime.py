"""Coordinate existing services without a Tk/Qt dependency.

The UI calls tick() on its thread; workers only return values through Futures.
Serial operations share one worker. Revisions discard canceled/obsolete replies.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from queue import Empty
import time

from ...config.settings import load_groq_config
from ...device.session import DeviceSession, available_ports
from ...device.protocol import DeviceError
from ...integrations.youtube import match_youtube_command, open_youtube
from ...integrations.whatsapp import InboxPoller, is_open_web_command, open_whatsapp_web
from ...models.avatar.ai_avatar import normalize_reply
from ..assistant.conversation import Conversation
from ..assistant.groq_client import GroqService, GroqError
from ..audio.audio import MicrophoneCapture, AudioError, available_inputs
from ..audio.automatic_audio import AutomaticCapture
from ..recognition.whisper_recognition import WhisperRecognizer
from ..recognition.recognition import RecognitionError
from ..recognition.voice_commands import match_command, VoiceAction
from ..speech.speech import SpeechEngine, SpeechError


class DesktopRuntime:
    def __init__(self, *, session=None, ai=None, speech=None, recognizer=None,
                 capture=None, automatic=None, inbox=None, config_loader=load_groq_config):
        self.session = session or DeviceSession()
        self.ai = ai or GroqService()
        self.speech = speech or SpeechEngine()
        self.recognizer = recognizer or WhisperRecognizer()
        self.capture = capture or MicrophoneCapture()
        self.automatic = automatic or AutomaticCapture(self.capture.backend)
        self.inbox = inbox or InboxPoller()
        self.config_loader = config_loader
        self.conversation = Conversation()
        self.jobs = {}
        self.serial = ThreadPoolExecutor(max_workers=1, thread_name_prefix='aubar-device')
        self.audio = ThreadPoolExecutor(max_workers=1, thread_name_prefix='aubar-input')
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='aubar-desktop')
        self.events = []
        self.closed = False
        self.revision = 0
        self.voice = True
        self.volume = 80
        self.last_reply = None
        self.auto = False
        self.input_device = None
        self.recording = False
        self.finish_requested = False
        self.auto_ready = False
        self.auto_starting = False
        self.spoken_at = 0.0
        self.last_speaking = False
        self.last_lease = 0.0
        self.pending_visual = None
        self.performance_key = None
        self.youtube_cancel = Event()
        self.last_youtube_query = ''
        self.config = None
        self.reload()

    @property
    def busy(self):
        return any(k in self.jobs for k in ('reply', 'youtube', 'whatsapp_web', 'transcribe', 'record_start', 'record_finish')) or self.recording

    @property
    def connected(self):
        return self.session.connected

    def emit(self, kind, value):
        if not self.closed:
            self.events.append((kind, value))

    def _job(self, kind, pool, function, context=None):
        if kind in self.jobs or self.closed:
            return False
        self.jobs[kind] = (pool.submit(function), self.revision, context)
        return True

    def reload(self):
        if self.config is not None:
            self.cancel()
        state = self.config_loader()
        self.config = state.config
        self.inbox.configure(self.config)
        self.emit('config', state.message)
        return state

    def scan(self):
        self._job('ports', self.serial, available_ports)
        self._job('inputs', self.audio, available_inputs)

    def connect(self, port):
        self._job('connect', self.serial, lambda: self.session.connect(port))

    def disconnect(self):
        self.pending_visual = None
        self._job('disconnect', self.serial, self.session.close)

    def select(self, action):
        self.emit('visual', action)
        if self.connected:
            self.pending_visual = action

    def send(self, text):
        text = text.strip()
        if not text or len(text) > 1000 or '\x00' in text:
            self.emit('error', 'Escribí un mensaje de entre 1 y 1000 caracteres.')
            return False
        if self.busy:
            self.emit('error', 'Esperá la respuesta actual o cancelala antes de enviar otra.')
            return False
        self.stop_voice()
        self.automatic.pause()
        if is_open_web_command(text):
            self.emit('user', text)
            self.youtube_cancel = Event()
            cancel = self.youtube_cancel
            self._job('whatsapp_web', self.worker, lambda: open_whatsapp_web(cancel_event=cancel))
            self.last_youtube_query = ''
            self.emit('status', 'Abriendo WhatsApp Web…')
            return True
        action = match_command(text)
        youtube = match_youtube_command(text, previous_query=self.last_youtube_query)
        if action is not None:
            self.emit('user', text)
            self.select(action)
            self.emit('assistant', action.label)
            return True
        if youtube is not None:
            self.emit('user', text)
            self.youtube_cancel = Event()
            cancel = self.youtube_cancel
            self._job('youtube', self.worker, lambda: open_youtube(youtube, cancel_event=cancel), context=youtube)
            self.emit('status', 'Abriendo YouTube…')
            return True
        if self.config is None:
            self.emit('error', 'Configurá GROQ_API_KEY en .env y recargá la configuración.')
            return False
        try:
            request = self.conversation.prepare(text)
            future = self.ai.submit(self.config, request)
        except (ValueError, GroqError) as error:
            self.emit('error', str(error))
            return False
        self.jobs['reply'] = (future, self.revision, request)
        self.last_youtube_query = ''
        self.emit('user', text)
        self.select(VoiceAction('ANIMATION', 'thinking', 'Pensar'))
        self.emit('status', 'Preparando respuesta…')
        return True

    def speak(self, reply=None):
        reply = reply or self.last_reply
        if not reply:
            return
        try:
            self.select(reply.action)
            self.jobs['speech'] = (self.speech.speak(reply.text, volume=self.volume,
                performance=reply.segments or None), self.revision, None)
            self.emit('status', 'Preparando la voz…')
        except (SpeechError, ValueError) as error:
            self.emit('error', str(error))

    def stop_voice(self):
        self.speech.stop()
        self.emit('speaking', False)
        self.performance_key = None

    def cancel(self):
        self.revision += 1
        self.conversation.invalidate_pending()
        self.ai.cancel()
        self.youtube_cancel.set()
        self.capture.cancel()
        self.recording = False
        self.finish_requested = False
        self.stop_voice()
        self.emit('status', 'Operación cancelada.')
        self.select(VoiceAction('EXPRESSION', 'neutral', 'Neutral'))

    def reset(self):
        self.cancel()
        self.conversation.reset()
        self.last_reply = None
        self.last_youtube_query = ''
        self.emit('clear', None)

    def start_recording(self, device):
        if self.busy or self.auto or self.speech.busy or self.jobs.get('speech'):
            self.emit('error', 'Detené la voz o la escucha automática antes de grabar.')
            return
        self.input_device = device
        self.capture.arm()
        self.recording = True
        self.finish_requested = False
        self._job('record_start', self.audio, lambda: self.capture.start(device))
        self.emit('status', 'Abriendo micrófono…')

    def finish_recording(self):
        if not self.recording:
            return
        self.capture.cancel()
        self.finish_requested = True

    def set_auto(self, enabled, device=None):
        if enabled and (self.recording or self.busy):
            self.emit('error', 'Terminá la operación actual antes de activar la escucha.')
            return
        self.auto = bool(enabled)
        self.input_device = device
        if self.auto:
            self.automatic.arm()
            self.auto_starting = True
            self._job('auto_start', self.audio, lambda: self.automatic.start(device))
            self.emit('status', 'Preparando escucha automática…')
        else:
            self.automatic.cancel()
            self.auto_ready = False
            self._job('auto_finish', self.audio, self.automatic.finish)
            self.emit('status', 'Micrófono desactivado.')

    def _recognized(self, result):
        self.emit('recognized', result.text)
        if result.action:
            self.select(result.action)
            self.emit('assistant', result.action.label)
        elif result.query or result.youtube:
            self.send(result.query or result.text)
        else:
            self.emit('status', result.message)
            if result.text:
                self.emit('voice_rejected', (result.text, result.message))

    def _complete(self, kind, result, context):
        if kind == 'reply':
            reply = normalize_reply(result)
            if self.conversation.commit(context, reply.text):
                self.last_reply = reply
                self.emit('assistant', reply.text)
                self.select(reply.action)
                if self.voice:
                    self.speak(reply)
                else:
                    self.emit('status', 'Respuesta lista · Aubar Director local')
        elif kind in ('youtube', 'whatsapp_web'):
            message, confirmation = result
            if confirmation and context and context.query:
                self.last_youtube_query = context.query
            self.emit('assistant', message)
            if confirmation and self.voice:
                self.speak(normalize_reply(confirmation))
        elif kind == 'record_start':
            self.spoken_at = time.monotonic()
            self.emit('status', 'Escuchando · pulsá Terminar cuando hayas hablado.')
        elif kind == 'record_finish':
            self.recording = False
            self.finish_requested = False
            query = self.last_youtube_query
            self._job('transcribe', self.audio, lambda: self.recognizer.recognize(result, youtube_query=query))
            self.emit('status', 'Transcribiendo…')
        elif kind == 'transcribe':
            self._recognized(result)
        elif kind == 'auto_start':
            self.auto_ready = bool(result) and self.auto
            self.auto_starting = False
        elif kind in ('connect', 'visual'):
            self.emit('device', result)
        elif kind == 'disconnect':
            self.emit('device', None)
        elif kind in ('ports', 'inputs'):
            self.emit(kind, result)
        elif kind == 'speech':
            self.emit('status', 'Listo para conversar')

    def tick(self):
        if self.closed:
            return []
        for kind, (future, epoch, context) in list(self.jobs.items()):
            if not future.done():
                continue
            del self.jobs[kind]
            try:
                result = future.result()
                # Device lifecycle and microphone cleanup must finish across cancellation.
                if epoch == self.revision or kind in ('connect', 'disconnect', 'ports', 'inputs', 'auto_finish'):
                    self._complete(kind, result, context)
                elif kind in ('record_start', 'record_finish'):
                    self.capture.cancel()
                    self._job('capture_cleanup', self.audio, self.capture.finish)
            except Exception as error:
                if kind.startswith('record') or kind == 'transcribe':
                    self.capture.cancel()
                    self.recording = False
                    self.finish_requested = False
                    self._job('capture_cleanup', self.audio, self.capture.finish)
                if kind.startswith('auto'):
                    self.auto = self.auto_ready = self.auto_starting = False
                    self.automatic.cancel()
                if epoch == self.revision:
                    safe = str(error) if isinstance(error, (GroqError, SpeechError, DeviceError, AudioError, RecognitionError, ValueError)) else 'No se pudo completar la operación. Revisá la conexión y volvé a probar.'
                    if self.config:
                        safe = safe.replace(self.config.api_key, '[credencial oculta]')
                    self.emit('error', safe)
        if self.recording and 'record_start' not in self.jobs and 'record_finish' not in self.jobs:
            if self.finish_requested or self.capture.limit_reached:
                self._job('record_finish', self.audio, self.capture.finish)
        talking = bool(self.speech.articulating)
        self.emit('speaking', talking)
        if talking:
            self.spoken_at = time.monotonic()
        segment = self.speech.performance
        if segment:
            key = (segment['index'], segment['avatar_type'], segment['avatar_id'])
            if key != self.performance_key:
                self.performance_key = key
                self.select(VoiceAction('ANIMATION' if segment['avatar_type'] == 'animation' else 'EXPRESSION', segment['avatar_id'], segment['delivery']))
        if self.auto_ready:
            if self.busy or self.speech.busy or time.monotonic()-self.spoken_at < .5:
                self.automatic.pause()
            else:
                self.automatic.resume()
                try:
                    recording = self.automatic.utterances.get_nowait()
                except Empty:
                    recording = None
                if recording is not None:
                    self.automatic.pause()
                    if isinstance(recording, Exception):
                        self.emit('error', str(recording))
                    else:
                        query = self.last_youtube_query
                        self._job('transcribe', self.audio, lambda: self.recognizer.recognize_automatic(recording, youtube_query=query))
        serial_busy = any(k in self.jobs for k in ('connect', 'disconnect', 'visual', 'lease', 'ports'))
        if self.connected and not serial_busy:
            if self.pending_visual is not None:
                action, self.pending_visual = self.pending_visual, None
                self._job('visual', self.serial, lambda: self.session.apply_action(action))
            elif talking != self.last_speaking or talking and time.monotonic()-self.last_lease > .7:
                self.last_speaking, self.last_lease = talking, time.monotonic()
                self._job('lease', self.serial, lambda: self.session.set_speaking(talking))
        notices = self.inbox.tick()
        if notices:
            status, events, missed = notices
            self.emit('whatsapp', (status, events, missed))
        events, self.events = self.events, []
        return events

    def close(self):
        if self.closed:
            return
        self.cancel()
        self.closed = True
        self.auto = False
        self.capture.cancel()
        self.automatic.cancel()
        self.inbox.close()
        self.ai.close()
        self.speech.close()
        self.serial.submit(self.session.close)
        self.audio.submit(self.capture.finish)
        self.audio.submit(self.automatic.finish)
        for executor in (self.serial, self.audio, self.worker):
            executor.shutdown(wait=False, cancel_futures=False)
