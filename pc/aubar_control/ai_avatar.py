"""Validated visual feedback. Model output never becomes arbitrary USB text."""
from dataclasses import dataclass,field
import json
import math

from .catalog import EXPRESSIONS,ANIMATIONS
from .voice_commands import VoiceAction


def safe_avatar_action(command,identifier):
    catalog={'EXPRESSION':EXPRESSIONS,'ANIMATION':ANIMATIONS}.get(command,{}) if isinstance(command,str) else {}
    if not isinstance(identifier,str) or identifier not in catalog:
        return VoiceAction('EXPRESSION','neutral','Neutral'),True
    return VoiceAction(command,identifier,catalog[identifier]),False


@dataclass(frozen=True)
class PerformanceSegment:
    text: str=field(repr=False)
    action: VoiceAction
    delivery: str
    speed: float=1.0
    energy: float=1.0
    pause_ms: int=0

    def payload(self):
        return {'text':self.text,'avatar_type':'animation' if self.action.command=='ANIMATION' else 'expression',
                'avatar_id':self.action.argument,'delivery':self.delivery,
                'speed':self.speed,'energy':self.energy,'pause_ms':self.pause_ms}


@dataclass(frozen=True)
class AvatarReply:
    text: str=field(repr=False)
    action: VoiceAction
    fallback: bool=False
    segments: tuple[PerformanceSegment,...]=()


@dataclass(frozen=True)
class AvatarCue:
    connection: int
    conversation: int
    control: int
    phase: str
    action: VoiceAction


def normalize_reply(value):
    segments=()
    if isinstance(value,AvatarReply):
        text=value.text
        if isinstance(value.action,VoiceAction) and value.action.look is None:
            action,fallback=safe_avatar_action(value.action.command,value.action.argument)
        else:
            action,fallback=safe_avatar_action(None,None)
        fallback=fallback or value.fallback
        if value.segments:
            segments=parse_segments([segment.payload() for segment in value.segments],text)
    else:
        text=value
        action,fallback=safe_avatar_action(None,None)
    if not isinstance(text,str) or not text.strip() or len(text)>2000 or '\x00' in text:
        raise ValueError('La respuesta de la IA no contiene un texto válido.')
    return AvatarReply(text.strip(),action,fallback,segments)


def parse_segments(items,text):
    if not isinstance(text,str) or not text.strip() or len(text)>2000 or '\x00' in text:
        raise ValueError('Texto de interpretación inválido.')
    if not isinstance(items,list) or not 1<=len(items)<=4:
        raise ValueError('El plan expresivo debe contener entre uno y cuatro fragmentos.')
    result=[]
    for item in items:
        if not isinstance(item,dict) or set(item)!={'text','avatar_type','avatar_id','delivery','speed','energy','pause_ms'}:
            raise ValueError('Fragmento expresivo inválido.')
        fragment,delivery=item['text'],item['delivery']
        if (not isinstance(fragment,str) or not fragment.strip() or len(fragment)>2000 or '\x00' in fragment
            or not isinstance(delivery,str) or not delivery.strip() or len(delivery)>160 or '\x00' in delivery):
            raise ValueError('Texto o intención expresiva inválidos.')
        for name,low,high in [('speed',.8,1.2),('energy',.65,1.2)]:
            value=item[name]
            if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
                raise ValueError('Control de voz fuera de rango.')
        if type(item['pause_ms']) is not int or not 0<=item['pause_ms']<=600:
            raise ValueError('Pausa fuera de rango.')
        command={'expression':'EXPRESSION','animation':'ANIMATION'}.get(item['avatar_type']) if isinstance(item['avatar_type'],str) else None
        action,fallback=safe_avatar_action(command,item['avatar_id'])
        if fallback:
            raise ValueError('El plan eligió un gesto no disponible.')
        result.append(PerformanceSegment(fragment.strip(),action,delivery.strip(),float(item['speed']),float(item['energy']),item['pause_ms']))
    if ' '.join(' '.join(s.text.split()) for s in result)!=' '.join(text.split()):
        raise ValueError('Los fragmentos de voz no coinciden con la respuesta escrita.')
    return tuple(result)


