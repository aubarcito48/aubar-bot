import json
import unittest

import test_app
from test_groq_client import CONFIG, KEY, Connection, ControlledClient
from pc.aubar_control.config import load_groq_config
from pc.aubar_control.conversation import Conversation, SYSTEM_PROMPT
from pc.aubar_control.groq_client import GroqClient, GroqService


class ConversationTests(unittest.TestCase):
    def test_prepare_is_transactional_and_followup_contains_personality_and_complete_turn(self):
        conversation=Conversation()
        first=conversation.prepare('Mi color preferido es violeta.')
        self.assertEqual(conversation.turn_count,0)
        self.assertEqual(first.messages[0].content,SYSTEM_PROMPT)
        self.assertEqual([m.role for m in first.messages],['system','user'])
        self.assertNotIn('violeta',repr(first))
        self.assertTrue(conversation.commit(first,'Lo recuerdo en esta conversación.'))
        second=conversation.prepare('¿Cuál es mi color preferido?')
        self.assertEqual([m.role for m in second.messages],['system','user','assistant','user'])
        self.assertEqual(second.messages[1].content,'Mi color preferido es violeta.')
        self.assertEqual(conversation.turn_count,1)

    def test_history_limits_remove_whole_oldest_pairs(self):
        conversation=Conversation()
        for i in range(10):
            conversation.commit(conversation.prepare(f'Mensaje {i}'),f'Respuesta {i}')
        self.assertEqual(conversation.turn_count,6)
        self.assertNotIn('Mensaje 3',conversation.transcript)
        self.assertIn('Mensaje 4',conversation.transcript)
        for i in range(10):
            conversation.commit(conversation.prepare(str(i)*1000),'a'*2000)
            self.assertLessEqual(conversation.character_count,12000)
        messages=conversation.prepare('Seguimiento').messages
        self.assertEqual([m.role for m in messages[1:-1]],['user','assistant']*conversation.turn_count)

    def test_reset_and_revision_reject_late_and_duplicate_answers(self):
        conversation=Conversation()
        old=conversation.prepare('Anterior')
        conversation.reset()
        self.assertFalse(conversation.commit(old,'Respuesta tardía'))
        fresh=conversation.prepare('Nueva')
        self.assertTrue(conversation.commit(fresh,'Respuesta nueva'))
        self.assertFalse(conversation.commit(fresh,'Respuesta duplicada'))
        self.assertEqual(conversation.turn_count,1)
        self.assertNotIn('tardía',conversation.transcript)
        self.assertNotIn('duplicada',conversation.transcript)

    def test_invalid_input_or_answer_does_not_enter_history(self):
        conversation=Conversation()
        for text in ('','  ','x'*1001,'hola\x00',None):
            with self.assertRaises(ValueError):
                conversation.prepare(text)
        request=conversation.prepare('Pregunta')
        for answer in ('','a'*2001,None):
            with self.assertRaises(ValueError):
                conversation.commit(request,answer)
        self.assertEqual(conversation.turn_count,0)

    def test_transport_sends_bounded_context_and_redacts_key_in_all_messages(self):
        conversation=Conversation()
        conversation.commit(conversation.prepare('Pregunta '+KEY),'Respuesta '+KEY)
        request=conversation.prepare('Seguimiento '+KEY)
        connection=Connection()
        GroqClient(lambda *a,**k:connection).complete(CONFIG,request)
        payload=json.loads(connection.requests[0][1]['body'])
        self.assertEqual([m['role'] for m in payload['messages']],['system','user','assistant','user'])
        self.assertNotIn(KEY,json.dumps(payload))
        self.assertIn('[credencial oculta]',payload['messages'][-1]['content'])


class ConversationPanelTests(unittest.TestCase):
    pump=test_app.AppTests.pump

    def setUp(self):
        test_app.AppTests.setUp(self)
        self.app.ai_service.close()
        self.client=ControlledClient()
        self.app.ai_service=GroqService(self.client)
        self.app.config_loader=lambda:load_groq_config(None,{'GROQ_API_KEY':KEY})
        self.app.reload_groq_configuration()

    def tearDown(self):
        self.client.release.set()
        test_app.AppTests.tearDown(self)

    def send(self,text):
        self.app.ai_input.set(text)
        self.app.send_ai_message()
        self.pump(lambda:self.app._ai_future is None)

    def test_followups_use_context_and_connection_test_does_not_enter_history(self):
        self.client.release.set()
        self.send('Me llamo Nahuel.')
        self.send('¿Cómo me llamo?')
        self.assertEqual(self.app.conversation.turn_count,2)
        self.assertEqual(self.client.calls[1].messages[1].content,'Me llamo Nahuel.')
        self.assertIn('Vos: Me llamo Nahuel.',self.app.ai_response.get('1.0','end'))
        self.assertEqual(self.app.speech.calls,[])
        self.app.test_groq();self.pump(lambda:self.app._ai_future is None)
        self.assertEqual(self.app.conversation.turn_count,2)
        self.app.new_conversation()
        self.assertEqual(self.app.conversation.turn_count,0)
        self.assertEqual(self.app.ai_response.get('1.0','end').strip(),'')

    def test_failure_preserves_previous_context_and_input_for_retry(self):
        self.client.release.set()
        self.send('Primero')
        self.client.error=OSError(KEY)
        self.send('Mensaje fallido')
        self.assertEqual(self.app.conversation.turn_count,1)
        self.assertNotIn('Mensaje fallido',self.app.conversation.transcript)
        self.assertEqual(self.app.ai_input.get(),'Mensaje fallido')
        self.client.error=None
        self.send('Reintento')
        self.assertEqual(self.app.conversation.turn_count,2)
        self.assertNotIn('Mensaje fallido',[m.content for m in self.client.calls[-1].messages])

    def test_new_conversation_discards_inflight_answer_and_next_query_has_no_old_context(self):
        self.client.release.set();self.send('Antes del reinicio')
        self.client.release.clear();self.client.started.clear()
        self.app.ai_input.set('Pendiente');self.app.send_ai_message()
        self.assertTrue(self.client.started.wait(1))
        self.app.new_conversation()
        self.client.release.set()
        self.pump(lambda:self.app._ai_future is None)
        self.assertEqual(self.app.conversation.turn_count,0)
        self.assertEqual(self.app.ai_response.get('1.0','end').strip(),'')
        self.send('Después del reinicio')
        self.assertEqual([m.role for m in self.client.calls[-1].messages],['system','user'])

    def test_reload_and_close_clear_context_and_invalidate_pending_turn(self):
        self.client.release.set();self.send('Antes de recargar')
        self.client.release.clear();self.client.started.clear()
        self.app.ai_input.set('Pendiente');self.app.send_ai_message()
        self.assertTrue(self.client.started.wait(1))
        pending=self.client.calls[-1]
        self.app.reload_groq_configuration()
        self.client.release.set();self.pump(lambda:self.app._ai_future is None)
        self.assertEqual(self.app.conversation.turn_count,0)
        self.assertFalse(self.app.conversation.commit(pending,'Tardía'))
        self.send('Antes de cerrar')
        self.app.close()
        self.assertEqual(self.app.conversation.turn_count,0)
