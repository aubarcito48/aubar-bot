from dataclasses import replace
import json
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from pc.aubar_control.config import GroqConfig,load_groq_config,validate_source_url
from pc.aubar_control.conversation import Conversation
from pc.aubar_control.connected_sources import ConnectedSources,SourcesCancelled,requested_sources,MAX_BYTES
from pc.aubar_control.groq_client import GroqClient,GroqCancelled
from test_groq_client import Connection,completion,CONFIG
from test_content_direction import direction


class SourceConnection(Connection):
    def __init__(self,value,status=200,content_type='application/json'):
        super().__init__(json.dumps(value).encode(),status)
        self.content_type=content_type

    def getheader(self,name,default=None):
        return self.content_type if name.lower()=='content-type' else default


def source_config(**kwargs):
    return replace(CONFIG,portfolio_api_url='https://portfolio.example/api/v1/',
        whatsapp_health_url='http://127.0.0.1:3000/health',**kwargs)


class ConnectedSourcesTests(unittest.TestCase):
    def request(self,text):
        return Conversation().prepare(text)

    def test_url_configuration_is_read_only_and_health_is_loopback_only(self):
        for health,urls in ((False,('https://portfolio.example/api/v1/', 'http://localhost:8000/api/v1/')),
                           (True,('http://127.0.0.1:3000/health','http://[::1]:3000/health'))):
            for url in urls:
                self.assertEqual(validate_source_url(url,health=health),url)
        for url in ('http://remote.example/api/v1/','https://user:secret@host/api/v1/',
                    'https://host/api/v1/chat/','https://host/admin/','https://host/api/v1/?x=1',
                    'https://host/api/v1/#x','https://host:99999/api/v1/','https://host/\\api/v1/'):
            with self.assertRaises(ValueError):
                validate_source_url(url,health=False)
        with self.assertRaises(ValueError):
            validate_source_url('https://remote.example/health',health=True)
        state=load_groq_config(None,{'GROQ_API_KEY':'synthetic',
            'AUBAR_PORTFOLIO_API_URL':'https://host/api/v1/',
            'AUBAR_WHATSAPP_HEALTH_URL':'http://localhost:3000/health'})
        self.assertTrue(state.ready)
        self.assertEqual(state.config.whatsapp_health_url,'http://localhost:3000/health')
        state=load_groq_config(None,{'GROQ_API_KEY':'synthetic',
            'AUBAR_WHATSAPP_HEALTH_URL':'https://user:private@host/health'})
        self.assertFalse(state.ready)
        self.assertNotIn('private',state.message)

    def test_router_is_bounded_on_demand_and_tracks_short_followup(self):
        self.assertEqual(requested_sources(self.request('Hola, decí buenas tardes'))[0],[])
        sections,wsp,lang=requested_sources(self.request('Tell me about projects and technologies'))
        self.assertEqual(sections,['proyectos','tecnologias'])
        self.assertEqual(lang,'en')
        self.assertFalse(wsp)
        self.assertTrue(requested_sources(self.request('Estado del bot de wsp'))[1])
        conversation=Conversation()
        conversation.commit(conversation.prepare('Qué proyectos hay?'),'Listado')
        self.assertEqual(requested_sources(conversation.prepare('¿Y cuáles usan Python?'))[0],['proyectos'])
        self.assertEqual(requested_sources(conversation.prepare('Y cuáles usan Python?'))[0],['proyectos'])

    def test_portfolio_uses_get_without_auth_or_chat_and_caches_public_data_only(self):
        response=SourceConnection({'count':1,'next':None,'previous':None,
            'results':[{'name':'Aubar','summary':'Own project','image':'large-image'}]})
        factory=Mock(return_value=response)
        sources=ConnectedSources(https_factory=factory)
        request=self.request('Qué proyectos tiene el portfolio?')
        # Explicit two sources: provide only projects in this transport check.
        request=replace(request,question='Proyectos')
        first=sources.context(source_config(),request,Event())
        second=sources.context(source_config(),request,Event())
        self.assertEqual(first,second)
        self.assertEqual(factory.call_count,1)
        args,kwargs=response.requests[0]
        self.assertEqual(args,('GET','/api/v1/proyectos/?lang=es&page_size=100'))
        self.assertNotIn('Authorization',kwargs['headers'])
        self.assertNotIn('large-image',first[0].content)
        self.assertIn('Aubar',first[0].content)
        self.assertEqual(len(response.requests),1)

    def test_whatsapp_disconnected_health_is_valid_and_no_contacts_are_exposed(self):
        connection=SourceConnection({'status':'waiting_for_qr','contacts':['private']},503)
        factory=Mock(return_value=connection)
        sources=ConnectedSources(http_factory=factory)
        data=sources.context(source_config(),self.request('Estado de WhatsApp'),Event())[0].content
        self.assertIn('waiting_for_qr',data)
        self.assertNotIn('private',data)
        self.assertEqual(connection.requests[0][0],('GET','/health'))

    def test_partial_lists_preserve_dates_and_never_follow_remote_links(self):
        response=SourceConnection({'count':101,'next':'https://untrusted.example/private',
            'results':[{'title':'Published experience','startDate':'2025-01-01',
                'endDate':None,'isCurrent':True,'private_key':'excluded'}]})
        factory=Mock(return_value=response)
        sources=ConnectedSources(https_factory=factory)
        content=sources.context(source_config(),self.request('Experiencia'),Event())[0].content
        value=json.loads(content)['external_read_only_data']['portfolio_experiencias']
        self.assertTrue(value['partial'])
        self.assertEqual(value['data']['results'][0]['startDate'],'2025-01-01')
        self.assertTrue(value['data']['results'][0]['isCurrent'])
        self.assertNotIn('excluded',content)
        self.assertNotIn('untrusted.example',content)
        self.assertEqual(factory.call_count,1)

    def test_shared_source_deadline_and_cancellation_before_groq(self):
        now=[0]
        response=SourceConnection({'name':'Late'})
        response.connect=lambda:now.__setitem__(0,7)
        sources=ConnectedSources(https_factory=lambda *a,**k:response,clock=lambda:now[0])
        content=sources.context(replace(source_config(),source_timeout_seconds=1),self.request('Perfil'),Event())[0].content
        self.assertIn('unavailable',content)
        self.assertEqual(response.requests,[])
        factory=Mock()
        sources=Mock()
        sources.context.side_effect=SourcesCancelled
        client=GroqClient(factory,sources=sources)
        with self.assertRaises(GroqCancelled):
            client.complete(source_config(),self.request('Perfil'))
        factory.assert_not_called()

    def test_invalid_redirect_oversize_and_unexpected_data_fail_without_leaking_body(self):
        for connection in (SourceConnection({'secret':'private'},302),
                           SourceConnection({'secret':'private'},200,'text/html'),
                           SourceConnection({'status':'unrecognized','secret':'private'}),
                           SourceConnection({'status':'connected','padding':'x'*MAX_BYTES})):
            with self.subTest(connection=connection):
                sources=ConnectedSources(http_factory=lambda *a,**k:connection)
                result=sources.context(source_config(),self.request('WhatsApp'),Event())[0].content
                self.assertIn('unavailable',result)
                self.assertNotIn('private',result)

    def test_expiration_invalidation_and_failed_source_cooldown(self):
        now=[0]
        factory=Mock(side_effect=[SourceConnection({'name':'Old'}),SourceConnection({'name':'New'}),
            SourceConnection({},500),SourceConnection({'name':'After'})])
        sources=ConnectedSources(https_factory=factory,clock=lambda:now[0])
        request=self.request('Perfil')
        self.assertIn('Old',sources.context(source_config(),request,Event())[0].content)
        now[0]=61
        self.assertIn('New',sources.context(source_config(),request,Event())[0].content)
        sources.clear_cache()
        self.assertIn('unavailable',sources.context(source_config(),request,Event())[0].content)
        self.assertIn('unavailable',sources.context(source_config(),request,Event())[0].content)
        self.assertEqual(factory.call_count,3)
        now[0]=72
        self.assertIn('After',sources.context(source_config(),request,Event())[0].content)

    def test_cancellation_and_greetings_make_no_source_requests(self):
        factory=Mock()
        sources=ConnectedSources(https_factory=factory,http_factory=factory)
        self.assertEqual(sources.context(source_config(),self.request('Hola'),Event()),())
        cancel=Event();cancel.set()
        with self.assertRaises(SourcesCancelled):
            sources.context(source_config(),self.request('Perfil'),cancel)
        factory.assert_not_called()

    def test_source_context_enters_only_content_stage_not_direction_or_history(self):
        source=SourceConnection({'count':1,'next':None,'results':[{'name':'Known project'}]})
        sources=ConnectedSources(https_factory=lambda *a,**k:source)
        content=Connection(completion('Known project.'))
        acting=Connection(completion(direction('Known project.')))
        transport=Mock(side_effect=[content,acting])
        client=GroqClient(transport,sources=sources)
        conversation=Conversation()
        request=conversation.prepare('Proyectos')
        reply=client.complete(replace(source_config(),timeout_seconds=5),request)
        self.assertEqual(reply.text,'Known project.')
        payload=json.loads(content.requests[0][1]['body'])
        self.assertIn('el modelo no puede ejecutarlo',payload['messages'][0]['content'])
        self.assertIn('Known project',payload['messages'][1]['content'])
        self.assertEqual(payload['messages'][-1]['content'],'Proyectos')
        director=json.loads(acting.requests[0][1]['body'])
        self.assertNotIn('external_read_only_data',json.dumps(director))
        self.assertNotIn('external_read_only_data',repr(request.messages))
        self.assertEqual(transport.call_count,2)

    def test_screenshot_queries_route_to_the_published_owner_and_current_data_follow_old_denial(self):
        conversation=Conversation()
        first=conversation.prepare('conta sobre nahuel')
        self.assertEqual(requested_sources(first)[0],['perfil'])
        conversation.commit(first,'¿A qué Nahuel te referís?')
        request=conversation.prepare('contame sobre el portfolio de nahuel argandoña')
        self.assertEqual(requested_sources(request)[0],['perfil','proyectos'])
        responses=iter([SourceConnection({'name':'Nahuel Argandoña','specialty':'Desarrollador full stack'}),
            SourceConnection({'count':1,'next':None,'results':[{'name':'StitchWeather'}]})])
        sources=ConnectedSources(https_factory=lambda *a,**k:next(responses))
        content=Connection(completion('Nahuel es desarrollador full stack y creó StitchWeather.'))
        acting=Connection(completion(direction('Nahuel es desarrollador full stack y creó StitchWeather.')))
        transport=Mock(side_effect=[content,acting])
        client=GroqClient(transport,sources=sources)
        reply=client.complete(source_config(),request)
        self.assertIn('StitchWeather',reply.text)
        payload=json.loads(content.requests[0][1]['body'])
        self.assertEqual(payload['messages'][-3]['content'],'¿A qué Nahuel te referís?')
        self.assertIn('Nahuel Argandoña',payload['messages'][-2]['content'])
        self.assertIn('StitchWeather',payload['messages'][-2]['content'])
        self.assertIn('no preguntes a qué Nahuel',payload['messages'][0]['content'])
        self.assertIn('Fuentes consultadas',sources.status())

    def test_cold_response_can_take_more_than_four_seconds_within_its_own_budget(self):
        now=[0]
        response=SourceConnection({'name':'Nahuel'})
        getresponse=response.getresponse
        def cold():
            now[0]=12
            return getresponse()
        response.getresponse=cold
        sources=ConnectedSources(https_factory=lambda *a,**k:response,clock=lambda:now[0])
        result=sources.context(source_config(),self.request('Nahuel'),Event())[0].content
        self.assertIn('"status":"ok"',result)
        self.assertIn('Nahuel',result)

    def test_unavailable_portfolio_is_reported_as_a_source_failure_without_calling_groq(self):
        response=SourceConnection({},503)
        sources=ConnectedSources(https_factory=lambda *a,**k:response)
        remote=Mock()
        reply=GroqClient(remote,sources=sources).complete(source_config(),self.request('portfolio de Nahuel'))
        self.assertIn('No pude consultar la API',reply.text)
        remote.assert_not_called()
        self.assertIn('No se pudo consultar',sources.status())


if __name__=='__main__':
    unittest.main()
