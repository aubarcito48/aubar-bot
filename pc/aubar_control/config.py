"""Local Groq settings. Loading never makes network requests or logs values."""
from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from dotenv import dotenv_values

ENV_PATH=Path(__file__).resolve().parents[2]/'.env'
DEFAULT_MODEL='openai/gpt-oss-20b'
DEFAULT_TIMEOUT=20.0


@dataclass(frozen=True)
class GroqConfig:
    api_key: str=field(repr=False)
    model: str=DEFAULT_MODEL
    timeout_seconds: float=DEFAULT_TIMEOUT
    director: str='groq'
    portfolio_api_url: str=''
    whatsapp_health_url: str=''
    whatsapp_control_url: str=''
    whatsapp_control_token: str=field(default='',repr=False)
    source_timeout_seconds: float=60.0


@dataclass(frozen=True)
class ConfigState:
    config: GroqConfig | None
    message: str

    @property
    def ready(self):
        return self.config is not None


def load_groq_config(env_path=ENV_PATH,environ=None):
    """Process environment overrides the explicit project .env, without mutation.

    No interpolation: values such as ${OTHER_SECRET} remain literal. env_path=None
    disables file loading, useful for callers supplying an isolated environment.
    Errors use fixed messages, never raw values or exception details.
    """
    values={}
    try:
        if env_path is not None and Path(env_path).exists():
            if Path(env_path).stat().st_size>65536:
                return ConfigState(None,'El archivo .env es demasiado grande. Revisá la configuración local.')
            values.update(dotenv_values(env_path,encoding='utf-8-sig',interpolate=False))
    except (OSError,UnicodeError):
        return ConfigState(None,'No se pudo leer .env. Revisá el archivo y sus permisos.')
    environment=os.environ if environ is None else environ
    for name in ('GROQ_API_KEY','GROQ_MODEL','GROQ_TIMEOUT_SECONDS','AUBAR_DIRECTOR',
                 'AUBAR_PORTFOLIO_API_URL','AUBAR_WHATSAPP_HEALTH_URL',
                 'AUBAR_WHATSAPP_CONTROL_URL','AUBAR_CONTROL_TOKEN','AUBAR_SOURCES_TIMEOUT_SECONDS'):
        if name in environment:
            values[name]=environment[name]

    key=(values.get('GROQ_API_KEY') or '').strip()
    if not key:
        return ConfigState(None,'Falta GROQ_API_KEY. Completá .env y pulsá «Recargar configuración».')
    if (not key.isascii() or any(character.isspace() or ord(character)<33 or ord(character)==127 for character in key)
        or '${' in key or key.lower() in ('tu_api_key','your_api_key','reemplazar_aqui')):
        return ConfigState(None,'GROQ_API_KEY tiene un formato inválido. Revisá el valor local sin compartirlo.')
    model=values.get('GROQ_MODEL',DEFAULT_MODEL) or ''
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}',model):
        return ConfigState(None,'GROQ_MODEL no es válido. Indicá un identificador de modelo en .env.')
    try:
        timeout=float(values.get('GROQ_TIMEOUT_SECONDS',str(DEFAULT_TIMEOUT)))
        if not math.isfinite(timeout) or not 1<=timeout<=120:
            raise ValueError
    except (TypeError,ValueError):
        return ConfigState(None,'GROQ_TIMEOUT_SECONDS debe ser un número entre 1 y 120.')
    director=values.get('AUBAR_DIRECTOR','groq')
    if director not in ('groq','local'):
        return ConfigState(None,'AUBAR_DIRECTOR debe ser groq o local.')
    try:
        portfolio=validate_source_url(values.get('AUBAR_PORTFOLIO_API_URL') or '',health=False)
        whatsapp=validate_source_url(values.get('AUBAR_WHATSAPP_HEALTH_URL') or '',health=True)
        control=validate_control_url(values.get('AUBAR_WHATSAPP_CONTROL_URL') or '')
    except ValueError:
        return ConfigState(None,'Revisá las URLs de integración: portfolio /api/v1/ por HTTPS '
            '(HTTP solo local) y WhatsApp /health solo en loopback.')
    token=values.get('AUBAR_CONTROL_TOKEN') or ''
    if bool(control)!=bool(token) or token and not re.fullmatch(r'[a-f0-9]{64}',token):
        return ConfigState(None,'Configurá AUBAR_WHATSAPP_CONTROL_URL y AUBAR_CONTROL_TOKEN juntos; '
            'el token debe tener 64 caracteres hexadecimales.')
    try:
        source_timeout=float(values.get('AUBAR_SOURCES_TIMEOUT_SECONDS','60'))
        if not math.isfinite(source_timeout) or not 1<=source_timeout<=90:
            raise ValueError
    except (TypeError,ValueError):
        return ConfigState(None,'AUBAR_SOURCES_TIMEOUT_SECONDS debe ser un número entre 1 y 90.')
    return ConfigState(GroqConfig(key,model,timeout,director,portfolio,whatsapp,control,token,source_timeout),
        'Configuración local lista. La clave y el acceso al modelo todavía no se comprobaron con Groq.')


def validate_source_url(value,*,health):
    if not value:
        return ''
    if not isinstance(value,str) or any(c.isspace() or ord(c)<33 for c in value) or '\\' in value:
        raise ValueError('URL de fuente inválida.')
    try:
        url=urlsplit(value)
        local=url.hostname in ('localhost','127.0.0.1','::1')
        if (not url.hostname or url.username is not None or url.password is not None
            or url.query or url.fragment or url.port==0
            or url.scheme not in ('http','https') or url.scheme=='http' and not local
            or health and not local or url.path!=('/health' if health else '/api/v1/')):
            raise ValueError
    except (ValueError,TypeError):
        raise ValueError('URL de fuente inválida.') from None
    return value


def validate_control_url(value):
    if not value:
        return ''
    if not isinstance(value,str) or not value.endswith('/control/'):
        raise ValueError('URL de control inválida.')
    validate_source_url(value[:-len('/control/')]+'/health',health=True)
    return value
