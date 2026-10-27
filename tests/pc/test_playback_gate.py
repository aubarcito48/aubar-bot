from concurrent.futures import Future
import unittest

import test_app
import test_automatic
from pc.aubar_control.audio import Recording
from pc.aubar_control.playback_gate import PlaybackGate
from pc.aubar_control.speech import SpeechCancelled, SpeechError, SpeechVoice
from test_automatic import pcm


class Clock:
    now=10.0
    def __call__(self):
        return self.now
    def advance(self,seconds):
        self.now+=seconds


class PlaybackGateTests(unittest.TestCase):
    def test_finish_retains_echo_guard_and_old_finish_cannot_release_a_new_playback(self):
        clock=Clock()
        gate=PlaybackGate(clock)
        first=gate.begin()
        self.assertTrue(gate.blocked)
        gate.finish(first)
        clock.advance(.34)
        self.assertTrue(gate.blocked)
        second=gate.begin()
        gate.finish(first)
        clock.advance(10)
        self.assertTrue(gate.active)
        gate.finish(second)
        clock.advance(.36)
        self.assertFalse(gate.blocked)

    def test_calibration_interrupted_by_playback_restarts_before_accepting_voice(self):
        from pc.aubar_control.automatic_audio import AutomaticCapture
        from audio_fakes import FakeAudio
        backend=FakeAudio()
        capture=AutomaticCapture(backend)
        capture.arm();capture.start(1);capture.resume()
        stream=backend.streams[-1]
        stream.emit(pcm(.2,400))
        self.assertTrue(capture.calibrating)
        capture.pause();capture.resume()
        self.assertEqual(capture.detector.calibration_left,20)
        stream.emit(pcm(.4,400))
        self.assertFalse(capture.calibrating)
        stream.emit(pcm(1,400))
        self.assertFalse(capture.speaking)
        capture.finish()


class ControlledSpeech:
    def __init__(self):
        self.calls=[]
        self.future=None
        self.before_start=lambda:None
        self.closed=False

    @property
    def busy(self):
        return self.future is not None and not self.future.done()

    def speak(self,text,**settings):
        self.before_start()
        self.calls.append(text)
        self.future=Future()
        return self.future

    def finish(self,error=None):
        if not self.busy:
            return
        if error:
            self.future.set_exception(error)
        else:
            self.future.set_result(SpeechVoice('es-test','Voz de prueba','es-MX'))

    def stop(self):
        self.finish(SpeechCancelled('Detenida.'))

    def close(self):
        self.closed=True
        self.stop()


