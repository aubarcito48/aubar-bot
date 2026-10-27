"""Validated visual feedback. Model output never becomes arbitrary USB text."""
from dataclasses import dataclass,field
import json

from .catalog import EXPRESSIONS,ANIMATIONS
from .voice_commands import VoiceAction


def safe_avatar_action(command,identifier):
    catalog={'EXPRESSION':EXPRESSIONS,'ANIMATION':ANIMATIONS}.get(command,{}) if isinstance(command,str) else {}
    if not isinstance(identifier,str) or identifier not in catalog:
        return VoiceAction('EXPRESSION','neutral','Neutral'),True
    return VoiceAction(command,identifier,catalog[identifier]),False


@dataclass(frozen=True)
class AvatarReply:
    text: str=field(repr=False)
    action: VoiceAction
    fallback: bool=False


@dataclass(frozen=True)
class AvatarCue:
    connection: int
    conversation: int
    control: int
    phase: str
    action: VoiceAction


def normalize_reply(value):
    if isinstance(value,AvatarReply):
        text=value.text
        if isinstance(value.action,VoiceAction) and value.action.look is None:
            action,fallback=safe_avatar_action(value.action.command,value.action.argument)
        else:
            action,fallback=safe_avatar_action(None,None)
        fallback=fallback or value.fallback
    else:
        text=value
        action,fallback=safe_avatar_action(None,None)
    if not isinstance(text,str) or not text.strip() or len(text)>2000 or '\x00' in text:
        raise ValueError('La respuesta de la IA no contiene un texto válido.')
    return AvatarReply(text.strip(),action,fallback)


def parse_avatar_reply(content):
    data=json.loads(content)
    if not isinstance(data,dict):
        raise ValueError('Respuesta estructurada inválida.')
    command={'expression':'EXPRESSION','animation':'ANIMATION'}.get(data.get('avatar_type')) if isinstance(data.get('avatar_type'),str) else None
    action,fallback=safe_avatar_action(command,data.get('avatar_id'))
    if set(data)!={'text','avatar_type','avatar_id'}:
        action,fallback=safe_avatar_action(None,None)
    return normalize_reply(AvatarReply(data.get('text'),action,fallback))


AVATAR_SCHEMA={
    'type':'object',
    'properties':{
        'text':{'type':'string'},
        'avatar_type':{'type':'string','enum':['expression','animation']},
        'avatar_id':{'type':'string','enum':sorted(set(EXPRESSIONS)|set(ANIMATIONS))},
    },
    'required':['text','avatar_type','avatar_id'],
    'additionalProperties':False,
}

AVATAR_INSTRUCTIONS=(
    'Devolvé únicamente un objeto JSON con text, avatar_type y avatar_id. '
    'text es tu respuesta natural para leer en voz alta, sin identificadores ni metadatos. '
    'Elegí una sola expresión o animación coherente con el tono de TU respuesta; '
    'priorizá acompañar con empatía al usuario, sin reaccionar con alegría ante una noticia triste. '
    'Usá neutral si no hay una emoción clara. No prometas que ya se aplicó la selección. '
    'Para avatar_type=expression, estos son los IDs permitidos con sus nombres: '
    +json.dumps(EXPRESSIONS,ensure_ascii=False)+'. '
    'Para avatar_type=animation, estos son los IDs permitidos con sus nombres: '
    +json.dumps(ANIMATIONS,ensure_ascii=False)+'.'
)
