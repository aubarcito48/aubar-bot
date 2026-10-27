import json
import threading
import unittest

from test_groq_client import CONFIG,KEY,Connection,completion,ControlledClient
import test_voice_conversation as voice_tests
from pc.aubar_control.ai_avatar import AvatarReply,parse_avatar_reply,normalize_reply
from pc.aubar_control.catalog import EXPRESSIONS,ANIMATIONS
from pc.aubar_control.conversation import Conversation
from pc.aubar_control.groq_client import GroqClient,GroqError,GroqService
from pc.aubar_control.protocol import DeviceError
from pc.aubar_control.voice_commands import VoiceAction


def structured(text='Respuesta humana.',kind='expression',identifier='contento'):
    return json.dumps(dict(text=text,avatar_type=kind,avatar_id=identifier))


class AvatarReplyTests(unittest.TestCase):
    def test_all_catalog_entries_are_validated_without_changing_spoken_text(self):
        for kind,catalog,command in [('expression',EXPRESSIONS,'EXPRESSION'),('animation',ANIMATIONS,'ANIMATION')]:
            for identifier in catalog:
                reply=parse_avatar_reply(structured(kind=kind,identifier=identifier))
                self.assertEqual(reply.action.command,command)
                self.assertEqual(reply.action.argument,identifier)
                self.assertEqual(reply.text,'Respuesta humana.')
                self.assertFalse(reply.fallback)

    def test_bad_or_mismatched_selection_falls_back_to_neutral_with_valid_text(self):
        for kind,identifier in [('expression','neutral\nMODE auto'),('animation','contento'),
                                ('LOOK','izquierda'),('expression',['neutral']),('expression',None)]:
            reply=parse_avatar_reply(structured(kind=kind,identifier=identifier))
            self.assertEqual((reply.action.command,reply.action.argument),('EXPRESSION','neutral'))
            self.assertTrue(reply.fallback)
            self.assertEqual(reply.text,'Respuesta humana.')
        payload=json.loads(structured());payload['command']='RESET'
        self.assertTrue(parse_avatar_reply(json.dumps(payload)).fallback)

    def test_invalid_json_or_text_is_rejected_instead_of_reading_metadata_aloud(self):
        for content in ('not JSON','[]',structured(text=''),structured(text='x'*2001),structured(text='x\x00')):
            with self.assertRaises((ValueError,TypeError)):
                parse_avatar_reply(content)
        reply=normalize_reply(AvatarReply('Hola',VoiceAction('EXPRESSION','contento','injected','derecha')))
        self.assertEqual(reply.action.argument,'neutral')

    def test_conversation_uses_schema_and_probe_keeps_plain_text(self):
        conversation=Conversation();request=conversation.prepare('Hola')
        connection=Connection(completion(structured()))
        reply=GroqClient(lambda *a,**k:connection).complete(CONFIG,request)
        self.assertEqual(reply.action.argument,'contento')
        body=json.loads(connection.requests[0][1]['body'])
        self.assertTrue(body['response_format']['json_schema']['strict'])
        self.assertIn('JSON',body['messages'][0]['content'])
        probe=Connection()
        self.assertIsInstance(GroqClient(lambda *a,**k:probe).complete(CONFIG,'Prueba'),str)
        self.assertNotIn('response_format',json.loads(probe.requests[0][1]['body']))

    def test_malformed_structured_response_is_safe_error_and_other_models_use_json_mode(self):
        request=Conversation().prepare('Hola')
        connection=Connection(completion('not JSON '+KEY))
        with self.assertRaises(GroqError) as caught:
            GroqClient(lambda *a,**k:connection).complete(CONFIG,request)
        self.assertNotIn(KEY,str(caught.exception))
        from pc.aubar_control.config import GroqConfig
        connection=Connection(completion(structured()))
        GroqClient(lambda *a,**k:connection).complete(GroqConfig(KEY,'other/model',2),request)
        self.assertEqual(json.loads(connection.requests[0][1]['body'])['response_format'],{'type':'json_object'})


class AvatarClient(ControlledClient):
    def __init__(self):
        super().__init__()
        self.answer=AvatarReply('Respuesta humana.',VoiceAction('EXPRESSION','contento','Contento'))

    def complete(self,config,text,*,cancel_event=None):
        super().complete(config,text,cancel_event=cancel_event)
        return self.answer


