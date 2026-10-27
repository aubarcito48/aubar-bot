import threading
import unittest
from unittest.mock import Mock

import test_voice_conversation as voice_tests
from test_groq_client import CONFIG,KEY,Connection
from pc.aubar_control.groq_client import GroqClient,GroqService,GroqError,GroqCancelled


class BlockingConnection(Connection):
    def __init__(self):
        super().__init__()
        self.waiting=threading.Event();self.interrupted=threading.Event()
        class Socket:
            def settimeout(inner,seconds):pass
            def shutdown(inner,how):self.interrupted.set()
        self.sock=Socket()

    def read1(self,count):
        self.waiting.set()
        if self.interrupted.wait(3):
            raise OSError(KEY)
        raise TimeoutError


class TransportCancellationTests(unittest.TestCase):
    def test_precancelled_request_never_creates_connection(self):
        event=threading.Event();event.set()
        factory=Mock()
        with self.assertRaises(GroqCancelled):
            GroqClient(factory).complete(CONFIG,'Hola',cancel_event=event)
        factory.assert_not_called()

    def test_cancel_interrupts_read_is_reusable_and_old_cancel_does_not_touch_new_socket(self):
        first=BlockingConnection();second=BlockingConnection();normal=Connection()
        connections=iter((first,second,normal))
        client=GroqClient(lambda *a,**k:next(connections));service=GroqService(client)
        try:
            future=service.submit(CONFIG,'Primera')
            self.assertTrue(first.waiting.wait(1))
            old_event=service._cancel
            service.cancel()
            with self.assertRaises(GroqCancelled) as caught:future.result(1)
            self.assertIsNone(caught.exception.__context__)
            self.assertNotIn(KEY,str(caught.exception))
            self.assertTrue(first.closed)
            future=service.submit(CONFIG,'Segunda')
            self.assertTrue(second.waiting.wait(1))
            client.cancel(old_event)
            self.assertFalse(second.interrupted.is_set())
            service.cancel()
            with self.assertRaises(GroqCancelled):future.result(1)
            self.assertEqual(service.submit(CONFIG,'Tercera').result(1),'Hola, lista para conversar.')
            self.assertEqual(len(first.requests),1)
            self.assertEqual(len(second.requests),1)
        finally:
            service.close()

    def test_cancel_during_connect_prevents_late_post_and_does_not_queue_another_request(self):
        started=threading.Event();release=threading.Event()
        connection=Connection()
        def connect():
            started.set();release.wait(2)
        connection.connect=connect
        service=GroqService(GroqClient(lambda *a,**k:connection))
        try:
            future=service.submit(CONFIG,'Hola');self.assertTrue(started.wait(1))
            service.cancel()
            with self.assertRaises(GroqError):service.submit(CONFIG,'No acumular')
            release.set()
            with self.assertRaises(GroqCancelled):future.result(1)
            self.assertEqual(connection.requests,[])
            self.assertTrue(connection.closed)
        finally:
            release.set();service.close()

    def test_close_interrupts_active_read_and_rejects_new_requests(self):
        connection=BlockingConnection()
        service=GroqService(GroqClient(lambda *a,**k:connection))
        future=service.submit(CONFIG,'Hola');self.assertTrue(connection.waiting.wait(1))
        service.close()
        with self.assertRaises(GroqCancelled):future.result(1)
        self.assertTrue(connection.closed)
        with self.assertRaises(GroqError):service.submit(CONFIG,'Después')


class CooperativeClient:
    def __init__(self):
        self.calls=[];self.started=threading.Event();self.release=threading.Event()
        self.cancel_called=threading.Event()

    def complete(self,config,text,*,cancel_event=None):
        self.calls.append(text);self.started.set()
        while not self.release.wait(.005):
            if cancel_event.is_set():raise GroqCancelled('Consulta cancelada.')
        return 'Respuesta válida.'

    def cancel(self,event):
        self.cancel_called.set()


