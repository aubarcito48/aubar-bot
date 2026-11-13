import unittest

from pc.aubar_control.speech_pronunciation import pronunciation_language, speech_speed


class PronunciationTests(unittest.TestCase):
    def test_spanish_and_voseo_use_latin_american_phonetics(self):
        for text in ['Hola, che. ¿Cómo andás? Soy Aubar.', 'Vos podés contar conmigo.',
                     'Estoy contento.', 'Vamos a abrir YouTube.', 'Listo.', 'BrotaIMS']:
            with self.subTest(text=text):
                self.assertEqual(pronunciation_language(text), 'es-419')

    def test_english_keeps_english_phonetics(self):
        for text in ["Hi, I'm Aubar. How can I help you today?", 'This is my new voice.',
                     'Open YouTube, please.', 'Thank you!', 'I am ready.']:
            with self.subTest(text=text):
                self.assertEqual(pronunciation_language(text), 'en-us')

    def test_speed_is_slightly_livelier_and_keeps_engine_limits(self):
        self.assertEqual(speech_speed(0), 1.08)
        self.assertLess(speech_speed(-5), speech_speed(0))
        self.assertEqual(speech_speed(10), 2.0)
