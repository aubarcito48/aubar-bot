import threading
import unittest

import test_app
import test_automatic
from test_groq_client import ControlledClient,KEY
from test_playback_gate import Clock,ControlledSpeech
from test_automatic import pcm
from pc.aubar_control.config import load_groq_config
from pc.aubar_control.groq_client import GroqService
from pc.aubar_control.playback_gate import PlaybackGate
from pc.aubar_control.recognition import RecognitionResult
from pc.aubar_control.speech import SpeechError
from pc.aubar_control.voice_commands import match_command


class VoiceConversationTests(unittest.TestCase):
    pump=test_app.AppTests.pump
    start_microphone=test_app.AppTests.start_microphone
    speak=test_app.AppTests.speak
    start_auto=test_automatic.AutomaticAppTests.start_auto
    speak_auto=test_automatic.AutomaticAppTests.speak_auto

    def setUp(self):
        test_app.AppTests.setUp(self)
        self.app.ai_service.close()
        self.client=ControlledClient()
        self.app.ai_service=GroqService(self.client)
        self.app.speech.close();self.voice=ControlledSpeech();self.app.speech=self.voice
        self.clock=Clock();self.app.playback_gate=PlaybackGate(self.clock)
        self.app.config_loader=lambda:load_groq_config(None,{'GROQ_API_KEY':KEY})
        self.app.reload_groq_configuration()

    def tearDown(self):
        self.client.release.set()
        test_app.AppTests.tearDown(self)

    def question(self,text='como estas'):
        self.recognizer.result=RecognitionResult('aubar '+text,None,'Consulta reconocida.',query=text)

    def automatic_question(self):
        self.start_auto();self.question();self.speak_auto()
        self.pump(lambda:self.client.started.is_set())

    def finish_voice(self):
        self.voice.finish()
        self.pump(lambda:self.app._speech_future is None)
        self.clock.advance(.36)

    def test_automatic_question_one_answer_echo_discard_resume_and_local_command_priority(self):
        self.automatic_question()
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.voice.calls,[])
        self.client.release.set();self.pump(lambda:len(self.voice.calls)==1)
        self.assertEqual(self.app.conversation.turn_count,1)
        self.assertIn('Aubar: Respuesta de prueba.',self.app.ai_response.get('1.0','end'))
        self.audio.streams[-1].emit(pcm(.6,4000)+pcm(.8))
        self.assertTrue(self.app.automatic_capture.utterances.empty())
        self.assertEqual(len(self.client.calls),1)
        self.assertEqual(self.session.actions,[])
        self.finish_voice();self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.recognizer.result=RecognitionResult('aubar enojado derecha',match_command('enojado derecha'),'')
        self.speak_auto();self.pump(lambda:len(self.session.actions)==1 and len(self.voice.calls)==2)
        self.assertEqual(len(self.client.calls),1)

    def test_manual_question_without_usb_speaks_but_never_reopens_manual_capture(self):
        self.question('contame algo interesante');self.speak()
        self.pump(lambda:self.client.started.is_set())
        self.assertFalse(self.app.connected)
        self.assertEqual(str(self.app.talk_button.cget('state')),'disabled')
        self.client.release.set();self.pump(lambda:len(self.voice.calls)==1)
        self.finish_voice()
        self.pump(lambda:str(self.app.talk_button.cget('state'))=='normal')
        self.assertEqual(len(self.audio.streams),1)
        self.assertFalse(self.app.auto_enabled.get())

    def test_text_and_voice_queries_share_context_but_text_does_not_autoplay(self):
        self.client.release.set()
        self.app.ai_input.set('Me llamo Nahuel');self.app.send_ai_message()
        self.pump(lambda:self.app._ai_future is None)
        self.assertEqual(self.voice.calls,[])
        self.question('como me llamo');self.speak()
        self.pump(lambda:len(self.voice.calls)==1)
        self.assertEqual(self.client.calls[-1].messages[1].content,'Me llamo Nahuel')
        self.assertEqual(self.app.conversation.turn_count,2)

    def test_mute_then_reenable_while_waiting_keeps_text_without_replaying_voice(self):
        self.automatic_question()
        self.app.speech_enabled.set(False);self.app.toggle_speech()
        self.app.speech_enabled.set(True);self.app.toggle_speech()
        self.client.release.set();self.pump(lambda:self.app._ai_future is None)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.voice.calls,[])
        self.assertEqual(self.app.conversation.turn_count,1)

    def test_stop_while_waiting_suppresses_late_voice_but_keeps_successful_text(self):
        self.automatic_question()
        self.app.stop_speech()
        self.client.release.set();self.pump(lambda:self.app._ai_future is None)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.voice.calls,[])
        self.assertEqual(self.app.conversation.turn_count,1)

    def test_api_failure_resumes_listening_without_history_and_next_question_works(self):
        self.automatic_question()
        self.client.error=OSError(KEY);self.client.release.set()
        self.pump(lambda:self.app._ai_future is None)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertTrue(self.app.connected)
        self.assertEqual(self.app.conversation.turn_count,0)
        self.assertEqual(self.voice.calls,[])
        self.assertNotIn(KEY,self.app.recognition_message.get())
        self.client.error=None;self.speak_auto()
        self.pump(lambda:len(self.voice.calls)==1)

    def test_speech_failure_keeps_text_and_context_without_repeating_request(self):
        self.automatic_question();self.client.release.set()
        self.pump(lambda:len(self.voice.calls)==1)
        self.voice.finish(SpeechError('Salida no disponible'))
        self.pump(lambda:self.app._speech_future is None)
        self.clock.advance(.36)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.app.conversation.turn_count,1)
        self.assertEqual(len(self.client.calls),1)
        self.assertIn('Respuesta de prueba',self.app.ai_response.get('1.0','end'))

    def test_new_conversation_discards_pending_voice_response_and_old_capture(self):
        self.automatic_question();self.app.new_conversation()
        self.client.release.set();self.pump(lambda:self.app._ai_future is None)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.app.conversation.turn_count,0)
        self.assertEqual(self.voice.calls,[])
        self.recognizer.gate=threading.Event()
        self.speak_auto();self.pump(lambda:self.app.audio_phase=='auto_recognizing')
        self.app.new_conversation();self.recognizer.gate.set()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.assertEqual(len(self.client.calls),1)

    def test_disconnect_during_query_drops_late_answer_and_reconnect_does_not_replay(self):
        self.automatic_question()
        self.app.disconnect();self.pump(lambda:not self.app.busy and self.app.audio_phase=='idle')
        self.client.release.set();self.pump(lambda:self.app._ai_future is None)
        self.app.connect();self.pump(lambda:self.app.connected and not self.app.busy)
        self.assertEqual(self.app.conversation.turn_count,0)
        self.assertEqual(self.voice.calls,[])
        self.assertFalse(self.app.auto_enabled.get())

    def test_switching_microphone_off_while_speaking_is_respected(self):
        self.automatic_question();self.client.release.set()
        self.pump(lambda:len(self.voice.calls)==1)
        self.app.auto_enabled.set(False);self.app.toggle_automatic()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.finish_voice()
        self.assertFalse(self.app.automatic_capture.requested.is_set())
        self.assertFalse(self.app.auto_enabled.get())
        self.assertFalse(self.app.automatic_capture.listening.is_set())

    def test_ai_answer_waits_for_catalog_voice_and_stop_discards_both_without_overlap(self):
        self.automatic_question()
        self.app.catalog_choices['ANIMATION'][0].set('Celebrar')
        self.app.apply_catalog('ANIMATION')
        self.pump(lambda:len(self.voice.calls)==1)
        self.assertEqual(self.voice.calls[0],'Voy a celebrar.')
        self.client.release.set();self.pump(lambda:self.app._ai_future is None)
        self.assertIsNotNone(self.app.ai_replies.pending)
        self.assertEqual(len(self.voice.calls),1)
        self.app.stop_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.clock.advance(.36)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertIsNone(self.app.ai_replies.pending)
        self.assertEqual(len(self.voice.calls),1)
        self.assertEqual(self.app.conversation.turn_count,1)