class PlaybackCoordinationTests(unittest.TestCase):
    pump=test_app.AppTests.pump
    start_auto=test_automatic.AutomaticAppTests.start_auto
    speak_auto=test_automatic.AutomaticAppTests.speak_auto

    def setUp(self):
        test_app.AppTests.setUp(self)
        self.app.speech.close()
        self.voice=ControlledSpeech()
        self.app.speech=self.voice
        self.clock=Clock()
        self.app.playback_gate=PlaybackGate(self.clock)

    def tearDown(self):
        test_app.AppTests.tearDown(self)

    def release_guard(self):
        self.clock.advance(.36)
        self.pump(lambda:not self.app._microphone_blocked())

    def test_test_and_free_text_pause_before_audio_starts_and_discard_old_and_new_audio(self):
        self.start_auto()
        def before_start():
            self.assertFalse(self.app.automatic_capture.listening.is_set())
            self.assertTrue(self.app.automatic_capture.utterances.empty())
        self.voice.before_start=before_start
        for testing in (True,False):
            self.app.automatic_capture.utterances.put(Recording(pcm(.5,4000),16000))
            self.assertTrue(self.app.speak_text('Aubar, contento.',is_test=testing))
            self.audio.streams[-1].emit(pcm(.5,4000)+pcm(.8))
            self.assertTrue(self.app.automatic_capture.utterances.empty())
            self.voice.finish()
            self.pump(lambda:self.app._speech_future is None)
            self.assertFalse(self.app.automatic_capture.listening.is_set())
            self.audio.streams[-1].emit(pcm(.5,4000)+pcm(.8))
            self.assertTrue(self.app.automatic_capture.utterances.empty())
            self.release_guard()
            self.pump(lambda:self.app.automatic_capture.listening.is_set())
            self.assertEqual(self.session.actions,[])
        # A new user phrase after playback is still accepted exactly once.
        self.speak_auto()
        self.pump(lambda:len(self.session.actions)==1 and self.voice.busy)
        self.assertEqual(len(self.voice.calls),3)

    def test_stop_and_mute_release_only_after_echo_guard_and_preserve_listening_preference(self):
        self.start_auto()
        for mute in (False,True):
            self.app.test_speech()
            if mute:
                self.app.speech_enabled.set(False)
                self.app.toggle_speech()
            else:
                self.app.stop_speech()
            self.pump(lambda:self.app._speech_future is None)
            self.assertFalse(self.app.automatic_capture.listening.is_set())
            self.release_guard()
            self.pump(lambda:self.app.automatic_capture.listening.is_set())
            self.assertTrue(self.app.auto_enabled.get())
            self.assertEqual(self.session.actions,[])
            if mute:
                self.app.speech_enabled.set(True);self.app.toggle_speech()

    def test_switching_off_microphone_during_test_never_reopens_it_after_completion(self):
        self.start_auto()
        stream=self.audio.streams[-1]
        self.app.test_speech()
        self.app.auto_enabled.set(False);self.app.toggle_automatic()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.voice.finish()
        self.pump(lambda:self.app._speech_future is None)
        self.release_guard()
        self.assertFalse(self.app.auto_enabled.get())
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        self.assertTrue(stream.closed)

    def test_async_and_startup_errors_do_not_leave_microphone_paused(self):
        self.start_auto()
        self.app.test_speech()
        self.voice.finish(SpeechError('Fallo de salida.'))
        self.pump(lambda:self.app._speech_future is None)
        self.release_guard()
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertIn('Fallo de salida',self.app.speech_message.get())
        def fail_before_start(text,**settings):
            raise SpeechError('No se pudo iniciar.')
        self.voice.speak=fail_before_start
        self.app.test_speech()
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        self.release_guard()
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertIn('No se pudo iniciar',self.app.speech_message.get())
        self.assertEqual(self.session.actions,[])

    def test_manual_microphone_cannot_open_during_playback_or_echo_guard(self):
        self.app.test_speech()
        self.app.start_recording()
        self.assertEqual(self.audio.streams,[])
        self.voice.finish()
        self.pump(lambda:self.app._speech_future is None)
        self.app.start_recording()
        self.assertEqual(self.audio.streams,[])
        self.release_guard()
        self.pump(lambda:str(self.app.talk_button.cget('state'))=='normal')
        self.app.start_recording()
        self.pump(lambda:self.app.audio_phase=='warming')
        self.assertEqual(len(self.audio.streams),1)

    def test_disconnect_during_test_does_not_resume_after_reconnect(self):
        self.start_auto()
        self.app.test_speech()
        self.app.disconnect()
        self.pump(lambda:not self.app.busy and self.app.audio_phase=='idle')
        self.voice.finish()
        self.pump(lambda:self.app._speech_future is None)
        self.release_guard()
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)
        self.assertFalse(self.app.auto_enabled.get())
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.session.actions,[])

    def test_closing_while_paused_cancels_audio_and_microphone_without_restart(self):
        self.start_auto()
        stream=self.audio.streams[-1]
        self.app.test_speech()
        self.app.close()
        self.assertTrue(self.voice.closed)
        self.assertFalse(self.app.automatic_capture.requested.is_set())
        self.assertFalse(self.app.automatic_capture.listening.is_set())
