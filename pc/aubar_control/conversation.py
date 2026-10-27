"""Session-only conversation; commit complete successful turns atomically."""
from dataclasses import dataclass, field

SYSTEM_PROMPT=(
    'Sos Aubar, una asistente de escritorio cercana, curiosa y respetuosa. '
    'Respondé en español con voseo natural, sin exagerar los modismos. '
    'Preferí entre una y tres frases breves, claras y cómodas de escuchar; '
    'evitá listas largas, tablas y formato Markdown salvo que te lo pidan. '
    'Usá el contexto disponible y no inventes recuerdos ni datos personales. '
    'Si falta información, reconocelo y pedí una aclaración breve. '
    'Podés proponer una expresión o animación para acompañar tu respuesta; '
    'la aplicación debe validarla y aplicarla. No afirmes haber ejecutado '
    'comandos, consultado internet o usado sensores sin confirmación. '
    'No pidas claves de API ni contraseñas. Presentate como Aubar cuando corresponda.'
)


@dataclass(frozen=True)
class Message:
    role: str
    content: str=field(repr=False)


@dataclass(frozen=True)
class ConversationRequest:
    revision: int
    question: str=field(repr=False)
    messages: tuple[Message,...]=field(repr=False)


class Conversation:
    MAX_TURNS=6
    MAX_CHARACTERS=12000

    def __init__(self):
        self._turns=[]
        self.revision=0

    @property
    def turn_count(self):
        return len(self._turns)

    @property
    def character_count(self):
        return sum(len(question)+len(answer) for question,answer in self._turns)

    @property
    def transcript(self):
        return '\n\n'.join(f'Vos: {question}\nAubar: {answer}' for question,answer in self._turns)

    def prepare(self,text):
        if not isinstance(text,str) or not text.strip() or len(text)>1000 or '\x00' in text:
            raise ValueError('El mensaje debe tener entre 1 y 1000 caracteres y no contener NUL.')
        messages=[Message('system',SYSTEM_PROMPT)]
        for question,answer in self._turns:
            messages.extend((Message('user',question),Message('assistant',answer)))
        question=text.strip()
        messages.append(Message('user',question))
        return ConversationRequest(self.revision,question,tuple(messages))

    def commit(self,request,answer):
        if request.revision!=self.revision:
            return False
        if not isinstance(answer,str) or not answer.strip() or len(answer)>2000:
            raise ValueError('La respuesta no tiene un formato válido.')
        self._turns.append((request.question,answer.strip()))
        while len(self._turns)>self.MAX_TURNS or self.character_count>self.MAX_CHARACTERS:
            self._turns.pop(0)
        self.revision+=1
        return True

    def reset(self):
        self._turns.clear()
        self.revision+=1
