import unittest
import test_app
from test_session import FakeSerial
from test_recognition import FakeBackend, result

from pc.aubar_control.catalog import EXPRESSIONS, ANIMATIONS
from pc.aubar_control.voice_commands import VoiceAction, match_command
from pc.aubar_control.protocol import DeviceError, encode_action
from pc.aubar_control.session import DeviceSession
from pc.aubar_control.recognition import LocalRecognizer
from pc.aubar_control.audio import Recording
from array import array


class CombinationTests(unittest.TestCase):
    def test_all_153_catalog_combinations_and_single_commands(self):
        for command, catalog in (('EXPRESSION',EXPRESSIONS),('ANIMATION',ANIMATIONS)):
            for identifier,label in catalog.items():
                common = command=='EXPRESSION' and identifier in ('neutral','contento','sorprendido','dormido','enojado')
                spoken = 'expresión '+label if command=='EXPRESSION' and not common else label
                self.assertEqual(match_command('Aubar '+spoken).argument,identifier)
                for direction in ('izquierda','centro','derecha'):
                    location='al centro' if direction=='centro' else 'a la '+direction
                    suffixes=(location,'mirando '+location,'y '+direction,'y mira '+location)
                    if command=='ANIMATION' or common:
                        suffixes=(direction,)+suffixes
                    for suffix in suffixes:
                        phrase='Aubar '+spoken+' '+suffix
                        action=match_command(phrase)
                        self.assertIsNotNone(action,phrase)
                        self.assertEqual((action.command,action.argument,action.look),(command,identifier,direction),phrase)
                        self.assertEqual(encode_action(action),f'{command} {identifier} {direction}\n'.encode())
                        self.assertLessEqual(len(encode_action(action))-1,64)
        self.assertEqual(match_command('Aubar derecha').command,'LOOK')
        self.assertEqual(match_command('Aubar enojado').argument,'enojado')
        self.assertEqual(match_command('Aubar enojado izquierda').look,'izquierda')

    def test_exact_expression_names_win_over_suffixes_and_ambiguous_phrases_reject(self):
        action=match_command('Aubar expresion mirada derecha')
        self.assertEqual(action.command,'EXPRESSION')
        self.assertIsNone(action.look)
        self.assertEqual(match_command('expresión enojado izquierda').argument,'angry-left')
        self.assertEqual(match_command('expresión enojado izquierda mirando a la derecha').look,'derecha')
        for phrase in ('enojado derecha izquierda','enojado y contento','celebrar izquierda y derecha',
                       'no enojado derecha','enojado derecha ahora','mira izquierda derecha',
                       'modo automatico derecha','aubar aubar enojado derecha'):
            self.assertIsNone(match_command(phrase),phrase)
        with self.assertRaises(DeviceError):
            encode_action(VoiceAction('MODE','auto','invalid','derecha'))
        with self.assertRaises(DeviceError):
            encode_action(VoiceAction('EXPRESSION','enojado','invalid','derecha\nMODE auto'))

    def test_combination_is_one_serial_message_and_ack_must_confirm_both_parts(self):
        port=FakeSerial(version=4)
        session=DeviceSession(lambda **_:port,timeout=.02)
        session.connect('COM3')
        action=match_command('aubar celebrar izquierda')
        session.apply_action(action)
        self.assertEqual(port.requests.count(b'ANIMATION celebrate izquierda\n'),1)
        self.assertNotIn(b'LOOK izquierda\n',port.requests)
        port.ack=b'OK APPLIED ANIMATION celebrate\n'
        with self.assertRaisesRegex(DeviceError,'no se reenviará'):
            session.apply_action(action)
        self.assertFalse(session.connected)
        self.assertEqual(port.requests.count(b'ANIMATION celebrate izquierda\n'),2)

    def test_old_firmware_rejects_combination_without_a_partial_action(self):
        for version in (2,3):
            port=FakeSerial(version=version)
            session=DeviceSession(lambda **_:port,timeout=.02)
            session.connect('COM3')
            baseline=len(port.requests)
            with self.assertRaisesRegex(DeviceError,'v4'):
                session.apply_action(match_command('enojado derecha'))
            self.assertEqual(len(port.requests),baseline)
            self.assertTrue(session.connected)
            session.close()

    def test_automatic_recognition_requires_aubar_for_the_whole_combination(self):
        recording=Recording(array('h',[2000]*16000).tobytes(),16000)
        for text,expected in (('aubar enojado derecha','derecha'),('aubar celebrar izquierda','izquierda'),
                              ('enojado derecha',None),('aubar enojado derecha izquierda',None)):
            engine=LocalRecognizer(backend=FakeBackend(result(text)))
            action=engine.recognize_automatic(recording).action
            self.assertEqual(action.look if action else None,expected)


class CombinationAppTests(unittest.TestCase):
    setUp=test_app.AppTests.setUp
    tearDown=test_app.AppTests.tearDown
    pump=test_app.AppTests.pump
    start_microphone=test_app.AppTests.start_microphone
    speak=test_app.AppTests.speak

    def test_voice_pipeline_sends_one_combined_action_and_shows_confirmed_state(self):
        from pc.aubar_control.recognition import RecognitionResult
        self.app.connect()
        self.pump(lambda:not self.app.busy)
        self.recognizer.result=RecognitionResult(
            'aubar celebrar izquierda',match_command('celebrar izquierda'),'')
        self.speak()
        self.pump(lambda:len(self.session.actions)==1 and not self.app.busy and self.app.audio_phase=='idle')
        self.assertEqual(self.session.actions[0].look,'izquierda')
        self.assertEqual(self.app.values['look'].get(),'Izquierda')
        self.assertEqual(self.app.animation_value.get(),'Animación: Celebrar')
        self.assertIn('Confirmado',self.app.recognition_message.get())
