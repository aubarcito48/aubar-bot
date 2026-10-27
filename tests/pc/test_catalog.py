import json
from pathlib import Path
import unittest

from pc.aubar_control.catalog import CATALOG, EXPRESSIONS, ANIMATIONS
from pc.aubar_control.protocol import DeviceError, parse_status, encode_action
from pc.aubar_control.voice_commands import VoiceAction, match_command
import test_app

ROOT = Path(__file__).resolve().parents[2]


class CatalogTests(unittest.TestCase):
    def test_every_exported_expression_and_animation_has_an_id(self):
        source=json.loads((ROOT/'avatar-original/kirby.avatar.json').read_text(encoding='utf-8'))
        self.assertEqual(len(EXPRESSIONS),28)
        self.assertEqual(len(ANIMATIONS),23)
        self.assertEqual({x['source'] for x in CATALOG['expressions']},set(source['expressionOrder']))
        self.assertEqual(list(ANIMATIONS),source['animationOrder'])
        for group, command in ((EXPRESSIONS,'EXPRESSION'),(ANIMATIONS,'ANIMATION')):
            for identifier in group:
                self.assertEqual(encode_action(VoiceAction(command,identifier,'')),
                                 f'{command} {identifier}\n'.encode())

    def test_all_catalog_labels_have_explicit_voice_commands(self):
        for identifier,label in EXPRESSIONS.items():
            self.assertEqual(match_command('expresión '+label).argument,identifier)
        for identifier,label in ANIMATIONS.items():
            for phrase in (label,'animación '+label,'Kirby '+label+' por favor'):
                action=match_command(phrase)
                self.assertIsNotNone(action,phrase)
                self.assertEqual((action.command,action.argument),('ANIMATION',identifier))
        for unknown in ('no quiero celebrar','hoy voy a trabajar','pensar y reír','ponete contento'):
            self.assertIsNone(match_command(unknown))

    def test_v3_status_with_long_ids_and_invalid_catalog(self):
        status=parse_status('OK STATUS mode=manual expression=asymmetric-down-right look=centro animation=searching')
        self.assertEqual(status.animation,'searching')
        self.assertEqual(status.expression,'asymmetric-down-right')
        for suffix in ('animation=bogus','animation=idle animation=happy','animation=idle extra=1'):
            with self.assertRaises(DeviceError):
                parse_status('OK STATUS mode=auto expression=neutral look=centro '+suffix)


class CatalogAppTests(unittest.TestCase):
    setUp = test_app.AppTests.setUp
    tearDown = test_app.AppTests.tearDown
    pump = test_app.AppTests.pump
    start_microphone = test_app.AppTests.start_microphone
    def test_catalog_applies_exactly_once_and_updates_animation(self):
        self.app.connect()
        self.pump(lambda:not self.app.busy)
        choice,_=self.app.catalog_choices['ANIMATION']
        choice.set('Celebrar')
        self.app.apply_catalog('ANIMATION')
        self.app.apply_catalog('ANIMATION')  # double click while waiting
        self.pump(lambda:not self.app.busy)
        self.assertEqual(len(self.session.actions),1)
        self.assertEqual(self.session.actions[0].argument,'celebrate')
        self.assertEqual(self.app.animation_value.get(),'Animación: Celebrar')
        self.assertIn('Confirmado',self.app.catalog_message.get())
        self.app.disconnect()
        self.pump(lambda:not self.app.busy)
        self.app.apply_catalog('ANIMATION')
        self.assertEqual(len(self.session.actions),1)

    def test_catalog_does_not_interrupt_active_capture(self):
        self.app.connect()
        self.pump(lambda:not self.app.busy)
        self.start_microphone()
        self.app.apply_catalog('ANIMATION')
        self.assertEqual(self.session.actions,[])
