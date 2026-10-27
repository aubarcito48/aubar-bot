"""Local voice segmentation with pre-roll, silence endpoint and bounded memory."""
from array import array
from collections import deque
from math import sqrt
from queue import Queue, Empty
from threading import Event, Lock

from .audio import AudioError, MicrophoneCapture, Recording


class SpeechSegmenter:
    FRAME_MS = 20
    PRE_ROLL = 15
    START_FRAMES = 3
    END_FRAMES = 40
    MIN_VOICE_FRAMES = 9
    MAX_FRAMES = 500

    def __init__(self, rate, noise=60.0, calibrate=False):
        self.rate = rate
        self.frame_bytes = int(rate*self.FRAME_MS/1000)*2
        self.noise = noise
        self.calibration_left = 20 if calibrate else 0
        self.calibration_total = 0.0
        self.reset()

    def reset(self):
        self.pending = bytearray()
        self.pre_roll = deque(maxlen=self.PRE_ROLL)
        self.chunks = []
        self.onset = self.silence = self.voiced = 0
        self.active = False
        self.level = 0.0

    def feed(self, pcm):
        self.pending.extend(pcm)
        while len(self.pending) >= self.frame_bytes:
            frame = bytes(self.pending[:self.frame_bytes])
            del self.pending[:self.frame_bytes]
            samples = array('h')
            samples.frombytes(frame)
            rms = sqrt(sum(value*value for value in samples)/len(samples))
            self.level = min(1.0, rms/6000)
            if self.calibration_left:
                self.calibration_total += rms
                self.calibration_left -= 1
                if not self.calibration_left:
                    self.noise = max(20, self.calibration_total/20)
                continue
            voice = rms >= max(250, self.noise*3.5)
            if not self.active:
                self.pre_roll.append(frame)
                if not voice:
                    self.noise = .96*self.noise+.04*rms
                self.onset = self.onset+1 if voice else 0
                if self.onset >= self.START_FRAMES:
                    self.active = True
                    self.chunks = list(self.pre_roll)
                    self.voiced = self.onset
                continue
            self.chunks.append(frame)
            self.voiced += int(voice)
            self.silence = 0 if voice else self.silence+1
            if len(self.chunks) >= self.MAX_FRAMES:
                self.reset()
                return AudioError('Frase demasiado larga o ruido continuo. Esperá una pausa y repetí «Aubar» y el comando.')
            if self.silence >= self.END_FRAMES:
                recording = Recording(b''.join(self.chunks), self.rate)
                enough_voice = self.voiced >= self.MIN_VOICE_FRAMES
                self.reset()
                if enough_voice:
                    return recording
        return None


class AutomaticCapture(MicrophoneCapture):
    def __init__(self, backend=None):
        if backend is None:
            super().__init__()
        else:
            super().__init__(backend)
        self.listening = Event()
        self.lock = Lock()
        self.utterances = Queue(maxsize=1)
        self.detector = None
        self.speaking = False
        self.noise = 60.0
        self.needs_calibration = True
        self.calibrating = False

    def arm(self):
        super().arm()
        self.pause()
        self.needs_calibration = True
        self.noise = 60.0
        while True:
            try:
                self.utterances.get_nowait()
            except Empty:
                break

    def resume(self):
        with self.lock:
            if not self.requested.is_set() or self.listening.is_set():
                return
            self.detector = SpeechSegmenter(self.sample_rate,self.noise,self.needs_calibration)
            self.calibrating = self.needs_calibration
            self.needs_calibration = False
            self.speaking = False
            self.listening.set()

    def pause(self):
        self.listening.clear()
        with self.lock:
            self.detector = None
            self.speaking = False
            self.level = 0
            self.calibrating = False

    def cancel(self):
        super().cancel()
        self.listening.clear()

    def _callback(self, data, frames, timing, status):
        if not self.requested.is_set():
            return
        self.ready.set()
        with self.lock:
            if not self.listening.is_set() or self.detector is None:
                return
            result = AudioError('Se perdieron muestras del micrófono. Revisá la entrada y activá la escucha de nuevo.') if status else self.detector.feed(bytes(data))
            self.level = self.detector.level
            self.speaking = self.detector.active
            self.calibrating = bool(self.detector.calibration_left)
            self.noise = self.detector.noise
            if result is not None:
                self.listening.clear()
                self.speaking = False
                self.utterances.put_nowait(result)
