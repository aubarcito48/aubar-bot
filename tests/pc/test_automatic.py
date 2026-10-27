from array import array
from dataclasses import replace
from queue import Empty
import threading
import unittest

from audio_fakes import FakeAudio
import test_app
from test_recognition import FakeBackend, FakeDecoder, result
from pc.aubar_control.audio import AudioError, Recording
from pc.aubar_control.automatic_audio import AutomaticCapture, SpeechSegmenter
from pc.aubar_control.recognition import LocalRecognizer, RecognitionResult
from pc.aubar_control.voice_commands import match_command


def pcm(seconds, value=0, rate=16000):
    return array('h',[value]*int(seconds*rate)).tobytes()


class SegmentationTests(unittest.TestCase):
    def test_calibration_handles_steady_background_noise(self):
        detector=SpeechSegmenter(16000,calibrate=True)
        self.assertIsNone(detector.feed(pcm(.4,400)))
        self.assertEqual(detector.calibration_left,0)
        self.assertIsNone(detector.feed(pcm(2,400)))
        self.assertFalse(detector.active)
        self.assertIsInstance(detector.feed(pcm(.5,4000)+pcm(.8,400)),Recording)

    def test_silence_stays_bounded_and_phrase_keeps_its_start(self):
        detector=SpeechSegmenter(16000)
        for _ in range(100):
            self.assertIsNone(detector.feed(pcm(.1)))
        self.assertLessEqual(len(detector.pre_roll),15)
        voice=pcm(.5,4000)
        self.assertIsNone(detector.feed(voice))
        self.assertIsNone(detector.feed(pcm(.78)))
        recording=detector.feed(pcm(.02))
        self.assertIsInstance(recording,Recording)
        self.assertIn(voice,recording.pcm)
        self.assertAlmostEqual(recording.duration,1.54,places=2)
        self.assertFalse(detector.active)

    def test_clicks_and_short_sounds_are_rejected(self):
        detector=SpeechSegmenter(16000)
        self.assertIsNone(detector.feed(pcm(.04,10000)+pcm(1)))
        self.assertIsNone(detector.feed(pcm(.1,10000)+pcm(1)))

    def test_continuous_noise_is_dropped_instead_of_executing_a_truncated_command(self):
        detector=SpeechSegmenter(16000)
        self.assertIsInstance(detector.feed(pcm(11,4000)),AudioError)
        self.assertFalse(detector.active)
        self.assertEqual(len(detector.pending),0)

    def test_pause_blocks_audio_and_fallback_preserves_rate(self):
        backend=FakeAudio()
        backend.reject_16k=True
        capture=AutomaticCapture(backend)
        capture.arm()
        capture.start(1)
        stream=backend.streams[-1]
        stream.emit(pcm(.5,4000,48000)+pcm(1,0,48000))
        self.assertTrue(capture.utterances.empty())
        capture.resume()
        stream.emit(pcm(.4,0,48000))
        stream.emit(pcm(.5,4000,48000)+pcm(.8,0,48000))
        recording=capture.utterances.get_nowait()
        self.assertEqual(recording.sample_rate,48000)
        stream.emit(pcm(.5,4000,48000)+pcm(1,0,48000))
        self.assertTrue(capture.utterances.empty())
        capture.cancel()
        capture.finish()
        self.assertTrue(stream.closed)


class AutomaticRecognitionTests(unittest.TestCase):
    def recognize(self,text,confidence=1):
        engine=LocalRecognizer(backend=FakeBackend(result(text,confidence)))
        return engine.recognize_automatic(Recording(pcm(1,3000),16000))

    def test_aubar_is_required_and_unknown_or_negated_speech_stays_inactive(self):
        for phrase in ('contento','kirby contento','hoy hace frio',
                       'aubar no te pongas contento','aubar contento y celebrar'):
            self.assertIsNone(self.recognize(phrase).action,phrase)
        for phrase,argument in (('aubar contento','contento'),('aubar celebrar','celebrate'),
                                ('aubar mira a la izquierda','izquierda')):
            self.assertEqual(self.recognize(phrase).action.argument,argument)
        self.assertIsNone(self.recognize('aubar contento',.4).action)

    def test_focused_wake_verifies_sound_without_inventing_a_command(self):
        class WakeBackend(FakeBackend):
            wake_calls=0
            def KaldiRecognizer(self, model, rate, grammar=None):
                if grammar is None:
                    return super().KaldiRecognizer(model,rate)
                self.wake_calls+=1
                return FakeDecoder(FakeBackend(self.wake))
        full=result('ayudar contento')
        full['result'][0].update(start=.2,end=.6)
        full['result'][1].update(start=.61,end=1.2)
        backend=WakeBackend(full)
        backend.wake={'text':'au bar','result':[
            dict(word='au',conf=.99,start=.2,end=.4),
            dict(word='bar',conf=.99,start=.4,end=.6)]}
        engine=LocalRecognizer(backend=backend)
        audio=Recording(pcm(1.5,3000),16000)
        self.assertEqual(engine.recognize_automatic(audio).action.argument,'contento')
        backend.wake['result'][1]['conf']=.5
        self.assertIsNone(engine.recognize_automatic(audio).action)
        backend.wake['result'][1]['conf']=.99
        backend.wake['result'].insert(0,dict(word='[unk]',conf=1,start=0,end=.2))
        self.assertIsNone(engine.recognize_automatic(audio).action)
        backend.final=result('ayudar hoy hace frio')
        calls=backend.wake_calls
        self.assertIsNone(engine.recognize_automatic(audio).action)
        self.assertEqual(backend.wake_calls,calls)


