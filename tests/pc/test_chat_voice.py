"""Written chat playback, opt-in, cancellation and replay without real services."""
import unittest

import test_voice_conversation as voice_tests


class ChatVoiceTests(unittest.TestCase):
    pump=voice_tests.VoiceConversationTests.pump

    def setUp(self):
        voice_tests.VoiceConversationTests.setUp(self)

    def tearDown(self):
        voice_tests.VoiceConversationTests.tearDown(self)

    def send(self):
        self.app.ai_input.set('Hola, soy Nahuel')
        self.app.send_ai_message()

    def test_text_only_by_default_and_manual_replay_reads_only_the_answer(self):
        self.assertIn('Onyx',self.app.speech_voice.get())
        self.client.release.set()
        self.send()
        self.pump(lambda:self.app._ai_future is None)
        self.assertEqual(self.voice.calls,[])
        self.assertEqual(str(self.app.ai_read_button.cget('state')),'normal')
        self.app.ai_read_button.invoke()
        self.pump(lambda:len(self.voice.calls)==1)
        self.assertEqual(self.voice.calls,['Respuesta de prueba.'])
        self.assertTrue(self.app._speech_is_ai)
        self.app.ai_voice_stop_button.invoke()
        self.pump(lambda:self.app._speech_future is None)
        self.assertEqual(self.app.conversation.turn_count,1)

    def test_enabled_chat_reads_the_answer_without_an_esp32_connection(self):
        self.app.ai_voice_check.invoke()
        self.assertTrue(self.app.chat_voice_enabled.get())
        self.assertTrue(self.app.speech_enabled.get())
        self.assertFalse(self.app.connected)
        self.send()
        self.client.release.set()
        self.pump(lambda:len(self.voice.calls)==1)
        self.assertEqual(self.voice.calls,['Respuesta de prueba.'])
        self.assertIn('Respuesta de prueba.',self.app.ai_response.get('1.0','end'))
        self.app.ai_voice_stop_button.invoke()
        self.pump(lambda:self.app._speech_future is None)
        self.assertEqual(len(self.voice.calls),1)

    def test_muting_and_reenabling_does_not_autoplay_a_late_answer(self):
        self.app.ai_voice_check.invoke()
        self.send()
        self.app.ai_voice_check.invoke()
        self.app.ai_voice_check.invoke()
        self.client.release.set()
        self.pump(lambda:self.app._ai_future is None)
        self.assertEqual(self.voice.calls,[])
        self.assertEqual(self.app.conversation.turn_count,1)
        self.app.ai_read_button.invoke()
        self.pump(lambda:len(self.voice.calls)==1)

    def test_new_conversation_clears_the_answer_available_for_replay(self):
        self.client.release.set()
        self.send()
        self.pump(lambda:self.app._ai_future is None)
        self.app.new_conversation()
        self.assertIsNone(self.app._last_ai_reply)
        self.assertEqual(str(self.app.ai_read_button.cget('state')),'disabled')
        self.app.read_ai_response()
        self.assertEqual(self.voice.calls,[])

    def test_stop_while_waiting_suppresses_late_chat_voice_but_keeps_text(self):
        self.app.ai_voice_check.invoke()
        self.send()
        self.app.stop_speech()
        self.client.release.set()
        self.pump(lambda:self.app._ai_future is None)
        self.assertEqual(self.voice.calls,[])
        self.assertEqual(self.app.conversation.turn_count,1)


if __name__=='__main__':
    unittest.main()
