"""Local Groq settings. Loading never makes network requests or logs values."""
from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import re

from dotenv import dotenv_values

ENV_PATH=Path(__file__).resolve().parents[2]/'.env'
DEFAULT_MODEL='openai/gpt-oss-20b'
DEFAULT_TIMEOUT=20.0


@dataclass(frozen=True)
class GroqConfig:
    api_key: str=field(repr=False)
    model: str=DEFAULT_MODEL
    timeout_seconds: float=DEFAULT_TIMEOUT


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
    for name in ('GROQ_API_KEY','GROQ_MODEL','GROQ_TIMEOUT_SECONDS'):
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
    return ConfigState(GroqConfig(key,model,timeout),
        'Configuración local lista. La clave y el acceso al modelo todavía no se comprobaron con Groq.')
