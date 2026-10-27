import json
import threading
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_app
from pc.aubar_control.config import GroqConfig, load_groq_config
from pc.aubar_control.groq_client import (
    ENDPOINT, HOST, MAX_RESPONSE_BYTES, GroqClient, GroqError, GroqService,
)

KEY='synthetic-groq-test-token'
CONFIG=GroqConfig(KEY,'openai/gpt-oss-20b',2)


def completion(content='Hola, lista para conversar.',reason='stop'):
    return json.dumps({'choices':[{'message':{'content':content,'reasoning':'not displayed'},'finish_reason':reason}]}).encode()


class Connection:
    def __init__(self,data=None,status=200,error=None):
        self.data=bytearray(completion() if data is None else data)
        self.status=status;self.error=error;self.closed=False;self.requests=[];self.reads=0
        self.sock=SimpleNamespace(settimeout=lambda seconds:None)

    def connect(self):
        if self.error:
            raise self.error

    def request(self,*args,**kwargs):
        self.requests.append((args,kwargs))

    def getresponse(self):
        return self

    def read1(self,count):
        self.reads+=1
        chunk=bytes(self.data[:count]);del self.data[:count]
        return chunk

    def close(self):
        self.closed=True


class GroqClientTests(unittest.TestCase):
    def test_https_request_uses_settings_and_sends_credential_only_in_header(self):
        connection=Connection()
        calls=[]
        def factory(host,**kwargs):
            calls.append((host,kwargs));return connection
        text=GroqClient(factory).complete(CONFIG,'¿Cómo estás?')
        self.assertEqual(text,'Hola, lista para conversar.')
        self.assertEqual(calls,[(HOST,{'timeout':2})])
        self.assertTrue(connection.closed)
        self.assertEqual(len(connection.requests),1)
        args,kwargs=connection.requests[0]
        self.assertEqual(args,('POST',ENDPOINT))
        self.assertEqual(kwargs['headers']['Authorization'],'Bearer '+KEY)
        payload=json.loads(kwargs['body'])
        self.assertEqual(payload['model'],CONFIG.model)
        self.assertEqual(payload['messages'][-1]['content'],'¿Cómo estás?')
        self.assertFalse(payload['include_reasoning'])
        self.assertNotIn(KEY,kwargs['body'].decode())

    def test_http_errors_use_fixed_messages_never_read_remote_body_or_retry(self):
        for status,expected in ((401,'clave'),(403,'autorizó'),(404,'modelo'),
                                (429,'límite'),(500,'disponible'),(302,'solicitud')):
            with self.subTest(status=status):
                connection=Connection(KEY.encode(),status)
                with self.assertRaisesRegex(GroqError,expected) as caught:
                    GroqClient(lambda *a,**k:connection).complete(CONFIG,'Hola')
                self.assertNotIn(KEY,str(caught.exception))
                self.assertEqual(connection.reads,0)
                self.assertEqual(len(connection.requests),1)
                self.assertTrue(connection.closed)

    def test_transport_failures_and_timeouts_leave_no_raw_exception_context(self):
        for error,expected in ((OSError(KEY),'internet'),(TimeoutError(KEY),'tiempo')):
            connection=Connection(error=error)
            try:
                GroqClient(lambda *a,**k:connection).complete(CONFIG,'Hola')
                self.fail('Expected a safe error')
            except GroqError as exc:
                self.assertIn(expected,str(exc))
                self.assertIsNone(exc.__context__)
                self.assertNotIn(KEY,traceback.format_exc())
            self.assertTrue(connection.closed)

    def test_invalid_or_incomplete_responses_are_not_reported_as_success(self):
        for data in (b'not JSON',b'{}',completion(''),completion('Parcial','length'),
                     completion('x'*2001),b'x'*(MAX_RESPONSE_BYTES+1)):
            connection=Connection(data)
            with self.assertRaises(GroqError):
                GroqClient(lambda *a,**k:connection).complete(CONFIG,'Hola')
            self.assertTrue(connection.closed)

    def test_total_deadline_is_checked_before_sending_after_connect(self):
        connection=Connection()
        with patch('pc.aubar_control.groq_client.time.monotonic',side_effect=[1,4]):
            with self.assertRaisesRegex(GroqError,'tiempo'):
                GroqClient(lambda *a,**k:connection).complete(CONFIG,'Hola')
        self.assertEqual(connection.requests,[])
        self.assertTrue(connection.closed)

    def test_response_redacts_credential_and_other_models_do_not_get_reasoning_options(self):
        connection=Connection(completion('Texto '+KEY))
        text=GroqClient(lambda *a,**k:connection).complete(GroqConfig(KEY,'other/model',2),'Hola')
        self.assertEqual(text,'Texto [credencial oculta]')
        payload=json.loads(connection.requests[0][1]['body'])
        self.assertNotIn('include_reasoning',payload)


