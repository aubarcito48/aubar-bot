import threading
import unittest

import test_app
from test_speech import FakeSpeechBackend
import test_automatic
from test_automatic import pcm
from pc.aubar_control.catalog import EXPRESSIONS, ANIMATIONS
from pc.aubar_control.responses import confirmation_text
from pc.aubar_control.voice_commands import VoiceAction, match_command
from pc.aubar_control.speech import SpeechEngine, SpeechError
from pc.aubar_control.recognition import RecognitionResult


class ResponseTextTests(unittest.TestCase):
    def test_all_actions_and_153_combinations_have_a_response(self):
        for command,catalog in (('EXPRESSION',EXPRESSIONS),('ANIMATION',ANIMATIONS)):
            for identifier in catalog:
                for direction in (None,'izquierda','centro','derecha'):
                    text=confirmation_text(VoiceAction(command,identifier,'',direction))
                    self.assertIsInstance(text,str)
                    self.assertTrue(text.endswith('.'))
                    self.assertNotIn('Aubar',text)
                    if direction is not None:
                        self.assertIn('mirando '+('al centro' if direction=='centro' else 'a la '+direction),text)
        for phrase in ('derecha','izquierda','centro','modo automatico','modo manual'):
            self.assertIsInstance(confirmation_text(match_command(phrase)),str)
        self.assertEqual(confirmation_text(match_command('enojado derecha')),
                         'Estoy enojado mirando a la derecha.')
        self.assertEqual(confirmation_text(match_command('celebrar izquierda')),
                         'Voy a celebrar mirando a la izquierda.')
        for action in (VoiceAction('EXPRESSION','bogus',''),VoiceAction('MODE','bad',''),
                       VoiceAction('LOOK','arriba',''),VoiceAction('ANIMATION','happy','','arriba')):
            self.assertIsNone(confirmation_text(action))


