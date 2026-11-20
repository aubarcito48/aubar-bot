"""Shared transcription result and error contract."""
from dataclasses import dataclass
from .voice_commands import VoiceAction
from ...integrations.youtube import YouTubeAction


class RecognitionError(Exception):
    pass


@dataclass(frozen=True)
class RecognitionResult:
    text: str
    action: VoiceAction | None
    message: str
    query: str | None = None
    youtube: YouTubeAction | None = None
