import threading
import unittest

import test_app
from test_speech import FakeSpeechBackend, FakeProcess
from pc.aubar_control.speech import SpeechEngine, SapiBackend


class SpeechControlTests(unittest.TestCase):
    pump=test_app.AppTests.pump

    def setUp(self):
        test_app.AppTests.setUp(self)
        self.app.speech.close()
        self.backend=FakeSpeechBackend()
        self.app.speech=SpeechEngine(self.backend)

    def tearDown(self):
        self.backend.release.set()
        test_app.AppTests.tearDown(self)

    def test_test_button_passes_volume_and_text_and_keeps_usb_responsive(self):
        self.app.speech_volume.set(42)
        self.app._speech_volume_changed()
        self.assertEqual(self.app.speech_volume_label.get(),'42 %')
        self.app.speech_text.delete('1.0','end')
        self.app.speech_text.insert('1.0','Prueba del panel.')
        self.app.test_speech()
        self.assertTrue(self.backend.started.wait(1))
        self.assertEqual(self.backend.calls,[('Prueba del panel.',42,0)])
        self.assertIn('Hablando',self.app.speech_message.get())
        self.assertEqual(str(self.app.speech_test_button.cget('state')),'disabled')
        self.assertEqual(str(self.app.speech_stop_button.cget('state')),'normal')
        self.app.test_speech()
        self.assertEqual(len(self.backend.calls),1)
        self.assertFalse(self.app.speak_text('Una respuesta futura tampoco debe sonar.'))
        self.assertEqual(len(self.backend.calls),1)
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)
        self.app.refresh_status()
        self.pump(lambda:not self.app.busy)
        self.app.start_recording()
        self.assertEqual(self.audio.streams,[])
        self.backend.release.set()
        self.pump(lambda:self.app._speech_future is None)
        self.assertIn('finalizada',self.app.speech_message.get())
        self.assertIn('es-MX',self.app.speech_voice.get())

    def test_stop_restores_controls_and_allows_another_test(self):
        self.app.test_speech()
        self.assertTrue(self.backend.started.wait(1))
        self.app.stop_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.assertIn('detenida',self.app.speech_message.get())
        self.assertFalse(self.backend.closed)
        self.assertEqual(str(self.app.speech_test_button.cget('state')),'normal')
        self.app.test_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.assertEqual(len(self.backend.calls),2)
        self.assertIn('finalizada',self.app.speech_message.get())

    def test_disabling_voice_stops_output_and_no_new_test_starts_until_enabled(self):
        self.app.test_speech()
        self.assertTrue(self.backend.started.wait(1))
        self.app.speech_enabled.set(False)
        self.app.toggle_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.assertEqual(self.app.speech_message.get(),'Voz desactivada.')
        self.assertEqual(str(self.app.speech_volume_scale.cget('state')),'disabled')
        self.app.test_speech()
        self.assertEqual(len(self.backend.calls),1)
        self.app.speech_enabled.set(True)
        self.app.toggle_speech()
        self.app.test_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.assertEqual(len(self.backend.calls),2)

    def test_empty_text_shows_error_without_starting_audio(self):
        self.app.speech_text.delete('1.0','end')
        self.app.test_speech()
        self.assertEqual(self.backend.calls,[])
        self.assertIn('texto',self.app.speech_message.get())
        self.assertEqual(str(self.app.speech_test_button.cget('state')),'normal')

    def test_missing_spanish_voice_reports_error_without_disconnect_and_can_retry(self):
        self.app.speech.close()
        processes=iter((
            FakeProcess({'ok':False,'code':'NO_SPANISH_VOICE'},returncode=1),
            FakeProcess(),
        ))
        self.app.speech=SpeechEngine(SapiBackend(lambda *args,**kwargs:next(processes)))
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)
        self.app.test_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.assertIn('español',self.app.speech_message.get())
        self.assertTrue(self.app.connected)
        self.app.test_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.assertIn('finalizada',self.app.speech_message.get())

    def test_automatic_listening_pauses_for_voice_test_and_then_resumes(self):
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)
        self.app.auto_enabled.set(True)
        self.app.toggle_automatic()
        self.pump(lambda:self.app.auto_running)
        self.assertEqual(str(self.app.speech_test_button.cget('state')),'normal')
        self.app.test_speech()
        self.assertTrue(self.backend.started.wait(1))
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        self.audio.streams[-1].emit(bytes(640))
        self.backend.release.set()
        self.pump(lambda:self.app._speech_future is None)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.app.auto_enabled.set(False)
        self.app.toggle_automatic()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.assertEqual(str(self.app.speech_test_button.cget('state')),'normal')

    def test_manual_capture_blocks_test_and_releases_it_when_finished(self):
        self.app.start_recording()
        self.pump(lambda:self.app.audio_phase=='warming')
        self.app.test_speech()
        self.assertEqual(self.backend.calls,[])
        self.app.stop_recording()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.assertEqual(str(self.app.speech_test_button.cget('state')),'normal')
