"""Explicit local YouTube commands; never execute model-generated URLs."""
from dataclasses import dataclass
import re
from urllib.parse import urlencode
import webbrowser


@dataclass(frozen=True)
class YouTubeAction:
    operation: str
    query: str = ''


class _QuietLogger:
    def debug(self, message): pass
    def warning(self, message): pass
    def error(self, message): pass


def first_video(query):
    """Resolve a search result without downloading media or using browser cookies."""
    from yt_dlp import YoutubeDL
    options = dict(extract_flat=True, skip_download=True, quiet=True,
                   no_warnings=True, cachedir=False, socket_timeout=8,
                   retries=0, extractor_retries=0, playlistend=1,
                   lazy_playlist=True, logger=_QuietLogger())
    with YoutubeDL(options) as client:
        result = client.extract_info('ytsearch1:' + query, download=False)
        entry = next(iter((result or {}).get('entries') or ()), None)
    identifier = entry.get('id') if isinstance(entry, dict) else None
    if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}', identifier):
        raise ValueError('No valid video result')
    return identifier


def match_youtube_command(text):
    text = ' '.join(text.strip().split())
    text = re.sub(r'^aubar[,:]?\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+por favor[.!]?$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:por favor[, ]+)', '', text, flags=re.IGNORECASE)
    # These are explicit requests too, rather than general questions about YouTube.
    text = re.sub(r'^(?:pod[eé]s|puedes|podr[ií]as)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(?:quiero|necesito)\s+que\s+(?:me\s+)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^me\s+(?=bus|pon|repro)', '', text, flags=re.IGNORECASE)
    open_verb = r'(?:abr[ií]|abrime|abre|abrir)'
    if re.fullmatch(open_verb+r'\s+you\s*tube[.!]?', text, re.IGNORECASE):
        return YouTubeAction('open')
    # Reduce one explicit YouTube sequence to one action. Opening the home page
    # first would create an unnecessary tab and would not start the selected video.
    opening = re.fullmatch(open_verb+r'\s+you\s*tube(?:\s+y\s+|,\s*(?:y\s+)?)(.+)',
                          text, re.IGNORECASE)
    youtube_context = opening is not None
    if opening:
        text = opening.group(1).strip()
    playback = re.fullmatch(
        r'(.+?)\s+y\s+(?:(?:despu[eé]s|luego)\s+)?'
        r'(?:reproducir|reproduc[ií](?:lo|los)?|reprod[uú]c(?:elo|elos)|reproduce(?:lo|los)?|'
        r'ponelo|ponlo|pon[eé](?:lo)?)'
        r'(?:\s+(?:el primero|el primer video|el video|ese video))?[.!]?',
        text, re.IGNORECASE)
    if playback:
        text = playback.group(1).strip()
    # Keep the user's search intact, including accents, C++, URLs and punctuation.
    location = r'(?:en|por)\s+you\s*tube'
    verbs = (
        ('search', r'(?:busc[aá]|b[uú]sc[aá]me|buscar(?:me)?|busques|busc[aá]s|busque)'),
        ('play', r'(?:pon[eé]|poneme|p[oó]nme|pon|poner|pongas|reproduc[ií]|reproduce|reproducir|reproduzcas)'),
    )
    for operation, verb in verbs:
        match = re.fullmatch(verb+r'\s+'+location+r'(?:\s+(.*))?', text, re.IGNORECASE)
        if match:
            return YouTubeAction('play' if playback else operation, (match.group(1) or '').strip())
        match = re.fullmatch(verb+r'(?:\s+(.*?))?\s+'+location+r'[.!]?', text, re.IGNORECASE)
        if match:
            return YouTubeAction('play' if playback else operation, (match.group(1) or '').strip())
        if youtube_context:
            match = re.fullmatch(verb+r'(?:\s+(.*))?', text, re.IGNORECASE)
            if match:
                return YouTubeAction('play' if playback else operation, (match.group(1) or '').strip())
    return None


def open_youtube(action, opener=webbrowser.open_new_tab, *, resolver=first_video, cancel_event=None):
    """Return a display message and optional spoken confirmation; no retries."""
    if action.operation == 'open' and not action.query:
        url = 'https://www.youtube.com/'
        confirmation = 'Abrí YouTube en tu navegador.'
    elif action.operation in ('search','play'):
        if not action.query or len(action.query) > 500:
            return 'Decí qué querés buscar en YouTube, con una frase de hasta 500 caracteres.', None
        if action.operation == 'play':
            if cancel_event is not None and cancel_event.is_set():
                return 'Acción de YouTube cancelada.', None
            try:
                identifier = resolver(action.query)
                if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}',identifier):
                    raise ValueError('Invalid video identifier')
            except Exception:
                return 'No se pudo encontrar un video para reproducir. Probá otra vez o usá «busca en YouTube» seguido del tema.', None
            url = 'https://www.youtube.com/watch?' + urlencode({'v': identifier, 'autoplay': '1'})
            confirmation = 'Abrí el primer video de ' + action.query + ' en YouTube.'
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
