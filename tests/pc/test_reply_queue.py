import threading
import unittest

import test_app
from test_playback_gate import Clock, ControlledSpeech
from pc.aubar_control.reply_queue import ReplyQueue
from pc.aubar_control.speech import SpeechError


class ReplyQueueTests(unittest.TestCase):
    def test_burst_keeps_only_latest_and_taking_it_cannot_repeat_it(self):
        queue=ReplyQueue()
        for i in range(1000):
            self.assertTrue(queue.put(str(i),1,queue.generation))
        self.assertEqual(queue.take(1).text,'999')
        self.assertIsNone(queue.take(1))

    def test_expiry_and_connection_scope_drop_old_responses(self):
        clock=Clock()
        queue=ReplyQueue(clock)
        queue.put('Vieja',1,queue.generation)
        clock.advance(15)
        self.assertIsNone(queue.pending)
        queue.put('Otra',1,queue.generation)
        self.assertIsNone(queue.peek(2))
        self.assertIsNone(queue.peek(1))

    def test_cancel_invalidates_late_acknowledgments_without_overwriting_new_reply(self):
        queue=ReplyQueue()
        old=queue.generation
        queue.put('Pendiente',1,old)
        queue.cancel()
        self.assertIsNone(queue.pending)
        queue.put('Nueva',1,queue.generation)
        self.assertFalse(queue.put('Confirmación tardía',1,old))
        self.assertEqual(queue.pending.text,'Nueva')


class PlaybackInterruptionTests(unittest.TestCase):
    pump=test_app.AppTests.pump
    start_microphone=test_app.AppTests.start_microphone
    speak=test_app.AppTests.speak

    def setUp(self):
        test_app.AppTests.setUp(self)
        self.app.speech.close()
        self.voice=ControlledSpeech()
        self.app.speech=self.voice
        self.clock=Clock()
        self.app.replies=ReplyQueue(self.clock)
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)

    def tearDown(self):
        test_app.AppTests.tearDown(self)

    def catalog(self,label):
        selected,_=self.app.catalog_choices['ANIMATION']
        selected.set(label)
        self.app.apply_catalog('ANIMATION')
        self.pump(lambda:not self.app.busy)

    def test_catalog_burst_does_not_overlap_and_announces_only_latest_pending(self):
        self.app.test_speech()
        self.catalog('Pensar')
        self.catalog('Celebrar')
        self.catalog('Reír')
        self.assertEqual(len(self.session.actions),3)
        self.assertEqual(len(self.voice.calls),1)
        self.assertEqual(self.app._pending_reply.text,'Voy a reír.')
        self.voice.finish()
        self.pump(lambda:len(self.voice.calls)==2)
        self.assertEqual(self.voice.calls[-1],'Voy a reír.')
        self.assertIsNone(self.app._pending_reply)
        self.voice.finish()
        self.pump(lambda:self.app._speech_future is None)
        self.assertEqual(len(self.voice.calls),2)

    def test_stop_clears_current_and_pending_responses_and_does_not_replay(self):
        self.app.test_speech()
        self.catalog('Pensar')
        self.assertIsNotNone(self.app._pending_reply)
        self.app.stop_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.assertIsNone(self.app._pending_reply)
        self.assertEqual(len(self.voice.calls),1)
        self.catalog('Celebrar')
        self.pump(lambda:len(self.voice.calls)==2)
        self.assertEqual(self.voice.calls[-1],'Voy a celebrar.')

    def test_mute_discards_pending_and_reenabling_does_not_replay(self):
        self.app.test_speech()
        self.catalog('Pensar')
        self.app.speech_enabled.set(False);self.app.toggle_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.app.speech_enabled.set(True);self.app.toggle_speech()
        self.root.update()
        self.assertIsNone(self.app._pending_reply)
        self.assertEqual(len(self.voice.calls),1)

    def test_pending_response_expires_during_long_playback(self):
        self.app.test_speech()
        self.catalog('Pensar')
        self.clock.advance(15.1)
        self.voice.finish()
        self.pump(lambda:self.app._speech_future is None)
        self.assertIsNone(self.app._pending_reply)
        self.assertEqual(len(self.voice.calls),1)

    def test_late_usb_ack_after_stop_or_mute_cannot_recreate_response(self):
        for mute in (False,True):
            gate=threading.Event()
            self.addCleanup(gate.set)
            original=self.session.apply_action
            def delayed(action):
                gate.wait(2)
                return original(action)
            self.session.apply_action=delayed
            self.app.test_speech()
            selected,_=self.app.catalog_choices['ANIMATION'];selected.set('Celebrar')
            self.app.apply_catalog('ANIMATION')
            self.assertTrue(self.app.busy)
            if mute:
                self.app.speech_enabled.set(False);self.app.toggle_speech()
                self.app.speech_enabled.set(True);self.app.toggle_speech()
            else:
                self.app.stop_speech()
            count=len(self.voice.calls)
            gate.set()
            self.pump(lambda:not self.app.busy and self.app._speech_future is None)
            self.assertEqual(len(self.voice.calls),count)
            self.assertIsNone(self.app._pending_reply)
            self.session.apply_action=original

    def test_mute_while_recognizing_keeps_avatar_control_but_suppresses_old_voice(self):
        self.recognizer.gate=threading.Event()
        self.speak()
        self.pump(lambda:self.app.audio_phase=='recognizing')
        self.app.speech_enabled.set(False);self.app.toggle_speech()
        self.app.speech_enabled.set(True);self.app.toggle_speech()
        self.recognizer.gate.set()
        self.pump(lambda:len(self.session.actions)==1 and not self.app.busy)
        self.assertEqual(self.voice.calls,[])
        self.assertEqual(self.app.values['expression'].get(),'Contento')

    def test_disconnect_cancels_active_reply_and_pending_and_reconnect_does_not_replay(self):
        self.catalog('Pensar')
        self.pump(lambda:len(self.voice.calls)==1)
        self.catalog('Celebrar')
        self.app.disconnect()
        self.pump(lambda:not self.app.busy and self.app._speech_future is None)
        self.assertIsNone(self.app._pending_reply)
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)
        self.assertEqual(len(self.voice.calls),1)
        self.catalog('Reír')
        self.pump(lambda:len(self.voice.calls)==2)
        self.assertEqual(self.voice.calls[-1],'Voy a reír.')

    def test_error_discards_pending_but_new_action_can_speak(self):
        self.app.test_speech()
        self.catalog('Celebrar')
        self.voice.finish(SpeechError('Error de reproducción.'))
        self.pump(lambda:self.app._speech_future is None)
        self.assertIsNone(self.app._pending_reply)
        self.assertTrue(self.app.connected)
        self.assertEqual(self.app.animation_value.get(),'Animación: Celebrar')
        self.assertEqual(len(self.voice.calls),1)
        self.catalog('Pensar')
        self.pump(lambda:len(self.voice.calls)==2)
        self.assertEqual(self.voice.calls[-1],'Voy a pensar.')

    def test_close_discards_active_and_pending_responses(self):
        self.app.test_speech()
        self.catalog('Celebrar')
        self.app.close()
        self.assertTrue(self.voice.closed)
        self.assertIsNone(self.app._pending_reply)
