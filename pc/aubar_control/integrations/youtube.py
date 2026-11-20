"""Explicit local YouTube commands; never execute model-generated URLs."""
from dataclasses import dataclass
from itertools import islice
import re
from urllib.parse import urlencode
import webbrowser


@dataclass(frozen=True)
class YouTubeAction:
    operation: str
    query: str = ''
    position: int = 1


POSITIONS = {'primero': 1, 'primer': 1, 'segundo': 2, 'tercero': 3, 'tercer': 3,
             'cuarto': 4, 'quinto': 5, 'sexto': 6, 'septimo': 7, 'séptimo': 7,
             'octavo': 8, 'noveno': 9, 'decimo': 10, 'décimo': 10}
ORDINAL = '(?:'+'|'.join(POSITIONS)+r'|\d{1,3})'
PLAY_VERB = (r'(?:reproducir|reproduc[ií](?:lo|los)?|reprod[uú]c(?:elo|elos)|'
             r'reproduce(?:lo|los)?|reproduzca(?:s)?|ponelo|ponlo|pon[eé](?:lo)?)')


def _position(value):
    value = (value or 'primero').casefold()
    return int(value) if value.isdecimal() else POSITIONS[value]


class _QuietLogger:
    def debug(self, message): pass
    def warning(self, message): pass
    def error(self, message): pass


def search_video(query, position=1):
    """Resolve a search result without downloading media or using browser cookies."""
    if type(position) is not int or not 1 <= position <= 10:
        raise ValueError('Video position must be between 1 and 10')
    from yt_dlp import YoutubeDL
    options = dict(extract_flat=True, skip_download=True, quiet=True,
                   no_warnings=True, cachedir=False, socket_timeout=8,
                   retries=0, extractor_retries=0, playlistend=position,
                   lazy_playlist=True, logger=_QuietLogger())
    with YoutubeDL(options) as client:
        result = client.extract_info(f'ytsearch{position}:' + query, download=False)
        entries = list(islice((result or {}).get('entries') or (), position))
        entry = entries[position-1] if len(entries) == position else None
    identifier = entry.get('id') if isinstance(entry, dict) else None
    if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}', identifier):
        raise ValueError('No valid video result')
    return identifier


def first_video(query):
    return search_video(query, 1)


def match_youtube_command(text, *, previous_query=None):
    text = ' '.join(text.strip().split())
    text = re.sub(r'^(?:aubar|au\s+bar)[,.:;!?]?\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+por favor[.!]?$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:por favor[, ]+)', '', text, flags=re.IGNORECASE)
    # These are explicit requests too, rather than general questions about YouTube.
    text = re.sub(r'^(?:pod[eé]s|puedes|podr[ií]as)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:quiero|necesito)\s+que\s+(?:me\s+)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^me\s+(?=bus|pon|repro)', '', text, flags=re.IGNORECASE)
    open_verb = r'(?:abr[ií]|abrime|abre|abrir)'
    followup = re.fullmatch(PLAY_VERB+r'\s+(?:el\s+)?('+ORDINAL+r')(?:\s+(?:resultado|v[ií]deo))?[.!]?', text, re.IGNORECASE)
    if followup is None and previous_query:
        followup = re.fullmatch(r'(?:el\s+)?('+ORDINAL+r')(?:\s+(?:resultado|v[ií]deo))?[.!]?', text, re.IGNORECASE)
    if followup:
        return YouTubeAction('play', previous_query or '', _position(followup[1]))
    if re.fullmatch(open_verb+r'\s+you\s*tube[.!]?', text, re.IGNORECASE):
        return YouTubeAction('open')
    # Reduce one explicit YouTube sequence to one action. Opening the home page
    # first would create an unnecessary tab and would not start the selected video.
    opening = re.fullmatch(open_verb+r'\s+you\s*tube(?:\s+y\s+|,\s*(?:y\s+)?)(.+)',
                          text, re.IGNORECASE)
    youtube_context = opening is not None
    if opening:
        text = opening.group(1).strip()
    playback = re.fullmatch(r'(.+?)(?:\s+y\s+|[,.;]\s*(?:y\s+)?)'
        r'(?:(?:despu[eé]s|luego)\s+)?'+PLAY_VERB+
        r'(?:\s+(?:(?:el\s+)?(?P<ordinal>'+ORDINAL+r')(?:\s+(?:resultado|v[ií]deo))?|el v[ií]deo|ese v[ií]deo))?[.!]?',
        text, re.IGNORECASE)
    # A quoted video title may itself contain words that look like a command.
    if playback and (playback[1].count('"') % 2 or playback[1].count('«') != playback[1].count('»')):
        playback = None
    position = _position(playback['ordinal']) if playback else 1
    if playback:
        text = playback.group(1).strip()
    # Keep the user's search intact, including accents, C++, URLs and punctuation.
    location = r'(?:en|por)\s+you\s*tube'
    verbs = (
        ('search', r'(?:busc[aá]|b[uú]sc[aá]me|buscar(?:me)?|busques|busc[aá]s|busque)'),
        ('play', r'(?:pon[eé]|poneme|p[oó]nme|pon|poner|pongas|reproduc[ií]|reproduce|reproducir|reproduzcas)'),
    )
    for operation, verb in verbs:
        # Whisper can place a sentence break between searching and playing,
        # or put the destination between "videos" and the topic.
        match = re.fullmatch(verb+r'\s+((?:(?:un|unos)\s+)?v[ií]deos?)\s+'+location+r'\s+(.+)', text, re.IGNORECASE)
        if match:
            query = match[1]+' '+match[2]
            return YouTubeAction('play' if playback else operation, query, position)
        match = re.fullmatch(verb+r'\s+'+location+r'(?:\s+(.*))?', text, re.IGNORECASE)
        if match:
            return YouTubeAction('play' if playback else operation, (match.group(1) or '').strip(), position)
        match = re.fullmatch(verb+r'(?:\s+(.*?))?\s+'+location+r'[.!]?', text, re.IGNORECASE)
        if match:
            return YouTubeAction('play' if playback else operation, (match.group(1) or '').strip(), position)
        if youtube_context or previous_query:
            match = re.fullmatch(verb+r'(?:\s+(.*))?', text, re.IGNORECASE)
            if match:
                query = (match.group(1) or '').strip()
                # A recent YouTube search supplies the destination for explicit
                # video requests, not arbitrary searches such as files or email.
                if youtube_context or re.match(r'v[ií]deos?\b', query, re.IGNORECASE):
                    return YouTubeAction('play' if playback else operation, query, position)
    return None