class ConfirmedResponseTests(unittest.TestCase):
    setUp=test_app.AppTests.setUp
    tearDown=test_app.AppTests.tearDown
    pump=test_app.AppTests.pump
    start_microphone=test_app.AppTests.start_microphone
    speak=test_app.AppTests.speak

    def connect(self):
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)

    def test_manual_voice_speaks_exactly_once_after_confirmation_not_after_status_polls(self):
        self.connect()
        gate=threading.Event()
        self.addCleanup(gate.set)
        original=self.session.apply_action
        def delayed(action):
            gate.wait(2)
            return original(action)
        self.session.apply_action=delayed
        self.recognizer.result=RecognitionResult('enojado derecha',match_command('enojado derecha'),'')
        self.speak()
        self.pump(lambda:self.app.voice_inflight)
        self.assertEqual(self.app.speech.calls,[])
        gate.set()
        self.pump(lambda:len(self.app.speech.calls)==1)
        self.assertEqual(self.app.speech.calls[0][0],'Estoy enojado mirando a la derecha.')
        self.app.refresh_status()
        self.pump(lambda:not self.app.busy and self.app._speech_future is None)
        self.assertEqual(len(self.app.speech.calls),1)

    def test_catalog_acknowledgment_also_speaks(self):
        self.connect()
        selected,_=self.app.catalog_choices['ANIMATION']
        selected.set('Celebrar')
        self.app.apply_catalog('ANIMATION')
        self.pump(lambda:len(self.app.speech.calls)==1)
        self.assertEqual(self.app.speech.calls[0][0],'Voy a celebrar.')

    def test_no_voice_on_failed_confirmation_unknown_phrase_or_muted_output(self):
        self.connect()
        self.session.fail=True
        self.speak()
        self.pump(lambda:not self.app.busy and not self.app.connected)
        self.assertEqual(self.app.speech.calls,[])
        self.session.fail=False
        self.connect()
        self.recognizer.result=RecognitionResult('hoy hace frio',None,'Sin acción.')
        self.speak()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.assertEqual(self.app.speech.calls,[])
        self.recognizer.result=RecognitionResult('contento',match_command('contento'),'')
        self.app.speech_enabled.set(False)
        self.app.toggle_speech()
        self.speak()
        self.pump(lambda:len(self.session.actions)==1 and not self.app.busy)
        self.assertEqual(self.app.speech.calls,[])
        self.app.speech_enabled.set(True)
        self.app.toggle_speech()
        self.root.update()
        self.assertEqual(self.app.speech.calls,[])

    def test_stale_acknowledgment_and_pending_response_are_not_replayed(self):
        self.connect()
        action=match_command('contento')
        old_token=self.app.connection_token-1
        self.app.events.put(('voice',(old_token,action,self.session.state),None))
        self.pump(lambda:self.app.events.empty())
        self.assertEqual(self.app.speech.calls,[])
        self.app.audio_phase='recognizing'
        self.app._queue_confirmed_reply(action,self.app.connection_token)
        self.app.disconnect()
        self.pump(lambda:not self.app.busy)
        self.app.audio_phase='idle'
        self.connect()
        self.assertIsNone(self.app._pending_reply)
        self.assertEqual(self.app.speech.calls,[])

    def test_response_source_can_supply_free_text_without_changing_the_engine(self):
        self.connect()
        self.app.reply_provider=lambda action:'Una respuesta independiente del avatar.'
        self.speak()
        self.pump(lambda:len(self.app.speech.calls)==1)
        self.assertEqual(self.app.speech.calls[0][0],'Una respuesta independiente del avatar.')

    def test_speech_error_does_not_undo_the_confirmed_action_or_repeat_it(self):
        self.connect()
        def unavailable(text,**settings):
            raise SpeechError('No hay voz española.')
        self.app.speech.speak=unavailable
        self.speak()
        self.pump(lambda:len(self.session.actions)==1 and not self.app.busy)
        self.assertEqual(self.app.values['expression'].get(),'Contento')
        self.assertTrue(self.app.connected)
        self.assertIn('confirmado',self.app.recognition_message.get().casefold())
        self.assertIn('española',self.app.speech_message.get())
        self.assertIsNone(self.app._pending_reply)


class AutomaticResponseTests(unittest.TestCase):
    setUp=test_app.AppTests.setUp
    tearDown=test_app.AppTests.tearDown
    pump=test_app.AppTests.pump
    start_auto=test_automatic.AutomaticAppTests.start_auto
    speak_auto=test_automatic.AutomaticAppTests.speak_auto

    def test_automatic_response_discards_its_audio_and_resumes_without_repeating_the_action(self):
        self.start_auto()
        self.app.speech.close()
        backend=FakeSpeechBackend()
        self.addCleanup(backend.release.set)
        self.app.speech=SpeechEngine(backend)
        self.speak_auto()
        self.pump(lambda:backend.started.is_set())
        self.assertEqual(len(self.session.actions),1)
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        self.audio.streams[-1].emit(pcm(.6,4000)+pcm(.8))
        self.assertTrue(self.app.automatic_capture.utterances.empty())
        backend.release.set()
        self.pump(lambda:self.app._speech_future is None)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertEqual(len(self.session.actions),1)
        self.assertEqual(len(backend.calls),1)

    def test_switching_off_listening_while_speaking_is_respected(self):
        self.start_auto()
        self.app.speech.close()
        backend=FakeSpeechBackend()
        self.addCleanup(backend.release.set)
        self.app.speech=SpeechEngine(backend)
        self.speak_auto()
        self.pump(lambda:backend.started.is_set())
        self.app.auto_enabled.set(False)
        self.app.toggle_automatic()
        self.pump(lambda:self.app.audio_phase=='idle')
        backend.release.set()
        self.pump(lambda:self.app._speech_future is None)
        self.assertFalse(self.app.auto_enabled.get())
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        self.assertTrue(self.audio.streams[-1].closed)
