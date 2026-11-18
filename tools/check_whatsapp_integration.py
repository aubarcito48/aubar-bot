"""Python -> native Node bridge smoke with a synthetic transport; never WhatsApp."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pc.aubar_control.config import GroqConfig
from pc.aubar_control.conversation import Conversation
from pc.aubar_control.groq_client import GroqClient
from pc.aubar_control.whatsapp_control import WhatsAppControl


def main():
    fixture=ROOT/'integrations'/'whatsapp-bot'/'scripts'/'desktop-smoke.js'
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    process=subprocess.Popen(['node',str(fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,**options)
    try:
        port=json.loads(process.stdout.readline())['port']
        config=GroqConfig('synthetic-not-used',timeout_seconds=5,
            whatsapp_control_url=f'http://127.0.0.1:{port}/control/',whatsapp_control_token='c'*64)
        control=WhatsAppControl()
        cursor,events,missed=control.events(config,'',Event())
        assert events==[] and not missed
        _,events,_=control.events(config,cursor,Event())
        assert len(events)==1 and events[0]['text']=='Mensaje simulado para Aubar.'
        def no_groq(*args,**kwargs):
            raise AssertionError('This smoke must not call Groq')
        client=GroqClient(no_groq,whatsapp=control)
        recent=client.complete(config,Conversation().prepare('mostrá mis mensajes de WhatsApp'))
        assert 'Mensaje simulado para Aubar.' in recent.text
        request=Conversation().prepare('enviá un WhatsApp a +12345678901: Texto de prueba local.')
        reply=client.complete(config,request)
        assert 'aceptó' in reply.text
        client.complete(config,request)  # Same UUID must not send twice.
        connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
        try:
            connection.request('GET','/fixture/result')
            assert json.loads(connection.getresponse().read(1024))['sends']==1
        finally:
            connection.close()
        print('OK: Python/Node, token, notificación, envío literal e idempotencia; 0 llamadas a Groq o WhatsApp.')
    finally:
        process.terminate()
        try: process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate(timeout=5)


if __name__=='__main__':
    main()
