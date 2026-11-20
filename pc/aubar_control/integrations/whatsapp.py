"""Explicit owner commands and private inbox. No LLM output can invoke a send."""
from dataclasses import dataclass,field
import http.client
import json
import re
import socket
from threading import Lock
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from urllib.parse import urlsplit,quote

from ..config.settings import validate_control_url


class WhatsAppError(Exception):
    pass


@dataclass(frozen=True)
class Outgoing:
    recipient: str=field(repr=False)
    text: str=field(repr=False)


def parse_send(text):
    # Intentionally anchored: quotations, received messages and hypothetical
    # requests cannot become an outbound operation.
    prefix=r'(?:aubar[,\s]+)?(?:envi[aá]|env[ií]a|enviar|envi[aá]le|mand[aá]|mandale|mand[aá]le|mandar|send)\s+'
    intent=prefix+r'.*\b(?:whatsapp|wsp|wpp)\b'
    if not re.match(intent,text.strip(),flags=re.I):
        return None
    match=re.fullmatch(prefix+r'(?:un\s+)?(?:mensaje\s+(?:por\s+)?)?(?:whatsapp|wsp|wpp)\s+'
        r'(?:a|al|to)\s+(\+?[\d -]{8,25})\s*(?::|\s+que\s+diga\s+)\s*(.+)',
        text.strip(),flags=re.I|re.S)
    if not match:
        raise WhatsAppError('Para enviar, indicá el número internacional y el texto: '
            'enviá un WhatsApp a +549XXXXXXXXXX: Hola.')
    recipient=re.sub(r'[ +\-]','',match[1])
    message=match[2].strip()
    if (not re.fullmatch(r'[0-9]{8,15}',recipient) or not message or len(message)>2000
        or any(ord(c)<32 and c not in '\n\r\t' for c in message)):
        raise WhatsAppError('Revisá el número internacional y el texto del mensaje.')
    return Outgoing(recipient,message)


def is_inbox_query(text):
    return bool(re.fullmatch(r'(?:aubar[,\s]+)?(?:consult[aá]|mostr[aá]|lee|le[eé]|mostrar|ver)\s+'
        r'(?:(?:mis|los)\s+)?mensajes(?:\s+recientes)?\s+(?:de|en|por)\s+(?:whatsapp|wsp|wpp)[?.!]*',
        text.strip(),flags=re.I))