def parse_avatar_reply(content):
    data=json.loads(content)
    if not isinstance(data,dict):
        raise ValueError('Respuesta estructurada inválida.')
    if set(data)=={'text','segments'}:
        if not isinstance(data['segments'],list):
            raise ValueError('Plan expresivo inválido.')
        items=[]
        for item in data['segments']:
            if not isinstance(item,dict) or not isinstance(item.get('gesture'),str) or ':' not in item['gesture']:
                raise ValueError('Gesto expresivo inválido.')
            kind,identifier=item['gesture'].split(':',1)
            items.append({**{k:v for k,v in item.items() if k!='gesture'},'avatar_type':kind,'avatar_id':identifier})
        segments=parse_segments(items,data['text'])
        return normalize_reply(AvatarReply(data['text'],segments[0].action,False,segments))
    command={'expression':'EXPRESSION','animation':'ANIMATION'}.get(data.get('avatar_type')) if isinstance(data.get('avatar_type'),str) else None
    action,fallback=safe_avatar_action(command,data.get('avatar_id'))
    if set(data) not in ({'text','avatar_type','avatar_id'},{'text','avatar_type','avatar_id','segments'}):
        action,fallback=safe_avatar_action(None,None)
    segments=parse_segments(data['segments'],data.get('text')) if 'segments' in data else ()
    if segments:
        if fallback or action.command!=segments[0].action.command or action.argument!=segments[0].action.argument:
            raise ValueError('El gesto inicial no coincide con el plan expresivo.')
    return normalize_reply(AvatarReply(data.get('text'),action,fallback,segments))


AVATAR_SCHEMA={
    'type':'object',
    'properties':{
        'text':{'type':'string'},
        'segments':{'type':'array','minItems':1,'maxItems':4,'items':{
            'type':'object','properties':{
                'text':{'type':'string'},
                'gesture':{'type':'string','enum':sorted(['expression:'+x for x in EXPRESSIONS]+['animation:'+x for x in ANIMATIONS])},
                'delivery':{'type':'string'},
                'speed':{'type':'number','minimum':.8,'maximum':1.2},
                'energy':{'type':'number','minimum':.65,'maximum':1.2},
                'pause_ms':{'type':'integer','minimum':0,'maximum':600}},
            'required':['text','gesture','delivery','speed','energy','pause_ms'],
            'additionalProperties':False}},
    },
    'required':['text','segments'],
    'additionalProperties':False,
}

AVATAR_INSTRUCTIONS=(
    'Dirigís la interpretación de Aubar, no solamente sus palabras. '
    'Devolvé únicamente un objeto JSON con text y segments. '
    'text es tu respuesta natural para leer en voz alta, sin identificadores ni metadatos. '
    'Elegí texto, gestos y prosodia conjuntamente según toda la conversación, la intención y las instrucciones del usuario. '
    'Si pide actuar o decir algo con una emoción, respetá esa actuación aunque el significado de la frase sea positivo. '
    'Si pide decir una frase literal, preservala: no agregues consejos, saludos ni exclamaciones que no pidió. '
    'No uses siempre alegría: podés ser neutral, firme, sereno, triste, juguetón o expresivo según el contexto. '
    'No confundas describir una emoción con actuarla. No finjas acciones físicas no disponibles. '
    'segments contiene de 1 a 4 fragmentos consecutivos con text, gesture, delivery, speed, energy y pause_ms. '
    'Al unir los textos de segments con un espacio debe obtenerse exactamente text. '
    'Usá un fragmento para frases breves; dividí solo si cambia la intención o conviene una pausa expresiva, nunca por palabra. '
    'gesture es un identificador exacto con prefijo: expression:ID o animation:ID. '
    'delivery describe brevemente cómo interpretar el fragmento y no se pronuncia. '
    'Controlás Onyx: speed entre 0.8 y 1.2 (1 mantiene el ritmo actual), energy entre 0.65 y 1.2 '
    '(1 mantiene la energía actual), pause_ms entre 0 y 600 después del fragmento. '
    'Elegí esos valores según la actuación, sin exagerarlos ni cambiar todos por costumbre. '
    'Este motor ajusta ritmo, energía y pausas: no admite instrucciones emocionales nativas ni cambios de voz. '
    'Usá neutral si no hay una emoción clara. No prometas que ya se aplicó la selección. '
    'Para gesture=expression:ID, estos son los IDs permitidos con sus nombres: '
    +json.dumps(EXPRESSIONS,ensure_ascii=False)+'. '
    'Para gesture=animation:ID, estos son los IDs permitidos con sus nombres: '
    +json.dumps(ANIMATIONS,ensure_ascii=False)+'.'
)
