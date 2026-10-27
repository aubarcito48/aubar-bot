import threading
import tkinter as tk
import unittest
from unittest.mock import Mock

import test_app
from audio_fakes import FakeAudio, FakeSpeechEngine
from pc.aubar_control.app import AubarApp
from pc.aubar_control.audio import MicrophoneCapture, InputDevice
from pc.aubar_control.config import load_groq_config
from pc.aubar_control.recognition import LocalRecognizer, RecognitionError


class PreparationTests(unittest.TestCase):
    pump=test_app.AppTests.pump

    def setUp(self):
        self.root=tk.Tk();self.root.withdraw()
        self.release=threading.Event();self.started=threading.Event()
        self.error=None;self.audio=FakeAudio()
        self.recognizer=LocalRecognizer()
        def prepare():
            self.started.set();self.release.wait(3)
            if self.error:raise self.error
        self.recognizer.prepare=Mock(side_effect=prepare)
        self.app=AubarApp(self.root,session=test_app.FakeSession(),port_provider=lambda:[],
            capture=MicrophoneCapture(self.audio),audio_provider=lambda:[InputDevice(1,'Mic','Test',True)],
            recognizer=self.recognizer,speech=FakeSpeechEngine(),
            config_loader=lambda:load_groq_config(None,environ={}))
        self.pump(self.started.is_set)

    def tearDown(self):
        self.release.set();self.app.close()

    def test_preparation_keeps_ui_responsive_and_never_opens_capture_before_ready(self):
        self.assertFalse(self.app.recognition_ready)
        self.assertEqual(str(self.app.talk_button.cget('state')),'disabled')
        self.app.start_recording();self.app.test_microphone()
        self.assertEqual(self.audio.streams,[])
        self.assertEqual(self.app.audio_phase,'idle')
        self.release.set();self.pump(lambda:self.app.recognition_ready)
        self.assertEqual(str(self.app.talk_button.cget('state')),'normal')
        self.recognizer.prepare.assert_called_once()

    def test_preparation_error_does_not_enable_capture_or_leave_pending_commands(self):
        self.error=RecognitionError('No se pudo preparar el modelo.')
        self.release.set()
        self.pump(lambda:'No se pudo preparar' in self.app.recognition_message.get())
        self.assertFalse(self.app.recognition_ready)
        self.assertEqual(str(self.app.talk_button.cget('state')),'disabled')
        self.assertEqual(self.audio.streams,[])
        self.assertIsNone(self.app.pending_action)
