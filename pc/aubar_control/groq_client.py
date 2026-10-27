"""Bounded Groq text requests over verified HTTPS, isolated from the Tk thread."""
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import socket
from threading import Lock
import time
from .conversation import ConversationRequest, Message, SYSTEM_PROMPT
from .ai_avatar import AvatarReply,AVATAR_SCHEMA,AVATAR_INSTRUCTIONS,parse_avatar_reply,normalize_reply

HOST='api.groq.com'
ENDPOINT='/openai/v1/chat/completions'
TEST_QUERY='Respondé en una frase breve: ¿estás lista para conversar?'
MAX_RESPONSE_BYTES=262144


class GroqError(Exception):
    """Fixed, credential-free message suitable for display in the panel."""


def status_message(status):
    if status==401:
        return 'Groq rechazó la clave. Revisá GROQ_API_KEY en .env y recargá la configuración.'
    if status==403:
        return 'Groq no autorizó esta solicitud. Revisá los permisos de la cuenta y del modelo.'
    if status==404:
        return 'El modelo no está disponible para esta cuenta. Revisá GROQ_MODEL y recargá la configuración.'
    if status in (413,422,400):
        return 'Groq rechazó la consulta o su configuración. Revisá el modelo e intentá una prueba nueva.'
    if status==429:
        return 'Se alcanzó un límite de Groq. Esperá antes de iniciar otra prueba y revisá los límites de tu cuenta.'
    if status>=500:
        return 'Groq no está disponible en este momento. Probá nuevamente más tarde.'
    return 'Groq no pudo completar la solicitud. Revisá la conexión y la configuración.'


class GroqClient:
    def __init__(self,connection_factory=http.client.HTTPSConnection):
        self.connection_factory=connection_factory

    def complete(self,config,text):
        if isinstance(text,ConversationRequest):
            messages=text.messages
        else:
            if not isinstance(text,str) or not text.strip() or len(text)>1000:
                raise GroqError('La consulta debe contener entre 1 y 1000 caracteres.')
            messages=(Message('system',SYSTEM_PROMPT),Message('user',text))
        payload={
            'model':config.model,
            'messages':[{'role':message.role,'content':message.content.replace(config.api_key,'[credencial oculta]')}
                        for message in messages],
            'max_completion_tokens':512,
            'stream':False,
        }
        if isinstance(text,ConversationRequest):
            payload['messages'][0]['content']+='\n'+AVATAR_INSTRUCTIONS
            payload['response_format']=(
                {'type':'json_schema','json_schema':{'name':'aubar_reply','strict':True,'schema':AVATAR_SCHEMA}}
                if config.model in ('openai/gpt-oss-20b','openai/gpt-oss-120b','qwen/qwen3.8-27b','meta-models/muse-spark-open')
                else {'type':'json_object'})
        if config.model in ('openai/gpt-oss-20b','openai/gpt-oss-120b'):
            payload.update(reasoning_effort='low',include_reasoning=False)
        connection=None
        error=None
        answer=None
        deadline=time.monotonic()+config.timeout_seconds

        def remaining():
            seconds=deadline-time.monotonic()
            if seconds<=0:
                raise TimeoutError
            if connection.sock is not None:
                connection.sock.settimeout(seconds)

        try:
            connection=self.connection_factory(HOST,timeout=config.timeout_seconds)
            connection.connect()
            remaining()
            connection.request('POST',ENDPOINT,body=json.dumps(payload,ensure_ascii=False).encode('utf-8'),
                headers={'Authorization':'Bearer '+config.api_key,'Content-Type':'application/json',
                         'Accept':'application/json','User-Agent':'AubarBot/1.0'})
            remaining()
            response=connection.getresponse()
            if response.status!=200:
                # Never expose or log a remote error body, headers or request.
                error=status_message(response.status)
            else:
                data=bytearray()
                while True:
                    remaining()
                    chunk=response.read1(min(65536,MAX_RESPONSE_BYTES+1-len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data)>MAX_RESPONSE_BYTES:
                        raise ValueError
                result=json.loads(data)
                choice=result['choices'][0]
                content=choice['message']['content']
                if choice.get('finish_reason')!='stop' or not isinstance(content,str) or not content.strip():
                    error='Groq devolvió una respuesta vacía, incompleta o demasiado larga. Podés iniciar otra prueba.'
                elif isinstance(text,ConversationRequest):
                    answer=parse_avatar_reply(content.replace(config.api_key,'[credencial oculta]'))
                elif len(content)>2000:
                    error='Groq devolvió una respuesta demasiado larga. Podés iniciar otra prueba.'
                else:
                    answer=content.strip().replace(config.api_key,'[credencial oculta]')
        except (TimeoutError,socket.timeout):
            error='La consulta a Groq agotó el tiempo de espera. Podés iniciar una prueba nueva.'
        except (OSError,http.client.HTTPException):
            error='No se pudo conectar con Groq. Revisá internet y probá nuevamente.'
        except Exception:
            error='Groq devolvió una respuesta que no se pudo interpretar. Podés iniciar otra prueba.'
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
        # Raise outside the handler: no raw transport exception in traceback context.
        if error is not None:
            raise GroqError(error)
        return answer


class GroqService:
    """At most one request, no automatic retries or queued conversations."""
    def __init__(self,client=None):
        self.client=client or GroqClient()
        self._executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='aubar-groq')
        self._lock=Lock()
        self._closed=False
        self._future=None

    @property
    def busy(self):
        with self._lock:
            return self._future is not None and not self._future.done()

    def submit(self,config,text):
        with self._lock:
            if self._closed:
                raise GroqError('El servicio de IA está cerrado.')
            if self._future is not None and not self._future.done():
                raise GroqError('Ya hay una consulta a Groq en curso. Esperá a que termine.')
            self._future=self._executor.submit(self._complete,config,text)
            return self._future

    def _complete(self,config,text):
        error=None
        try:
            answer=self.client.complete(config,text)
            if isinstance(text,ConversationRequest):
                reply=normalize_reply(answer)
                return AvatarReply(reply.text.replace(config.api_key,'[credencial oculta]'),reply.action,reply.fallback)
            if not isinstance(answer,str) or not answer.strip() or len(answer)>2000:
                error='La respuesta de Groq no tiene un formato válido.'
            else:
                return answer.replace(config.api_key,'[credencial oculta]')
        except GroqError as exc:
            error=str(exc).replace(config.api_key,'[credencial oculta]')
        except Exception:
            error='No se pudo completar la consulta a Groq. Podés iniciar una prueba nueva.'
        raise GroqError(error)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed=True
        # In-flight I/O is bounded by the configured timeout and closes in finally.
        self._executor.shutdown(wait=False,cancel_futures=True)
