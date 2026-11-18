from array import array
from pathlib import Path
import unittest

from pc.aubar_control.audio import Recording
from pc.aubar_control.recognition import RecognitionError
from pc.aubar_control.whisper_recognition import WhisperRecognizer
from pc.aubar_control.voice_commands import match_command


def result(text, confidence=1):
    return {'text': text, 'result': [{'word': word, 'conf': confidence} for word in text.split()]}


class FakeBackend:
    """Whisper constructor and model fake with mutable segment evidence."""
    def __init__(self, final, segment=None):
        self.final, self.segment = final, segment
        self.models = 0
        self.rate = None

    def __call__(self, path, **kwargs):
        self.models += 1
        return self

    def transcribe(self, samples, **kwargs):
        from types import SimpleNamespace as Item
        self.rate = 16000
        parts = ([self.segment] if self.segment is not None else []) + [self.final]
        return iter([Item(text=part['text'], words=[Item(probability=w['conf']) for w in part['result']],
            avg_logprob=-.1, no_speech_prob=.01, compression_ratio=1) for part in parts]), Item()


class VoiceTests(unittest.TestCase):
    def test_spanish_commands_accents_and_politeness(self):
        phrases = {
            '¡Contento!': ('EXPRESSION', 'contento'),
            'pone enojado': ('EXPRESSION', 'enojado'),
            'Kirby, dormíte por favor': ('EXPRESSION', 'dormido'),
            'dormí te': ('EXPRESSION', 'dormido'),
            'ponte enojado': ('EXPRESSION', 'enojado'),
            'mirá a la izquierda': ('LOOK', 'izquierda'),
            'mira al centro': ('LOOK', 'centro'),
            'MIRÁ HACIA LA DERECHA': ('LOOK', 'derecha'),
            'modo automático': ('MODE', 'auto'),
            'activa el modo manual': ('MODE', 'manual'),
        }
        for phrase, expected in phrases.items():
            with self.subTest(phrase=phrase):
                action = match_command(phrase)
                self.assertEqual((action.command, action.argument), expected)

    def test_unknown_negated_and_combined_phrases_are_not_commands(self):
        for phrase in ('', 'hoy hace frio', 'no te pongas enojado', 'no pone contento', 'creo que esta contento',
                       'ponete contento', 'ponte contento', 'pone contento', 'bonete contento', 'o nete contento',
                       'mira a la izquierda y a la derecha', 'ponete contento ahora mismo', 'modo automatico falso'):
            with self.subTest(phrase=phrase):
                self.assertIsNone(match_command(phrase))

    def test_segments_are_combined_before_matching_and_model_is_cached(self):
        backend = FakeBackend(result('la izquierda'), result('mira a'))
        engine = WhisperRecognizer(backend=backend)
        audio = Recording(array('h', [2000]*8000).tobytes(), 48000)
        recognized = engine.recognize(audio)
        self.assertEqual(recognized.text, 'mira a la izquierda')
        self.assertEqual(recognized.action.argument, 'izquierda')
        engine.recognize(audio)
        self.assertEqual(backend.models, 1)
        self.assertEqual(backend.rate, 16000)

    def test_low_confidence_keeps_text_but_rejects_action(self):
        engine = WhisperRecognizer(backend=FakeBackend(result('contento', 0.3)))
        recognized = engine.recognize(Recording(array('h', [2000]*1000).tobytes(), 16000))
        self.assertEqual(recognized.text, 'contento')
        self.assertIsNone(recognized.action)

    def test_silence_does_not_load_a_model(self):
        backend = FakeBackend(result('contento'))
        recognized = WhisperRecognizer(backend=backend).recognize(Recording(bytes(32000), 16000))
        self.assertIsNone(recognized.action)
        self.assertEqual(backend.models, 0)

    def test_missing_model_is_actionable(self):
        with self.assertRaisesRegex(RecognitionError, 'Falta Whisper local'):
            WhisperRecognizer(model_path=Path('missing-test-model')).recognize(
                Recording(array('h', [2000]*1000).tobytes(), 16000))


if __name__ == '__main__':
    unittest.main()
