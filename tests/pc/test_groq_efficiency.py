"""Deterministic provider-call counts; no key or live Groq request required."""
from dataclasses import replace
import json
from threading import Event
import unittest
from unittest.mock import Mock,patch

from pc.aubar_control.conversation import Conversation
from pc.aubar_control.groq_client import GroqClient,GroqCancelled,GroqError,GroqService
from pc.aubar_control.groq_efficiency import GroqEfficiency
from test_groq_client import CONFIG,Connection,completion
from test_content_direction import direction


class GroqEfficiencyTests(unittest.TestCase):
    def client(self,items):
        factory=Mock(side_effect=[Connection(item) for item in items])
        return GroqClient(factory),factory

    def test_identical_full_request_reuses_both_stages_and_counts_only_reported_usage(self):
        data=json.loads(completion('Hola.'))
        data['usage']={'prompt_tokens':100,'completion_tokens':25,'total_tokens':125,
            'prompt_tokens_details':{'cached_tokens':40}}
        client,factory=self.client([json.dumps(data).encode(),completion(direction('Hola.'))])
        request=Conversation().prepare('Hola')
        first=client.complete(CONFIG,request)
        second=client.complete(CONFIG,request)
        self.assertEqual(first,second)
        self.assertEqual(factory.call_count,2)
        stats=client.efficiency.snapshot()
        self.assertEqual((stats['calls'],stats['cache_hits'],stats['usage_responses']),(2,2,1))
        self.assertEqual((stats['total_tokens'],stats['cached_prompt_tokens']),(125,40))
        self.assertNotIn(CONFIG.api_key,repr(stats))
        self.assertNotIn('Hola',repr(stats))

    def test_new_context_key_model_and_payload_parameters_never_share_results(self):
        policy=GroqEfficiency()
        payload={'model':'a','messages':[{'role':'user','content':'same question'}],'temperature':.6}
        account,key=policy.keys('first',payload)
        generation,_,_=policy.lookup(account,key,reusable=True)
        policy.store(key,'original',generation)
        changes=[('second',payload),('first',{**payload,'model':'b'}),
            ('first',{**payload,'temperature':.7}),
            ('first',{**payload,'messages':[{'role':'assistant','content':'new context'},*payload['messages']]})]
        for credential,value in changes:
            a,k=policy.keys(credential,value)
            self.assertIsNone(policy.lookup(a,k,reusable=True)[1])
        client,factory=self.client([completion('Hola.'),completion(direction('Hola.')),
            completion('Otra respuesta.'),completion(direction('Otra respuesta.'))])
        conversation=Conversation()
        request=conversation.prepare('Hola')
        client.complete(CONFIG,request)
        conversation.commit(request,'Hola.')
        self.assertEqual(client.complete(CONFIG,conversation.prepare('Hola')).text,'Otra respuesta.')
        self.assertEqual(factory.call_count,4)

    def test_ttl_capacity_and_clear_during_request(self):
        now=[0]
        policy=GroqEfficiency(clock=lambda:now[0])
        generation=policy.lookup(b'a',b'k',reusable=True)[0]
        policy.store(b'k','answer',generation)
        now[0]=301
        self.assertIsNone(policy.lookup(b'a',b'k',reusable=True)[1])
        for i in range(70):
            policy.store(bytes([i]),'answer',generation)
        self.assertEqual(len(policy._cache),64)
        self.assertNotIn(bytes([0]),policy._cache)
        policy.clear_cache()
        policy.store(b'stale','old in-flight answer',generation)
        self.assertEqual(len(policy._cache),0)

    def test_429_waits_without_retry_or_reading_body_and_reset_cannot_bypass(self):
        now=[0]
        response=Connection(b'private error',429)
        response.getheader=lambda name:'90'
        factory=Mock(side_effect=[response,Connection(completion('Ready.'))])
        client=GroqClient(factory)
        client.efficiency=GroqEfficiency(clock=lambda:now[0])
        with self.assertRaises(GroqError):
            client.complete(CONFIG,'test')
        self.assertEqual(response.reads,0)
        client.clear_cache()
        with self.assertRaisesRegex(GroqError,'90 segundos'):
            client.complete(replace(CONFIG,model='another-model'),'test')
        self.assertEqual(factory.call_count,1)
        now[0]=91
        self.assertEqual(client.complete(CONFIG,'test'),'Ready.')
        self.assertEqual(factory.call_count,2)

    def test_failed_or_rewritten_direction_is_not_cached_but_content_is_preserved(self):
        client,factory=self.client([completion('Original.'),completion(direction('Wrong.')),
            completion(direction('Original.'))])
        request=Conversation().prepare('Say Original.')
        self.assertTrue(client.complete(CONFIG,request).fallback)
        self.assertFalse(client.complete(CONFIG,request).fallback)
        self.assertEqual(factory.call_count,3)
        self.assertEqual(client.efficiency.snapshot()['cache_hits'],1)

    def test_health_check_always_calls_provider_and_cancellation_beats_cache(self):
        client,factory=self.client([completion('Ready.'),completion('Ready.')])
        client.complete(CONFIG,'test')
        client.complete(CONFIG,'test')
        self.assertEqual(factory.call_count,2)
        client,factory=self.client([completion('Hola.'),completion(direction('Hola.'))])
        request=Conversation().prepare('Hola')
        client.complete(CONFIG,request)
        cancel=Event();cancel.set()
        with self.assertRaises(GroqCancelled):
            client.complete(CONFIG,request,cancel_event=cancel)
        self.assertEqual(factory.call_count,2)

    def test_local_director_reexecutes_locally_when_content_is_cached(self):
        from pc.aubar_control.ai_avatar import normalize_reply
        client,factory=self.client([completion('Hola.')])
        request=Conversation().prepare('Hola')
        with patch('pc.aubar_control.aubar_director.AubarDirector') as director:
            director.return_value.direct.return_value=normalize_reply('Hola.')
            for _ in range(2):
                client.complete(replace(CONFIG,director='local'),request)
            self.assertEqual(director.return_value.direct.call_count,2)
        self.assertEqual(factory.call_count,1)

    def test_invalid_usage_is_unknown_and_does_not_invent_tokens(self):
        policy=GroqEfficiency()
        for usage in (None,{}, {'prompt_tokens':True,'completion_tokens':1,'total_tokens':2}):
            policy.record(usage,failed=False,elapsed=.1)
        self.assertEqual(policy.snapshot()['usage_responses'],0)
        self.assertEqual(policy.snapshot()['total_tokens'],0)

    def test_invalid_spoken_content_never_enters_cache(self):
        client,factory=self.client([completion('bad\x00text'),completion('bad\x00text')])
        request=Conversation().prepare('Hola')
        for _ in range(2):
            with self.assertRaises(GroqError):
                client.complete(CONFIG,request)
        self.assertEqual(factory.call_count,2)
        self.assertEqual(client.efficiency.snapshot()['cache_hits'],0)

    def test_service_close_clears_cached_responses(self):
        client=Mock()
        service=GroqService(client)
        service.close()
        client.clear_cache.assert_called_once()


if __name__=='__main__':
    unittest.main()
