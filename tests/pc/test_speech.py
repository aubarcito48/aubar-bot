import json
import os
import subprocess
import threading
import time
import unittest

import test_app
from pc.aubar_control.speech import SpeechEngine, SpeechError, SpeechVoice, SapiBackend

VOICE={'id':'test-es','name':'Voz de prueba','language':'es-MX'}


class FakeSpeechBackend:
    def __init__(self):
        self.started=threading.Event()
        self.release=threading.Event()
        self.closed=False
        self.calls=[]

    def speak(self,text,volume,rate):
        self.calls.append((text,volume,rate))
        self.started.set()
        self.release.wait(2)
        if self.closed:
            raise SpeechError('Reproducción cancelada.')
        return SpeechVoice(**VOICE)

    def close(self):
        self.closed=True
        self.release.set()


class SpeechEngineTests(unittest.TestCase):
    def test_text_from_any_source_is_async_and_a_second_utterance_is_not_queued(self):
        backend=FakeSpeechBackend()
        engine=SpeechEngine(backend)
        try:
            before=time.monotonic()
            future=engine.speak('Una respuesta libre de la futura IA.',volume=80,rate=1)
            self.assertLess(time.monotonic()-before,.2)
            self.assertTrue(backend.started.wait(1))
            self.assertFalse(future.done())
            with self.assertRaisesRegex(SpeechError,'ocupado'):
                engine.speak('No debe acumularse.')
            backend.release.set()
            self.assertEqual(future.result(1).language,'es-MX')
            self.assertEqual(backend.calls,[('Una respuesta libre de la futura IA.',80,1)])
            self.assertFalse(engine.busy)
        finally:
            engine.close()

    def test_invalid_input_never_starts_output(self):
        backend=FakeSpeechBackend()
        engine=SpeechEngine(backend)
        try:
            for text in ('','   ','x'*2001,'hola\x00resto',None):
                with self.assertRaises(SpeechError):
                    engine.speak(text)
            for options in ({'volume':101},{'volume':-1},{'rate':11},{'rate':True}):
                with self.assertRaises(SpeechError):
                    engine.speak('Hola',**options)
            self.assertFalse(backend.started.is_set())
        finally:
            engine.close()

    def test_close_stops_active_output_and_rejects_new_requests(self):
        backend=FakeSpeechBackend()
        engine=SpeechEngine(backend)
        future=engine.speak('Una frase larga.')
        self.assertTrue(backend.started.wait(1))
        engine.close()
        with self.assertRaises(SpeechError):
            future.result(1)
        with self.assertRaisesRegex(SpeechError,'cerrado'):
            engine.speak('No reproducir.')
        engine.close()


class FakeProcess:
    def __init__(self,response=None,returncode=0,timeout=False,gate=None):
        self.response=response if response is not None else {'ok':True,'voice':VOICE,'voices':[VOICE]}
        self.returncode=returncode
        self.timeout=timeout
        self.gate=gate
        self.started=threading.Event()
        self.killed=False
        self.input=None

    def communicate(self,input=None,timeout=None):
        if input is not None:
            self.input=input
        self.started.set()
        if self.timeout and not self.killed:
            raise subprocess.TimeoutExpired('speech',timeout)
        if self.gate:
            self.gate.wait(2)
        return (self.response if isinstance(self.response,str) else json.dumps(self.response)),''

    def poll(self):
        return None if self.gate and not self.gate.is_set() else self.returncode

    def terminate(self):
        self.returncode=-1
        if self.gate:
            self.gate.set()

    def kill(self):
        self.killed=True
        self.returncode=-9