class CancellationPanelTests(unittest.TestCase):
    pump=voice_tests.VoiceConversationTests.pump
    start_auto=voice_tests.VoiceConversationTests.start_auto
    speak_auto=voice_tests.VoiceConversationTests.speak_auto
    question=voice_tests.VoiceConversationTests.question
    finish_voice=voice_tests.VoiceConversationTests.finish_voice

    def setUp(self):
        voice_tests.VoiceConversationTests.setUp(self)
        self.app.ai_service.close();self.client=CooperativeClient()
        self.app.ai_service=GroqService(self.client)

    def tearDown(self):
        voice_tests.VoiceConversationTests.tearDown(self)

    def send(self,text):
        self.app.ai_input.set(text);self.app.send_ai_message()

    def test_cancel_keeps_completed_history_drops_pending_turn_and_allows_explicit_new_query(self):
        self.client.release.set();self.send('Completada');self.pump(lambda:self.app._ai_future is None)
        self.client.release.clear();self.client.started.clear()
        self.send('Cancelar esta');self.assertTrue(self.client.started.wait(1))
        self.app.cancel_ai_query()
        self.send('No acumular')
        self.pump(lambda:self.app._ai_future is None)
        self.assertTrue(self.client.cancel_called.is_set())
        self.assertEqual(self.app.conversation.turn_count,1)
        self.assertNotIn('Cancelar esta',self.app.conversation.transcript)
        self.assertEqual(len(self.client.calls),2)
        self.client.release.set();self.send('Nueva consulta')
        self.pump(lambda:self.app._ai_future is None)
        self.assertEqual(self.app.conversation.turn_count,2)
        self.assertEqual(len(self.client.calls),3)

    def test_new_query_cannot_overlap_ai_speech_and_cancel_stops_reading(self):
        self.start_auto();self.question();self.client.release.set();self.speak_auto()
        self.pump(lambda:len(self.voice.calls)==1)
        self.send('No superponer');self.app.test_groq()
        self.assertEqual(len(self.client.calls),1)
        self.assertEqual(str(self.app.ai_send_button.cget('state')),'disabled')
        self.app.cancel_ai_query()
        self.pump(lambda:self.app._speech_future is None)
        self.assertEqual(len(self.voice.calls),1)
        self.assertEqual(self.app.conversation.turn_count,1)
        self.clock.advance(.36);self.pump(lambda:self.app.automatic_capture.listening.is_set())

    def test_cancel_during_recognition_never_sends_old_query(self):
        self.start_auto();self.question();self.recognizer.gate=threading.Event()
        self.speak_auto();self.pump(lambda:self.app.audio_phase=='auto_recognizing')
        self.app.cancel_ai_query();self.recognizer.gate.set()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.assertEqual(self.client.calls,[])
        self.assertEqual(self.voice.calls,[])
        self.assertEqual(self.app.conversation.turn_count,0)

    def test_disconnect_cancels_text_request_and_reconnect_does_not_replay(self):
        self.app.connect();self.pump(lambda:self.app.connected and not self.app.busy)
        self.send('Pendiente');self.assertTrue(self.client.started.wait(1))
        self.app.disconnect();self.pump(lambda:not self.app.busy and self.app._ai_future is None)
        self.assertTrue(self.client.cancel_called.is_set())
        self.app.connect();self.pump(lambda:self.app.connected and not self.app.busy)
        self.client.release.set();self.root.update()
        self.assertEqual(len(self.client.calls),1)
        self.assertEqual(self.app.conversation.turn_count,0)
        self.assertEqual(self.session.actions,[])

    def test_reset_and_reload_cancel_transport_and_close_cleans_without_callback(self):
        for operation in (self.app.new_conversation,self.app.reload_groq_configuration):
            self.client.started.clear();self.client.cancel_called.clear()
            self.send('Pendiente');self.assertTrue(self.client.started.wait(1))
            operation();self.pump(lambda:self.app._ai_future is None)
            self.assertTrue(self.client.cancel_called.is_set())
            self.assertEqual(self.app.conversation.turn_count,0)
        self.client.started.clear();self.client.cancel_called.clear()
        self.send('Cerrar');self.assertTrue(self.client.started.wait(1))
        self.app.close()
        self.assertTrue(self.client.cancel_called.is_set())
        self.assertIsNone(self.app._ai_future)