def open_youtube(action, opener=webbrowser.open_new_tab, *, resolver=search_video, cancel_event=None):
    """Return a display message and optional spoken confirmation; no retries."""
    if action.operation == 'open' and not action.query:
        url = 'https://www.youtube.com/'
        confirmation = 'Abrí YouTube en tu navegador.'
    elif action.operation in ('search','play'):
        if not action.query and action.operation == 'play':
            return 'Primero indicá qué buscar en YouTube; después podés pedir el segundo resultado.', None
        if not action.query or len(action.query) > 500:
            return 'Decí qué querés buscar en YouTube, con una frase de hasta 500 caracteres.', None
        if action.operation == 'play':
            if type(action.position) is not int or not 1 <= action.position <= 10:
                return 'Podés elegir un resultado del primero al décimo. Indicá cuál querés.', None
            if cancel_event is not None and cancel_event.is_set():
                return 'Acción de YouTube cancelada.', None
            try:
                identifier = resolver(action.query) if action.position == 1 else resolver(action.query, action.position)
                if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}',identifier):
                    raise ValueError('Invalid video identifier')
            except Exception:
                return 'No se pudo encontrar el resultado solicitado. No abrí otro video. Probá otra búsqueda.', None
            url = 'https://www.youtube.com/watch?' + urlencode({'v': identifier, 'autoplay': '1'})
            ordinal = {1:'primer', 2:'segundo', 3:'tercer', 4:'cuarto', 5:'quinto',
                       6:'sexto', 7:'séptimo', 8:'octavo', 9:'noveno', 10:'décimo'}[action.position]
            confirmation = 'Abrí el '+ordinal+' resultado de ' + action.query + ' en YouTube.'
        else:
            url = 'https://www.youtube.com/results?' + urlencode({'search_query': action.query})
            confirmation = 'Abrí la búsqueda de ' + action.query + ' en YouTube.'
    else:
        return 'La acción de YouTube no es válida.', None
    if cancel_event is not None and cancel_event.is_set():
        return 'Acción de YouTube cancelada.', None
    try:
        opened = opener(url)
    except Exception:
        opened = False
    if not opened:
        return 'No se pudo abrir el navegador. Revisá el navegador predeterminado de Windows.', None
    return confirmation + ' Solicitud enviada al navegador.', confirmation
