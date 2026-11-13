import json
from threading import Event
import unittest
from unittest.mock import Mock,patch

from pc.aubar_control.ai_avatar import parse_avatar_reply
from pc.aubar_control.conversation import Conversation
from pc.aubar_control.groq_client import GroqClient,GroqError,GroqCancelled
from test_groq_client import CONFIG,Connection,completion


def direction(text):
    return json.dumps({'text':text,'avatar_type':'animation','avatar_id':'angry'})


class ContentDirectionTests(unittest.TestCase):
    def test_director_cannot_replace_approved_words(self):
        connections=iter((Connection(completion('Buenas tardes.')),Connection(completion(direction('Salí de acá.')))))
        reply=GroqClient(lambda *a,**k:next(connections)).complete(CONFIG,Conversation().prepare('Actuá un saludo.'))
        self.assertEqual(reply.text,'Buenas tardes.')
        self.assertTrue(reply.fallback)
        self.assertEqual(reply.action.argument,'neutral')

    def test_unavailable_director_preserves_text_without_reading_error_body(self):
        failed=Connection(b'private remote error',429)
        connections=iter((Connection(completion('Respuesta correcta.')),failed))
        reply=GroqClient(lambda *a,**k:next(connections)).complete(CONFIG,Conversation().prepare('Hola'))
        self.assertEqual(reply.text,'Respuesta correcta.')
        self.assertTrue(reply.fallback)
        self.assertEqual(failed.reads,0)
        self.assertEqual(len(failed.requests),1)

    def test_failed_content_does_not_start_direction(self):
        connection=Connection(status=500)
        factory=Mock(return_value=connection)
        with self.assertRaises(GroqError):
            GroqClient(factory).complete(CONFIG,Conversation().prepare('Hola'))
        self.assertEqual(factory.call_count,1)

    def test_stages_share_deadline_and_cancellation(self):
        client=GroqClient();cancel=Event()
        directed=parse_avatar_reply(direction('Hola.'))
        with patch.object(client,'_complete_once',side_effect=['Hola.',directed]) as complete,patch('pc.aubar_control.groq_client.time.monotonic',side_effect=[10,10.5]):
            result=client.complete(CONFIG,Conversation().prepare('Hola'),cancel_event=cancel)
        self.assertIs(result,directed)
        self.assertEqual(complete.call_args_list[1].args[0].timeout_seconds,1.5)
        self.assertIs(complete.call_args_list[1].kwargs['cancel_event'],cancel)
        self.assertEqual(complete.call_args_list[1].kwargs['performance_text'],'Hola.')
        def cancelled(*args,**kwargs):
            cancel.set();return 'Hola.'
        cancel.clear()
        with patch.object(client,'_complete_once',side_effect=cancelled) as complete:
            with self.assertRaises(GroqCancelled):
                client.complete(CONFIG,Conversation().prepare('Hola'),cancel_event=cancel)
        self.assertEqual(complete.call_count,1)