class AutomaticAppTests(unittest.TestCase):
    setUp=test_app.AppTests.setUp
    tearDown=test_app.AppTests.tearDown
    pump=test_app.AppTests.pump

    def start_auto(self):
        self.app.connect()
        self.pump(lambda:not self.app.busy)
        self.recognizer.recognize_automatic=self.recognizer.recognize
        self.recognizer.result=RecognitionResult('aubar contento',match_command('contento'),'')
        self.app.auto_enabled.set(True)
        self.app.toggle_automatic()
        self.pump(lambda:self.app.auto_running)
        self.audio.streams[-1].emit(pcm(.02))
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.audio.streams[-1].emit(pcm(.4))

    def speak_auto(self):
        self.audio.streams[-1].emit(pcm(.5,4000)+pcm(.8))

    def test_one_phrase_one_action_then_listening_resumes_without_a_button(self):
        self.assertFalse(self.app.auto_enabled.get())
        self.assertEqual(len(self.audio.streams),0)
        self.start_auto()
        self.speak_auto()
        self.pump(lambda:len(self.session.actions)==1 and self.app.audio_phase=='idle' and not self.app.busy)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.session.actions[0].argument,'contento')
        self.assertIn('Confirmado',self.app.recognition_message.get())
        # No action on silence and no second submission of the same recording.
        self.audio.streams[-1].emit(pcm(1))
        self.root.update()
        self.assertEqual(len(self.session.actions),1)
        self.app.auto_enabled.set(False)
        self.app.toggle_automatic()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.assertTrue(self.audio.streams[-1].closed)

    def test_turning_off_discards_recognition_already_in_progress(self):
        self.start_auto()
        self.recognizer.gate=threading.Event()
        self.speak_auto()
        self.pump(lambda:self.app.audio_phase=='auto_recognizing')
        self.app.auto_enabled.set(False)
        self.app.toggle_automatic()
        self.recognizer.gate.set()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.assertEqual(self.session.actions,[])
        self.assertTrue(self.audio.streams[-1].closed)

    def test_disconnect_disables_listening_and_never_replays_after_reconnect(self):
        self.start_auto()
        self.recognizer.gate=threading.Event()
        self.speak_auto()
        self.pump(lambda:self.app.audio_phase=='auto_recognizing')
        self.app.disconnect()
        self.recognizer.gate.set()
        self.pump(lambda:not self.app.busy and self.app.audio_phase=='idle')
        self.assertFalse(self.app.auto_enabled.get())
        self.assertEqual(self.session.actions,[])
        self.app.connect()
        self.pump(lambda:not self.app.busy)
        self.assertFalse(self.app.auto_enabled.get())
        self.assertEqual(self.session.actions,[])

    def test_unknown_phrase_and_microphone_loss_do_not_send_or_disconnect_usb(self):
        self.start_auto()
        self.recognizer.result=replace(self.recognizer.result,action=None,text='hoy hace frio')
        self.speak_auto()
        self.pump(lambda:self.app.recognition_text.get()=='hoy hace frio')
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.session.actions,[])
        self.app.automatic_capture.finished.set()
        self.pump(lambda:not self.app.auto_enabled.get() and self.app.audio_phase=='idle')
        self.assertTrue(self.app.connected)
        self.assertTrue(self.audio.streams[-1].closed)

    def test_catalog_reply_does_not_resume_listening_during_recognition(self):
        self.start_auto()
        catalog_gate=threading.Event()
        self.addCleanup(catalog_gate.set)
        original=self.session.apply_action
        def delayed(action):
            catalog_gate.wait(2)
            return original(action)
        self.session.apply_action=delayed
        self.app.apply_catalog('EXPRESSION')
        self.recognizer.gate=threading.Event()
        self.speak_auto()
        self.pump(lambda:self.app.audio_phase=='auto_recognizing')
        catalog_gate.set()
        self.pump(lambda:not self.app.busy)
        self.assertEqual(self.app.audio_phase,'auto_recognizing')
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        self.recognizer.gate.set()
        self.pump(lambda:len(self.session.actions)==2 and not self.app.busy)

    def test_turning_off_during_send_does_not_start_a_second_capture(self):
        self.start_auto()
        send_gate=threading.Event()
        self.addCleanup(send_gate.set)
        original=self.session.apply_action
        def delayed(action):
            send_gate.wait(2)
            return original(action)
        self.session.apply_action=delayed
        self.speak_auto()
        self.pump(lambda:self.app.voice_inflight)
        self.app.auto_enabled.set(False)
        self.app.toggle_automatic()
        self.pump(lambda:self.app.audio_phase=='idle')
        count=len(self.audio.streams)
        self.app.start_recording()
        self.assertEqual(len(self.audio.streams),count)
        send_gate.set()
        self.pump(lambda:not self.app.voice_inflight)
        self.assertEqual(len(self.session.actions),1)
