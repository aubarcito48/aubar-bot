from dataclasses import replace
from threading import Event
import unittest
from unittest.mock import Mock, patch
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pc.aubar_control.aubar_director import AubarDirector, direct_reply
from pc.aubar_control.ai_avatar import AvatarReply, parse_segments, safe_avatar_action
from pc.aubar_control.catalog import EXPRESSIONS, ANIMATIONS
from pc.aubar_control.config import load_groq_config
from pc.aubar_control.conversation import Conversation
from pc.aubar_control.director_encoder import instruction
from pc.aubar_control.groq_client import GroqClient, GroqCancelled
from test_groq_client import CONFIG, Connection, completion
from pc.aubar_control import aubar_director, director_encoder


class AubarDirectorTests(unittest.TestCase):
    def test_changed_catalog_or_weights_are_rejected_before_inference(self):
        import numpy as np
        with TemporaryDirectory() as folder:
            path = Path(folder)
            np.savez_compressed(path/'classifier.npz', coefficient=np.zeros((2,384)), intercept=np.zeros(2))
            payload = (path/'classifier.npz').read_bytes()
            metadata = {'feature_version': aubar_director.FEATURE_VERSION, 'encoder_revision': director_encoder.REVISION,
                        'catalog_sha256': aubar_director.catalog_hash(), 'classifier_sha256': hashlib.sha256(payload).hexdigest(),
                        'model_type':'logistic-regression', 'labels':['ANIMATION:angry','EXPRESSION:neutral'],
                        'confidence_threshold':.5, 'margin_threshold':.1, 'max_depth':18}
            (path/'model.json').write_text(json.dumps(metadata), encoding='utf8')
            with patch.object(aubar_director, 'WEIGHTS', path):
                try:
                    aubar_director._model.cache_clear()
                    self.assertEqual(aubar_director._model()[0]['labels'], metadata['labels'])
                    (path/'classifier.npz').write_bytes(payload+b'changed')
                    aubar_director._model.cache_clear()
                    with self.assertRaises(ValueError): aubar_director._model()
                    (path/'classifier.npz').write_bytes(payload)
                    metadata['catalog_sha256']='changed'
                    (path/'model.json').write_text(json.dumps(metadata), encoding='utf8')
                    aubar_director._model.cache_clear()
                    with self.assertRaises(ValueError): aubar_director._model()
                finally:
                    aubar_director._model.cache_clear()

    def test_missing_encoder_never_downloads_during_a_response(self):
        with TemporaryDirectory() as folder, patch.object(director_encoder, 'FOLDER', Path(folder)), \
             patch('urllib.request.urlopen', side_effect=AssertionError('No inference downloads')):
            director_encoder._encoder.cache_clear()
            try:
                result=direct_reply('Texto aprobado.', 'Decime enojado: "Hola."')
                self.assertEqual(result.origin, 'model-unavailable')
                self.assertEqual(result.reply.text, 'Texto aprobado.')
            finally:
                director_encoder._encoder.cache_clear()
    def test_own_full_catalog_is_available_without_a_classifier_or_network(self):
        with patch('pc.aubar_control.aubar_director.predict_style', side_effect=AssertionError('explicit catalog needs no ML')):
            for kind, catalog in [('EXPRESSION', EXPRESSIONS), ('ANIMATION', ANIMATIONS)]:
                for identifier, label in catalog.items():
                    request = ('expresión ' if kind=='EXPRESSION' else 'animación ') + label
                    result = direct_reply('Estas palabras se conservan.', request)
                    self.assertEqual((result.reply.action.command, result.reply.action.argument), (kind, identifier), request)
                    self.assertEqual(result.reply.text, 'Estas palabras se conservan.')
                    self.assertEqual(result.origin, 'explicit-catalog')

    def test_visual_director_never_dispatches_functions_modes_or_looks(self):
        with patch('pc.aubar_control.aubar_director.predict_style', return_value=('EXPRESSION:neutral', .99, True)):
            for question in ['modo automático', 'mirá a la izquierda', 'abrí YouTube', 'borra todo']:
                result = direct_reply('Respuesta aprobada.', question)
                self.assertEqual(result.reply.action.command, 'EXPRESSION')
                self.assertEqual(result.reply.action.argument, 'neutral')

    def test_low_confidence_and_missing_model_preserve_text_and_neutral(self):
        for prediction in [('ANIMATION:angry', .3, False), ValueError('model mismatch')]:
            options = {'side_effect': prediction} if isinstance(prediction, Exception) else {'return_value': prediction}
            with patch('pc.aubar_control.aubar_director.predict_style', **options):
                result = direct_reply('¡Estoy muy bien, Nahuel!', 'Decilo con una actuación.')
                self.assertTrue(result.reply.fallback)
                self.assertEqual(result.reply.text, '¡Estoy muy bien, Nahuel!')
                self.assertEqual(result.reply.action.argument, 'neutral')

    def test_onyx_profiles_are_bounded_and_spoken_words_never_include_delivery(self):
        for identifier in ANIMATIONS:
            with patch('pc.aubar_control.aubar_director.predict_style', return_value=('ANIMATION:'+identifier, .95, True)):
                reply = direct_reply('¡Estoy feliz!', 'Quiero una interpretación.').reply
                validated = parse_segments([s.payload() for s in reply.segments], reply.text)
                self.assertEqual(validated[0].text, '¡Estoy feliz!')
                self.assertEqual(validated[0].action.argument, identifier)

    def test_unknown_class_abstains_and_literal_content_is_not_a_style_instruction(self):
        with patch('pc.aubar_control.aubar_director.predict_style', return_value=('ANIMATION:inventado', .99, True)):
            self.assertEqual(direct_reply('Hola.', 'Un pedido.').reply.action.argument, 'neutral')
        self.assertEqual(instruction('Decime enojado: "Estoy feliz y contento."'), 'Decime enojado:')

    def test_local_mode_makes_one_content_request_and_never_calls_remote_director(self):
        connection = Connection(completion('Texto aprobado.'))
        factory = Mock(return_value=connection)
        with patch.object(AubarDirector, 'direct', return_value=direct_reply('Texto aprobado.', 'expresión neutral').reply):
            reply = GroqClient(factory).complete(replace(CONFIG, director='local'), Conversation().prepare('Hola'))
        self.assertEqual(reply.text, 'Texto aprobado.')
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(len(connection.requests), 1)

    def test_local_director_cannot_replace_content_and_cancellation_still_wins(self):
        action, _ = safe_avatar_action('EXPRESSION', 'neutral')
        client = GroqClient()
        with patch.object(client, '_complete_once', return_value='Texto original.'), \
             patch.object(AubarDirector, 'direct', return_value=AvatarReply('Otro texto.', action)):
            reply = client.complete(replace(CONFIG, director='local'), Conversation().prepare('Hola'))
            self.assertEqual(reply.text, 'Texto original.')
            self.assertTrue(reply.fallback)
        cancel = Event()
        def cancelled(*args, **kwargs):
            cancel.set()
            return AvatarReply('Texto original.', action)
        with patch.object(client, '_complete_once', return_value='Texto original.'), patch.object(AubarDirector, 'direct', side_effect=cancelled):
            with self.assertRaises(GroqCancelled):
                client.complete(replace(CONFIG, director='local'), Conversation().prepare('Hola'), cancel_event=cancel)

    def test_director_config_is_explicit_and_invalid_mode_is_rejected(self):
        state = load_groq_config(None, {'GROQ_API_KEY':'synthetic-token', 'AUBAR_DIRECTOR':'local'})
        self.assertEqual(state.config.director, 'local')
        self.assertFalse(load_groq_config(None, {'GROQ_API_KEY':'synthetic-token', 'AUBAR_DIRECTOR':'unknown'}).ready)