class WhatsAppControl:
    def __init__(self,*,http_factory=http.client.HTTPConnection,https_factory=http.client.HTTPSConnection):
        self._http=http_factory
        self._https=https_factory
        self._lock=Lock()
        self._active=None

    def cancel(self,cancel):
        with self._lock:
            active=self._active
            sock=active[1].sock if active is not None and active[0] is cancel else None
        if sock is not None:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass

    def _request(self,config,path,method,cancel,body=None):
        if not config.whatsapp_control_url or not config.whatsapp_control_token:
            raise WhatsAppError('El control local de WhatsApp todavía no está configurado.')
        validate_control_url(config.whatsapp_control_url)
        if cancel.is_set():
            raise WhatsAppError('Operación de WhatsApp cancelada antes de transmitir.')
        parsed=urlsplit(config.whatsapp_control_url)
        deadline=perf_counter()+min(10,config.timeout_seconds)
        connection=None
        transmitted=False
        try:
            factory=self._https if parsed.scheme=='https' else self._http
            connection=factory(parsed.hostname,port=parsed.port,timeout=min(4,config.timeout_seconds))
            with self._lock: self._active=(cancel,connection)
            connection.connect()
            if cancel.is_set():
                raise WhatsAppError('Operación de WhatsApp cancelada antes de transmitir.')
            def check_budget():
                if cancel.is_set(): raise TimeoutError
                remaining=deadline-perf_counter()
                if remaining<=0: raise TimeoutError
                if connection.sock is not None: connection.sock.settimeout(remaining)
            check_budget()
            headers={'Authorization':'Bearer '+config.whatsapp_control_token,'Accept':'application/json'}
            payload=None
            if body is not None:
                payload=json.dumps(body,ensure_ascii=False).encode()
                headers['Content-Type']='application/json'
            transmitted=True
            connection.request(method,parsed.path+path,body=payload,headers=headers)
            check_budget()
            response=connection.getresponse()
            if response.status not in (200,202):
                messages={403:'El token o el destinatario no está autorizado. Revisá el control local y TEST_CONTACTS.',
                    429:'WhatsApp está ocupado. No se inició otro envío.',503:'El bot de WhatsApp no está conectado.',
                    409:'El identificador del envío ya se utilizó con otro contenido.'}
                raise WhatsAppError(messages.get(response.status,'El puente de WhatsApp rechazó la operación.'))
            if response.getheader('Content-Type','').split(';')[0].lower().strip()!='application/json':
                raise ValueError
            data=bytearray()
            while True:
                check_budget()
                chunk=response.read1(min(16384,65537-len(data)))
                if not chunk: break
                data.extend(chunk)
                if len(data)>65536: raise ValueError
            value=json.loads(data)
            if not isinstance(value,dict): raise ValueError
            return value
        except WhatsAppError:
            raise
        except Exception:
            if method=='POST' and transmitted:
                raise WhatsAppError('No pude confirmar el envío. Puede haberse transmitido: '
                    'revisá WhatsApp antes de repetirlo; no lo reintenté automáticamente.') from None
            raise WhatsAppError('No pude conectar con el control local de WhatsApp.') from None
        finally:
            if connection is not None:
                try: connection.close()
                except Exception: pass
            with self._lock:
                if self._active is not None and self._active[1] is connection: self._active=None

    def send(self,config,outgoing,request_id,cancel):
        value=self._request(config,'send','POST',cancel,
            {'recipient':outgoing.recipient,'text':outgoing.text,'request_id':request_id})
        if value.get('request_id')!=request_id or value.get('status') not in ('accepted','unknown'):
            raise WhatsAppError('El envío no pudo confirmarse. Revisá WhatsApp antes de repetirlo.')
        if value['status']=='unknown':
            return 'El envío quedó sin confirmar. Revisá WhatsApp antes de repetirlo; no lo reenvié.'
        return 'WhatsApp aceptó el envío al número terminado en '+outgoing.recipient[-4:]+'. Todavía no confirma lectura ni entrega.'

    def events(self,config,cursor,cancel):
        path='events'+('?after='+quote(cursor,safe='') if cursor else '')
        value=self._request(config,path,'GET',cancel)
        if (not isinstance(value.get('cursor'),str) or not re.fullmatch(r'[a-f0-9-]{36}:\d{1,12}',value['cursor'])
            or type(value.get('missed')) is not bool or not isinstance(value.get('events'),list) or len(value['events'])>20):
            raise WhatsAppError('La bandeja de WhatsApp devolvió un formato inválido.')
        return value['cursor'],self._messages(value['events']),value['missed']

    @staticmethod
    def _messages(items):
        if not isinstance(items,list) or len(items)>20:
            raise WhatsAppError('La bandeja de WhatsApp devolvió un formato inválido.')
        result=[]
        for item in items:
            if (not isinstance(item,dict) or not isinstance(item.get('sender'),str)
                or not re.fullmatch(r'[0-9]{8,15}',item['sender']) or not isinstance(item.get('name'),str)
                or len(item['name'])>80 or not isinstance(item.get('text'),str) or not item['text'].strip()
                or len(item['text'])>2000 or type(item.get('sequence')) is not int):
                raise WhatsAppError('La bandeja de WhatsApp devolvió un mensaje inválido.')
            result.append({k:item[k] for k in ('sender','name','text','sequence')})
        return result

    def recent(self,config,cancel):
        value=self._request(config,'inbox','GET',cancel)
        if type(value.get('partial')) is not bool:
            raise WhatsAppError('La bandeja de WhatsApp devolvió un formato inválido.')
        events=self._messages(value.get('events'))
        if not events:
            return 'El puente no conserva mensajes recientes de los contactos habilitados. Esto no consulta el historial completo de WhatsApp.'
        lines=['Estos son los últimos mensajes que conserva el puente (hasta cinco minutos); no es el historial completo de WhatsApp.']
        for event in events[-3:]:
            name=event['name'] or 'Número terminado en '+event['sender'][-4:]
            text=event['text']
            if len(text)>450: text=text[:450]+' [texto recortado]'
            lines.append(name+': '+text)
        if len(events)>3 or value['partial']:
            lines.append('Mostré solo los últimos tres; revisá WhatsApp para el resto.')
        return '\n\n'.join(lines)


class InboxPoller:
    """One bounded poll outside Tk; reload/close discard stale events."""
    def __init__(self,client=None,*,clock=perf_counter):
        self.client=client if client is not None else WhatsAppControl()
        self._executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='aubar-whatsapp')
        self._clock=clock
        self._config=None
        self._epoch=0
        self._future=None
        self._future_epoch=None
        self._cancel=Event()
        self._cursor=''
        self._next=0
        self._closed=False

    def configure(self,config):
        self._cancel.set()
        self.client.cancel(self._cancel)
        self._epoch+=1
        self._config=config
        self._cursor=''
        self._cancel=Event()
        self._next=0

    def tick(self):
        if self._closed:
            return None
        result=None
        if self._future is not None and self._future.done():
            try:
                cursor,events,missed=self._future.result()
                if self._future_epoch==self._epoch:
                    self._cursor=cursor
                    result=('connected',events,missed)
            except Exception:
                if self._future_epoch==self._epoch:
                    result=('unavailable',[],False)
            self._future=None
            self._next=self._clock()+(10 if result and result[0]=='unavailable' else 3)
        if (self._future is None and self._config is not None and self._config.whatsapp_control_url
            and self._config.whatsapp_control_token and self._clock()>=self._next):
            self._future_epoch=self._epoch
            self._future=self._executor.submit(self.client.events,self._config,self._cursor,self._cancel)
        return result

    def close(self):
        self._closed=True
        self.configure(None)
        self._executor.shutdown(wait=False,cancel_futures=True)
