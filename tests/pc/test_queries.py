import threading
import unittest
from unittest.mock import Mock

import test_app
import test_automatic
from test_automatic import pcm
from test_recognition import FakeBackend, FakeDecoder, result
from pc.aubar_control.audio import Recording
from pc.aubar_control.recognition import LocalRecognizer, RecognitionResult
from pc.aubar_control.voice_commands import match_command


class QueryRecognitionTests(unittest.TestCase):
    def recognize(self,text,confidence=1,automatic=True):
        recognizer=LocalRecognizer(backend=FakeBackend(result(text,confidence)))
        return recognizer.recognize(Recording(pcm(2,3000),16000),require_wake=automatic)

    def test_questions_statements_and_greetings_are_queries_after_activation(self):
        for automatic in (True,False):
            for text in ('como estas','contame algo interesante','hola','gracias',
                         'me siento contento','no te pongas enojado','contento y celebrar'):
                with self.subTest(text=text,automatic=automatic):
                    recognized=self.recognize('aubar '+text,automatic=automatic)
                    self.assertEqual(recognized.query,text)
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

    def test_queries_require_activation_and_a_body_in_both_capture_modes(self):
        for automatic in (True,False):
            for phrase in ('como estas','contame algo interesante','kirby como estas','aubar','au bar','a un bar'):
                recognized=self.recognize(phrase,automatic=automatic)
                self.assertIsNone(recognized.action)
                self.assertIsNone(recognized.query)

    def test_unclear_nonfinite_and_oversized_queries_are_discarded(self):
        for confidence in (.2,.4,float('nan')):
            recognized=self.recognize('aubar como estas',confidence)
            self.assertIsNone(recognized.action)
            self.assertIsNone(recognized.query)
        recognized=self.recognize('aubar '+'a'*1001)
        self.assertIsNone(recognized.query)

    def test_query_tolerates_one_softer_word_but_not_a_misaligned_transcript(self):
        decoded=result('aubar como estas',.8)
        decoded['result'][-1]['conf']=.4
        audio=Recording(pcm(2,3000),16000)
        engine=LocalRecognizer(backend=FakeBackend(decoded))
        self.assertEqual(engine.recognize_automatic(audio).query,'como estas')
        decoded['result'].pop()
        self.assertIsNone(engine.recognize_automatic(audio).query)

    def test_focused_wake_accepts_a_pause_without_swallowing_query_words_or_negation(self):
        class WakeBackend(FakeBackend):
            def KaldiRecognizer(self,model,rate,grammar=None):
                if grammar is None:
                    return super().KaldiRecognizer(model,rate)
                return FakeDecoder(FakeBackend(self.wake))
        decoded=result('ayudar no enojado')
        for word,start,end in zip(decoded['result'],(.2,.9,1.1),(.6,1.1,1.4)):
            word.update(start=start,end=end)
        backend=WakeBackend(decoded)
        backend.wake={'text':'au bar','result':[
            dict(word='au',conf=.99,start=.2,end=.4),
            dict(word='bar',conf=.99,start=.4,end=.6)]}
        audio=Recording(pcm(2,3000),16000)
        engine=LocalRecognizer(backend=backend)
        recognized=engine.recognize_automatic(audio)
        self.assertEqual(recognized.query,'no enojado')
        self.assertIsNone(recognized.action)
        # A weak first query word must not be removed to create a command.
        decoded['result'][1]['conf']=.1
        recognized=engine.recognize_automatic(audio)
        self.assertIsNone(recognized.action)
        self.assertIsNone(recognized.query)
        decoded['result'][1]['conf']=1
        backend.wake['result'][1]['conf']=.4
        self.assertIsNone(engine.recognize_automatic(audio).query)

    def test_unverified_phonetic_prefix_does_not_activate_a_query(self):
        decoded=result('ayudar como estas')
        for index,word in enumerate(decoded['result']):
            word.update(start=.2+index*.4,end=.6+index*.4)
        self.assertIsNone(LocalRecognizer(backend=FakeBackend(decoded)).recognize_automatic(
            Recording(pcm(2,3000),16000)).query)

    def test_asr_can_omit_name_only_if_prefix_audio_still_verifies_it(self):
        class OmittedNameBackend(FakeBackend):
            def KaldiRecognizer(self,model,rate,grammar=None):
                if grammar is None:
                    return super().KaldiRecognizer(model,rate)
                return FakeDecoder(FakeBackend(self.wake))
        audio=Recording(pcm(2,3000),16000)
        for phrase in ('contento','enojado derecha','como estas'):
            decoded=result(phrase)
            for index,word in enumerate(decoded['result']):
                word.update(start=.8+index*.3,end=1.1+index*.3)
            backend=OmittedNameBackend(decoded)
            backend.wake={'text':'au bar','result':[
                dict(word='au',conf=.99,start=.2,end=.4),
                dict(word='bar',conf=.99,start=.4,end=.6)]}
            engine=LocalRecognizer(backend=backend)
            recognized=engine.recognize_automatic(audio)
            action=match_command(phrase)
            self.assertEqual(recognized.action,action)
            self.assertEqual(recognized.query,None if action else phrase)
            # The same transcript without acoustic proof must stay inactive.
            backend.wake={'text':'[unk]','result':[dict(word='[unk]',conf=1,start=.2,end=.6)]}
            rejected=engine.recognize_automatic(audio)
            self.assertIsNone(rejected.action)
            self.assertIsNone(rejected.query)


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