class ControlledClient:
    def __init__(self):
        self.started=threading.Event();self.release=threading.Event()
        self.error=None;self.calls=[]

    def complete(self,config,text,*,cancel_event=None):
        self.calls.append(text);self.started.set();self.release.wait(2)
        if self.error:
            raise self.error
        return 'Respuesta de prueba.'


class GroqServiceTests(unittest.TestCase):
    def test_one_async_request_no_queue_error_recovery_and_close(self):
        client=ControlledClient();service=GroqService(client)
        try:
            future=service.submit(CONFIG,'Hola')
            self.assertTrue(client.started.wait(1))
            self.assertFalse(future.done())
            with self.assertRaisesRegex(GroqError,'curso'):
                service.submit(CONFIG,'No acumular')
            client.error=OSError(KEY);client.release.set()
            with self.assertRaises(GroqError) as caught:
                future.result(1)
            self.assertNotIn(KEY,str(caught.exception))
            self.assertIsNone(caught.exception.__context__)
            client.error=None
            self.assertEqual(service.submit(CONFIG,'Otra').result(1),'Respuesta de prueba.')
            self.assertEqual(client.calls,['Hola','Otra'])
        finally:
            client.release.set();service.close()
        with self.assertRaisesRegex(GroqError,'cerrado'):
            service.submit(CONFIG,'Cerrado')
        service.close()


class GroqPanelTests(unittest.TestCase):
    pump=test_app.AppTests.pump

    def setUp(self):
        test_app.AppTests.setUp(self)
        self.app.ai_service.close()
        self.client=ControlledClient()
        self.app.ai_service=GroqService(self.client)
        self.app.config_loader=lambda:load_groq_config(None,{'GROQ_API_KEY':KEY})
        self.app.reload_groq_configuration()

    def tearDown(self):
        self.client.release.set()
        test_app.AppTests.tearDown(self)

    def test_pending_request_keeps_tk_usb_and_voice_available_without_duplicate_calls(self):
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)
        self.app.test_groq()
        self.assertTrue(self.client.started.wait(1))
        self.app.test_groq()
        self.assertEqual(len(self.client.calls),1)
        heartbeat=[];self.root.after(5,lambda:heartbeat.append(True))
        self.app.refresh_status()
        self.pump(lambda:self.app.connected and not self.app.busy and heartbeat)
        self.assertFalse(self.app._ai_future.done())
        self.app.test_speech()
        self.pump(lambda:len(self.app.speech.calls)==1)
        self.client.release.set()
        self.pump(lambda:self.app._ai_future is None)
        self.assertIn('Respuesta de prueba',self.app.ai_response.get('1.0','end'))
        self.assertIn('comprobada',self.app.ai_message.get())
        self.assertIn('verificada con Groq',self.app.groq_config_message.get())
        self.assertEqual(str(self.app.ai_test_button.cget('state')),'normal')

    def test_error_does_not_expose_key_or_disconnect_usb_and_allows_new_test(self):
        self.app.connect();self.pump(lambda:self.app.connected and not self.app.busy)
        self.client.error=OSError(KEY);self.client.release.set()
        self.app.test_groq();self.pump(lambda:self.app._ai_future is None)
        self.assertTrue(self.app.connected)
        self.assertNotIn(KEY,self.app.ai_message.get()+self.app.ai_response.get('1.0','end')+self.app.activity.get('1.0','end'))
        self.client.error=None
        self.app.test_groq();self.pump(lambda:self.app._ai_future is None)
        self.assertIn('comprobada',self.app.ai_message.get())

    def test_reload_discards_previous_result_and_close_does_not_wait_for_network(self):
        self.app.test_groq();self.assertTrue(self.client.started.wait(1))
        self.app.reload_groq_configuration()
        self.client.release.set()
        self.pump(lambda:self.app._ai_future is None)
        self.assertEqual(self.app.ai_response.get('1.0','end').strip(),'')
        self.client.release.clear();self.client.started.clear()
        self.app.test_groq();self.assertTrue(self.client.started.wait(1))
        self.app.close()
        self.assertIsNone(self.app._ai_future)
        self.assertFalse(self.client.release.is_set())
