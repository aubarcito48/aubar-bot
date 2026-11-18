import threading
import unittest
from unittest.mock import Mock

import test_app
import test_automatic
from test_automatic import pcm
from test_recognition import FakeBackend, result
from pc.aubar_control.audio import Recording
from pc.aubar_control.recognition import RecognitionResult
from pc.aubar_control.whisper_recognition import WhisperRecognizer
from pc.aubar_control.voice_commands import match_command


class QueryRecognitionTests(unittest.TestCase):
    def recognize(self,text,confidence=1,automatic=True):
        recognizer=WhisperRecognizer(backend=FakeBackend(result(text,confidence)))
        recording=Recording(pcm(2,3000),16000)
        return recognizer.recognize_automatic(recording) if automatic else recognizer.recognize(recording)

    def test_questions_statements_and_greetings_are_queries_after_activation(self):
        for automatic in (True,False):
            for text in ('como estas','contame algo interesante','hola','gracias',
                         'me siento contento','no te pongas enojado','contento y celebrar'):
                with self.subTest(text=text,automatic=automatic):
                    recognized=self.recognize('aubar '+text,automatic=automatic)
                    self.assertEqual(recognized.query,'aubar '+text)
                    self.assertIsNone(recognized.action)

    def test_exact_commands_have_priority_and_unclear_commands_do_not_become_queries(self):
        for phrase in ('contento','enojado derecha','celebrar izquierda','derecha','modo automatico'):
            recognized=self.recognize('aubar '+phrase)
            self.assertEqual(recognized.action,match_command(phrase))
            self.assertIsNone(recognized.query)
            unclear=self.recognize('aubar '+phrase,.5)
            self.assertIsNone(unclear.action)
            self.assertIsNone(unclear.query)
        self.assertEqual(self.recognize('contento',automatic=False).action.argument,'contento')

    def test_automatic_queries_accept_direct_speech_but_not_name_alone(self):
        for phrase in ('como estas','contame algo interesante'):
            self.assertEqual(self.recognize(phrase).query,phrase)
        for phrase in ('aubar','au bar','a un bar'):
            recognized=self.recognize(phrase)
            self.assertIsNone(recognized.action)
            self.assertIsNone(recognized.query)

    def test_manual_button_activates_queries_without_inventing_a_wake_alias(self):
        for phrase in ('como estas','contame algo interesante','ahogar contame algo interesante',
                       'que significa ahogar','no te pongas enojado'):
            recognized=self.recognize(phrase,automatic=False)
            self.assertIsNone(recognized.action)
            self.assertEqual(recognized.query,phrase)
            self.assertEqual(self.recognize(phrase).query,phrase)
        for phrase in ('aubar','au bar','a un bar'):
            self.assertIsNone(self.recognize(phrase,automatic=False).query)

    def test_unclear_nonfinite_and_oversized_queries_are_discarded(self):
        for confidence in (.2,.4,float('nan')):
            recognized=self.recognize('aubar como estas',confidence)
            self.assertIsNone(recognized.action)
            self.assertIsNone(recognized.query)
        recognized=self.recognize('aubar '+'a'*1001)
        self.assertIsNone(recognized.query)

    def test_query_tolerates_one_softer_word_but_rejects_unreliable_evidence(self):
        decoded=result('aubar como estas',.8)
        decoded['result'][-1]['conf']=.4
        audio=Recording(pcm(2,3000),16000)
        engine=WhisperRecognizer(backend=FakeBackend(decoded))
        self.assertEqual(engine.recognize_automatic(audio).query,'aubar como estas')
        decoded['result'][-1]['conf']=.1
        self.assertIsNone(engine.recognize_automatic(audio).query)

    def test_unverified_optional_prefix_is_preserved_in_query(self):
        decoded=result('ayudar como estas')
        for index,word in enumerate(decoded['result']):
            word.update(start=.2+index*.4,end=.6+index*.4)
        self.assertEqual(WhisperRecognizer(backend=FakeBackend(decoded)).recognize_automatic(
            Recording(pcm(2,3000),16000)).query,'ayudar como estas')

    def test_direct_transcript_does_not_need_an_optional_name(self):
        for phrase in ('contento','enojado derecha','como estas'):
            recognized=self.recognize(phrase)
            action=match_command(phrase)
            self.assertEqual(recognized.action,action)
            self.assertEqual(recognized.query,None if action else phrase)


class QueryPanelTests(unittest.TestCase):
    setUp=test_app.AppTests.setUp
    tearDown=test_app.AppTests.tearDown
    pump=test_app.AppTests.pump
    speak=test_app.AppTests.speak
    start_microphone=test_app.AppTests.start_microphone
    start_auto=test_automatic.AutomaticAppTests.start_auto
    speak_auto=test_automatic.AutomaticAppTests.speak_auto

    def query_result(self):
        return RecognitionResult('ayudar como estas',None,'Consulta reconocida.',query='como estas')

    def test_automatic_query_is_identified_without_api_usb_or_speech_then_commands_still_work(self):
        self.start_auto()
        self.app.ai_service.submit=Mock(side_effect=AssertionError('Queries must stay local in TK29'))
        self.recognizer.result=self.query_result()
        self.speak_auto()
        self.pump(lambda:self.app.recognized_query=='como estas')
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.app.recognition_text.get(),'como estas')
        self.assertEqual(self.session.actions,[])
        self.assertEqual(self.app.speech.calls,[])
        self.app.ai_service.submit.assert_not_called()
        self.recognizer.result=RecognitionResult('aubar enojado derecha',match_command('enojado derecha'),'')
        self.speak_auto()
        self.pump(lambda:len(self.session.actions)==1 and not self.app.busy)
        self.assertIsNone(self.app.recognized_query)
        self.assertEqual(self.session.actions[0].look,'derecha')

    def test_manual_query_is_visible_without_device_and_cleared_at_next_capture(self):
        self.recognizer.result=self.query_result()
        self.speak()
        self.pump(lambda:self.app.recognized_query=='como estas')
        self.assertFalse(self.app.connected)
        self.assertIsNone(self.app._ai_future)
        self.start_microphone()
        self.assertIsNone(self.app.recognized_query)

    def test_switching_off_during_recognition_drops_query_and_reconnect_does_not_replay_it(self):
        self.start_auto()
        self.recognizer.result=self.query_result()
        self.recognizer.gate=threading.Event()
        self.speak_auto()
        self.pump(lambda:self.app.audio_phase=='auto_recognizing')
        self.app.auto_enabled.set(False);self.app.toggle_automatic()
        self.recognizer.gate.set()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.assertIsNone(self.app.recognized_query)
        self.assertIsNone(self.app._ai_future)
        self.app.disconnect();self.pump(lambda:not self.app.busy)
        self.app.connect();self.pump(lambda:self.app.connected and not self.app.busy)
        self.assertIsNone(self.app.recognized_query)
        self.assertEqual(self.session.actions,[])