class AIAvatarPanelTests(unittest.TestCase):
    pump=voice_tests.VoiceConversationTests.pump
    start_auto=voice_tests.VoiceConversationTests.start_auto
    speak_auto=voice_tests.VoiceConversationTests.speak_auto
    question=voice_tests.VoiceConversationTests.question

    def setUp(self):
        voice_tests.VoiceConversationTests.setUp(self)
        self.app.ai_service.close();self.client=AvatarClient()
        self.app.ai_service=GroqService(self.client)
        self.session.version=4

    def tearDown(self):
        voice_tests.VoiceConversationTests.tearDown(self)

    def text_question(self):
        self.app.connect();self.pump(lambda:self.app.connected and not self.app.busy)
        self.app.ai_input.set('Hola');self.app.send_ai_message()
        self.pump(lambda:len(self.session.actions)==1 and not self.app.busy)

    def test_thinking_then_confirmed_expression_before_speaking_text_only(self):
        self.start_auto();self.question();self.speak_auto()
        self.pump(lambda:len(self.session.actions)==1 and not self.app.busy)
        self.assertEqual(self.session.actions[0].argument,'thinking')
        self.assertEqual(self.voice.calls,[])
        self.client.release.set();self.pump(lambda:len(self.voice.calls)==1)
        self.assertEqual([a.argument for a in self.session.actions],['thinking','contento'])
        self.assertEqual(self.app.values['expression'].get(),'Contento')
        self.assertEqual(self.voice.calls,['Respuesta humana.'])
        self.assertNotIn('avatar_id',self.app.conversation.transcript)

    def test_invalid_selection_uses_neutral_and_never_sends_unknown_usb(self):
        self.client.answer=AvatarReply('Texto válido.',VoiceAction('EXPRESSION','neutral\nMODE auto','Bad'))
        self.text_question();self.client.release.set()
        self.pump(lambda:len(self.session.actions)==2 and not self.app.busy)
        self.assertEqual([a.argument for a in self.session.actions],['thinking','neutral'])
        self.assertIn('Texto válido.',self.app.ai_response.get('1.0','end'))
        self.assertEqual(self.voice.calls,[])

    def test_manual_catalog_control_is_not_overwritten_by_late_model_answer_or_reset(self):
        self.text_question()
        self.app.catalog_choices['EXPRESSION'][0].set('Enojado');self.app.apply_catalog('EXPRESSION')
        self.pump(lambda:len(self.session.actions)==2 and not self.app.busy)
        self.client.release.set();self.pump(lambda:self.app._ai_future is None)
        self.app.new_conversation();self.root.update()
        self.assertEqual([a.argument for a in self.session.actions],['thinking','enojado'])
        self.assertEqual(self.app.values['expression'].get(),'Enojado')

    def test_reset_during_inflight_thinking_restores_neutral_and_drops_old_answer(self):
        gate=threading.Event();self.addCleanup(gate.set)
        original=self.session.apply_action
        def delayed(action):
            if action.argument=='thinking':gate.wait(2)
            return original(action)
        self.session.apply_action=delayed
        self.app.connect();self.pump(lambda:self.app.connected and not self.app.busy)
        self.app.ai_input.set('Hola');self.app.send_ai_message()
        self.pump(lambda:self.app._ai_avatar_inflight)
        self.app.new_conversation();gate.set();self.client.release.set()
        self.pump(lambda:self.app._ai_future is None and len(self.session.actions)==2 and not self.app.busy)
        self.assertEqual([a.argument for a in self.session.actions],['thinking','neutral'])
        self.assertEqual(self.app.conversation.turn_count,0)

    def test_api_error_restores_neutral_without_voice_or_failed_history(self):
        self.text_question();self.client.error=OSError(KEY);self.client.release.set()
        self.pump(lambda:self.app._ai_future is None and len(self.session.actions)==2 and not self.app.busy)
        self.assertEqual(self.session.actions[-1].argument,'neutral')
        self.assertEqual(self.app.conversation.turn_count,0)
        self.assertEqual(self.voice.calls,[])

    def test_usb_failure_keeps_valid_text_without_announcing_avatar_confirmation(self):
        self.text_question()
        original=self.session.apply_action
        def fail_final(action):
            if action.argument=='contento':raise DeviceError('Sin confirmación USB.')
            return original(action)
        self.session.apply_action=fail_final;self.client.release.set()
        self.pump(lambda:not self.app.connected and not self.app.busy)
        self.assertEqual(self.app.conversation.turn_count,1)
        self.assertIn('Respuesta humana.',self.app.ai_response.get('1.0','end'))
        self.assertIn('No se pudo confirmar',self.app.ai_avatar_message.get())

    def test_v2_skips_thinking_animation_and_uses_neutral_for_animation_answer(self):
        self.session.version=2
        self.client.answer=AvatarReply('Celebramos.',VoiceAction('ANIMATION','celebrate','Celebrar'))
        self.client.release.set()
        self.app.connect();self.pump(lambda:self.app.connected and not self.app.busy)
        self.app.ai_input.set('Hola');self.app.send_ai_message()
        self.pump(lambda:self.app._ai_future is None and len(self.session.actions)==1 and not self.app.busy)
        self.assertEqual(self.session.actions[0].argument,'neutral')

    def test_disconnect_cleans_owned_pose_and_late_text_reply_does_not_change_reconnected_avatar(self):
        self.text_question()
        self.app.disconnect();self.pump(lambda:not self.app.busy)
        self.assertEqual([a.argument for a in self.session.actions],['thinking','neutral'])
        self.app.connect();self.pump(lambda:self.app.connected and not self.app.busy)
        self.client.release.set();self.pump(lambda:self.app._ai_future is None)
        self.assertEqual([a.argument for a in self.session.actions],['thinking','neutral'])
        self.assertEqual(self.app.values['expression'].get(),'Neutral')
