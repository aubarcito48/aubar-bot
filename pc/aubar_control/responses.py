"""Replaceable text source for confirmed actions; independent of TTS playback."""
from .catalog import EXPRESSIONS

EXPRESSION_REPLIES = {
    'neutral':'Estoy tranquilo',
    'contento':'Estoy contento',
    'sorprendido':'Estoy sorprendido',
    'dormido':'Me voy a dormir',
    'enojado':'Estoy enojado',
}
ANIMATION_REPLIES = {
    'sleeping':'Me voy a dormir', 'waking':'Voy a despertarme',
    'idle':'Voy a descansar', 'listening':'Te escucho',
    'thinking':'Voy a pensar', 'searching':'Voy a buscar',
    'working':'Me pongo a trabajar', 'excited':'Estoy entusiasmado',
    'bored':'Me estoy aburriendo', 'suspicious':'Voy a observar con atención',
    'angry':'Me estoy enojando', 'drowsy':'Me está dando sueño',
    'happy':'Estoy alegre', 'curious':'Tengo curiosidad',
    'confused':'Estoy confundido', 'surprised':'Estoy sorprendido',
    'proud':'Estoy orgulloso', 'shy':'Me da un poco de vergüenza',
    'sad':'Estoy triste', 'laughing':'Voy a reír',
    'scared':'Estoy asustado', 'playful':'Voy a jugar',
    'celebrate':'Voy a celebrar',
}
LOCATIONS = {'izquierda':'a la izquierda','centro':'al centro','derecha':'a la derecha'}


def confirmation_text(action):
    """Produce text only; callers must already have the device acknowledgment."""
    if action.command=='EXPRESSION':
        if action.argument not in EXPRESSIONS:
            return None
        text=EXPRESSION_REPLIES.get(action.argument)
        if text is None:
            text='Muestro la expresión '+EXPRESSIONS[action.argument].lower()
    elif action.command=='ANIMATION':
        text=ANIMATION_REPLIES.get(action.argument)
        if text is None:
            return None
    elif action.command=='LOOK' and action.argument in LOCATIONS and action.look is None:
        return 'Miro '+LOCATIONS[action.argument]+'.'
    elif action.command=='MODE' and action.argument in ('manual','auto') and action.look is None:
        return 'Activo el modo '+('automático' if action.argument=='auto' else 'manual')+'.'
    else:
        return None
    if action.look is not None:
        if action.look not in LOCATIONS:
            return None
        text+=' mirando '+LOCATIONS[action.look]
    return text+'.'
