from dataclasses import dataclass
import unicodedata
from .catalog import EXPRESSIONS, ANIMATIONS


@dataclass(frozen=True)
class VoiceAction:
    command: str
    argument: str
    label: str


def normalize(text: str) -> str:
    text = ''.join(char for char in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(char))
    text = ''.join(char if char.isalnum() or char.isspace() else ' ' for char in text)
    return ' '.join(text.split())


def match_command(text: str) -> VoiceAction | None:
    phrase = normalize(text)
    if phrase.startswith('kirby '):
        phrase = phrase[6:]
    if phrase.endswith(' por favor'):
        phrase = phrase[:-10]
    actions = {}
    for word in ('neutral', 'contento', 'sorprendido', 'dormido', 'enojado'):
        action = VoiceAction('EXPRESSION', word, f'Expresión: {word}')
        forms = (word,) if word == 'contento' else (
            word, f'ponete {word}', f'ponte {word}', f'pone {word}', f'cara {word}')
        for form in forms:
            actions[form] = action
    for form in ('dormite', 'dormi te', 'duerme', 'a dormir'):
        actions[form] = VoiceAction('EXPRESSION', 'dormido', 'Expresión: dormido')
    for direction in ('izquierda', 'centro', 'derecha'):
        action = VoiceAction('LOOK', direction, f'Mirada: {direction}')
        article = 'el' if direction == 'centro' else 'la'
        for form in (direction, f'mira a {article} {direction}', f'mira {article} {direction}',
                     f'mira hacia {article} {direction}'):
            actions[form] = action
        if direction == 'centro':
            actions['mira al centro'] = action
    for word, argument in (('automatico', 'auto'), ('manual', 'manual')):
        action = VoiceAction('MODE', argument, f'Modo: {word}')
        for form in (f'modo {word}', f'activa modo {word}', f'activa el modo {word}'):
            actions[form] = action
    # Explicit catalog prefixes disambiguate a static face from a sequence.
    for identifier, label in EXPRESSIONS.items():
        actions['expresion '+normalize(label)] = VoiceAction(
            'EXPRESSION', identifier, f'Expresión: {label}')
    aliases = {
        'sleeping': ('dormir',), 'waking': ('despertar',),
        'idle': ('reposo',), 'listening': ('escuchar',),
        'thinking': ('pensar',), 'searching': ('buscar',),
        'working': ('trabajar',), 'excited': ('entusiasmarse',),
        'bored': ('aburrirse',), 'suspicious': ('sospechar',),
        'angry': ('enojarse',), 'drowsy': ('adormecerse',),
        'happy': ('alegria',), 'curious': ('curiosear',),
        'confused': ('confundirse',), 'surprised': ('sorprenderse',),
        'proud': ('orgullo',), 'shy': ('timidez',), 'sad': ('tristeza',),
        'laughing': ('reir',), 'scared': ('asustarse',),
        'playful': ('jugar',), 'celebrate': ('celebrar',),
    }
    for identifier, words in aliases.items():
        action = VoiceAction('ANIMATION', identifier, f'Animación: {ANIMATIONS[identifier]}')
        for word in words:
            actions[word] = action
            actions['animacion '+word] = action
    return actions.get(phrase)