@unittest.skipUnless(os.name=='nt','Windows SAPI subprocess adapter')
class SapiBackendTests(unittest.TestCase):
    def test_arbitrary_text_is_only_json_stdin_and_helper_window_is_hidden(self):
        process=FakeProcess()
        calls=[]
        def factory(arguments,**options):
            calls.append((arguments,options))
            return process
        engine=SpeechEngine(SapiBackend(factory))
        text='<voice>Hola</voice> $(Get-Date); comillas " y tildes: canción.'
        try:
            self.assertEqual(engine.speak(text).result(1).language,'es-MX')
            arguments,options=calls[0]
            self.assertNotIn(text,' '.join(arguments))
            self.assertEqual(json.loads(process.input)['text'],text)
            self.assertIn('-File',arguments)
            self.assertEqual(options['creationflags'],subprocess.CREATE_NO_WINDOW)
            self.assertNotIn('shell',options)
        finally:
            engine.close()

    def test_no_spanish_voice_is_actionable_and_does_not_fall_back_to_english(self):
        process=FakeProcess({'ok':False,'code':'NO_SPANISH_VOICE'},returncode=1)
        engine=SpeechEngine(SapiBackend(lambda *args,**kwargs:process))
        try:
            with self.assertRaisesRegex(SpeechError,'español'):
                engine.voices().result(1)
            self.assertFalse(engine.busy)
        finally:
            engine.close()

    def test_voice_query_does_not_request_playback(self):
        process=FakeProcess()
        engine=SpeechEngine(SapiBackend(lambda *args,**kwargs:process))
        try:
            self.assertEqual(engine.voices().result(1),[SpeechVoice(**VOICE)])
            self.assertEqual(json.loads(process.input),{'action':'voices'})
        finally:
            engine.close()

    def test_timeout_kills_helper_and_reports_an_error(self):
        process=FakeProcess(timeout=True)
        engine=SpeechEngine(SapiBackend(lambda *args,**kwargs:process))
        try:
            with self.assertRaisesRegex(SpeechError,'tiempo'):
                engine.speak('Hola').result(1)
            self.assertTrue(process.killed)
            self.assertFalse(engine.busy)
        finally:
            engine.close()

    def test_invalid_response_does_not_report_success(self):
        for response in ('not JSON',[],{'ok':True,'voice':{'language':'en-US'}}):
            process=FakeProcess(response)
            engine=SpeechEngine(SapiBackend(lambda *args,**kwargs:process))
            try:
                with self.assertRaises(SpeechError):
                    engine.speak('Hola').result(1)
            finally:
                engine.close()

    def test_close_terminates_the_actual_process_adapter_without_waiting_for_speech(self):
        process=FakeProcess(gate=threading.Event())
        engine=SpeechEngine(SapiBackend(lambda *args,**kwargs:process))
        future=engine.speak('Hola')
        self.assertTrue(process.started.wait(1))
        engine.close()
        with self.assertRaises(SpeechError):
            future.result(1)
        self.assertTrue(process.gate.is_set())


class SpeechAppTests(unittest.TestCase):
    setUp=test_app.AppTests.setUp
    tearDown=test_app.AppTests.tearDown
    pump=test_app.AppTests.pump

    def test_panel_and_usb_keep_responding_while_voice_is_active(self):
        self.app.speech.close()
        backend=FakeSpeechBackend()
        self.app.speech=SpeechEngine(backend)
        future=self.app.speech.speak('Hola')
        self.assertTrue(backend.started.wait(1))
        heartbeat=[]
        self.root.after(5,lambda:heartbeat.append(True))
        self.app.connect()
        self.pump(lambda:bool(heartbeat) and self.app.connected and not self.app.busy)
        self.assertFalse(future.done())
        self.app.refresh_status()
        self.pump(lambda:not self.app.busy)
        self.assertEqual(self.app.values['expression'].get(),'Enojado')
        backend.release.set()
        self.assertEqual(future.result(1).language,'es-MX')

    def test_closing_panel_cancels_output(self):
        self.app.speech.close()
        backend=FakeSpeechBackend()
        self.app.speech=SpeechEngine(backend)
        future=self.app.speech.speak('Hola')
        self.assertTrue(backend.started.wait(1))
        self.app.close()
        with self.assertRaises(SpeechError):
            future.result(1)
        self.assertTrue(backend.closed)
