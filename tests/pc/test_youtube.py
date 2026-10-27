import unittest
from unittest.mock import Mock, ANY, patch
from urllib.parse import parse_qs, urlsplit

import test_app
import test_automatic
import test_queries
from pc.aubar_control.youtube import YouTubeAction, match_youtube_command, open_youtube, first_video
from pc.aubar_control.recognition import RecognitionResult


class YouTubeCommandTests(unittest.TestCase):
    def test_open_and_search_variants_preserve_search_contents(self):
        for phrase in ('abrí youtube', 'abre you tube', 'Aubar, abrir YouTube por favor'):
            self.assertEqual(match_youtube_command(phrase), YouTubeAction('open'))
        for phrase in ('buscá C++ y música en YouTube', 'busca en youtube C++ y música',
                       'Aubar buscame C++ y música en youtube por favor',
                       'búscame C++ y música en YouTube',
                       'podés buscar C++ y música en youtube',
                       'quiero que me busques C++ y música por youtube',
                       'me buscás C++ y música en youtube',
                       'por favor busca en youtube C++ y música'):
            self.assertEqual(match_youtube_command(phrase), YouTubeAction('search','C++ y música'))
        for phrase in ('no abras youtube','cómo abrir youtube','busca gatos','youtube',
                       'me gustaría saber cómo buscar en youtube','no pongas musica en youtube',
                       'como reproducir musica en youtube'):
            self.assertIsNone(match_youtube_command(phrase))

    def test_only_fixed_https_host_and_encoded_query_reach_browser(self):
        opener=Mock(return_value=True)
        query='música C++ & https://otro.test/?a=1#algo'
        message,spoken=open_youtube(YouTubeAction('search',query),opener)
        url=urlsplit(opener.call_args.args[0])
        self.assertEqual((url.scheme,url.netloc,url.path),('https','www.youtube.com','/results'))
        self.assertEqual(parse_qs(url.query),{'search_query':[query]})
        self.assertFalse(url.fragment)
        self.assertIsNotNone(spoken)
        opener.reset_mock()
        open_youtube(YouTubeAction('open'),opener)
        opener.assert_called_once_with('https://www.youtube.com/')

    def test_empty_oversized_invalid_or_failed_actions_never_announce_success(self):
        opener=Mock(return_value=True)
        for action in (YouTubeAction('search'),YouTubeAction('search','x'*501),
                       YouTubeAction('execute','anything'),YouTubeAction('open','bad')):
            self.assertIsNone(open_youtube(action,opener)[1])
        opener.assert_not_called()
        for fail in (False,OSError('internal failure')):
            opener=Mock(return_value=fail) if fail is False else Mock(side_effect=fail)
            message,spoken=open_youtube(YouTubeAction('open'),opener)
            self.assertIsNone(spoken)
            self.assertNotIn('internal failure',message)
            opener.assert_called_once()
        for phrase in ('busca en youtube','busca en youtube por favor'):
            self.assertEqual(match_youtube_command(phrase),YouTubeAction('search'))

    def test_play_variants_select_first_video_but_search_keeps_results(self):
        for phrase in ('poné música en youtube','pone música en youtube',
                       'poneme música por youtube','reproducí música en youtube',
                       'puedes reproducir música en youtube','pon en youtube música',
                       'quiero que me pongas música en youtube'):
            self.assertEqual(match_youtube_command(phrase),YouTubeAction('play','música'))
        resolver=Mock(return_value='abcdefghijk');opener=Mock(return_value=True)
        message,spoken=open_youtube(YouTubeAction('play','música'),opener,resolver=resolver)
        resolver.assert_called_once_with('música')
        url=urlsplit(opener.call_args.args[0])
        self.assertEqual((url.scheme,url.netloc,url.path),('https','www.youtube.com','/watch'))
        self.assertEqual(parse_qs(url.query),{'v':['abcdefghijk'],'autoplay':['1']})
        self.assertIn('primer video',spoken)
        resolver.reset_mock()
        open_youtube(YouTubeAction('search','música'),opener,resolver=resolver)
        resolver.assert_not_called()

    def test_compound_open_search_play_becomes_one_video_action(self):
        for phrase in (
            'abrí youtube y busca video de gato y reproducir',
            'abre youtube y busca video de gato y reproduce el primero',
            'abrí YouTube, buscá video de gato y reproducilo',
            'busca video de gato en youtube y reproduce el primer video',
            'busca en youtube video de gato y después reproducilo',
            'abrí youtube y poné video de gato',
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(match_youtube_command(phrase),YouTubeAction('play','video de gato'))
        self.assertEqual(match_youtube_command('abrí youtube y busca video de gato'),
                         YouTubeAction('search','video de gato'))
        opener=Mock(return_value=True);resolver=Mock(return_value='abcdefghijk')
        action=match_youtube_command('abrí youtube y busca video de gato y reproducir')
        open_youtube(action,opener,resolver=resolver)
        resolver.assert_called_once_with('video de gato')
        opener.assert_called_once_with('https://www.youtube.com/watch?v=abcdefghijk&autoplay=1')
        for phrase in ('no abras youtube y busca gato y reproducir',
                       'abre youtube y no busques gato y reproducir',
                       'busca gato y reproducilo'):
            self.assertIsNone(match_youtube_command(phrase))

    def test_play_errors_and_invalid_results_never_open_browser_or_announce_success(self):
        opener=Mock()
        for identifier in (None,'','https://otro.test/','bad\nidentifier'):
            message,spoken=open_youtube(YouTubeAction('play','música'),opener,
                                       resolver=Mock(return_value=identifier))
            self.assertIsNone(spoken)
        message,spoken=open_youtube(YouTubeAction('play','música'),opener,
                                   resolver=Mock(side_effect=OSError('private internal error')))
        self.assertIsNone(spoken);self.assertNotIn('private',message)
        opener.assert_not_called()
        resolver=Mock()
        open_youtube(YouTubeAction('play'),opener,resolver=resolver)
        resolver.assert_not_called()

    def test_cancel_during_lookup_prevents_late_video_open(self):
        from threading import Event
        cancel=Event();opener=Mock()
        def resolve(query):
            cancel.set();return 'abcdefghijk'
        message,spoken=open_youtube(YouTubeAction('play','música'),opener,
                                   resolver=resolve,cancel_event=cancel)
        self.assertIsNone(spoken);opener.assert_not_called()
        resolver=Mock()
        open_youtube(YouTubeAction('play','música'),opener,resolver=resolver,cancel_event=cancel)
        resolver.assert_not_called()

    def test_lookup_uses_flat_search_without_media_download_and_rejects_no_results(self):
        with patch('yt_dlp.YoutubeDL') as factory:
            client=factory.return_value.__enter__.return_value
            client.extract_info.return_value={'entries':[{'id':'abcdefghijk'}]}
            self.assertEqual(first_video('música'),'abcdefghijk')
            client.extract_info.assert_called_once_with('ytsearch1:música',download=False)
            self.assertTrue(factory.call_args.args[0]['extract_flat'])
            self.assertTrue(factory.call_args.args[0]['skip_download'])
            client.extract_info.return_value={'entries':[]}
            with self.assertRaises(ValueError):first_video('música')


class YouTubeRecognitionTests(unittest.TestCase):
    recognize=test_queries.QueryRecognitionTests.recognize

    def test_manual_and_automatic_route_to_browser_without_query_or_usb_action(self):
        for automatic in (False,True):
            prefix=''
            for command in ('abri youtube','busca musica relajante en youtube', 'busca en youtube',
                            'pone musica en youtube','reproduce en youtube videos de gatos'):
                recognized=self.recognize(prefix+command,automatic=automatic)
                self.assertIsNotNone(recognized.youtube)
                self.assertIsNone(recognized.action)
                self.assertIsNone(recognized.query)

    def test_screenshot_compound_phrase_routes_locally_in_both_capture_modes(self):
        phrase='abrí youtube y busca video de gato y reproducir'
        for automatic in (False,True):
            recognized=self.recognize(phrase,automatic=automatic)
            self.assertEqual(recognized.youtube,YouTubeAction('play','video de gato'))
            self.assertIsNone(recognized.query)
            self.assertIsNone(recognized.action)

    def test_automatic_direct_commands_keep_confidence_and_negation_checks(self):
        self.assertEqual(self.recognize('abri youtube').youtube,YouTubeAction('open'))
        self.assertIsNone(self.recognize('aubar abri youtube',.5).youtube)
        self.assertIsNone(self.recognize('aubar no abras youtube').youtube)


class YouTubePanelTests(unittest.TestCase):
    setUp=test_app.AppTests.setUp
    tearDown=test_app.AppTests.tearDown
    pump=test_app.AppTests.pump
    speak=test_app.AppTests.speak
    start_microphone=test_app.AppTests.start_microphone
    start_auto=test_automatic.AutomaticAppTests.start_auto
    speak_auto=test_automatic.AutomaticAppTests.speak_auto

    def browser_result(self,action):
        self.recognizer.result=RecognitionResult('abri youtube',None,'YouTube',youtube=action)

    def test_manual_without_usb_or_groq_opens_once_and_speaks_after_success(self):
        self.app.youtube_opener=Mock(return_value=('Solicitud enviada.','Abrí YouTube.'))
        self.app.ai_service.submit=Mock(side_effect=AssertionError('No Groq'))
        self.browser_result(YouTubeAction('open'));self.speak()
        self.pump(lambda:len(self.app.speech.calls)==1)
        self.app.youtube_opener.assert_called_once_with(YouTubeAction('open'),cancel_event=ANY)
        self.app.ai_service.submit.assert_not_called()
        self.assertEqual(self.session.actions,[])
        self.assertFalse(self.app.connected)
        self.assertEqual(self.app.recognition_message.get(),'Solicitud enviada.')

    def test_automatic_search_returns_to_listening_and_failure_preserves_usb(self):
        self.app.youtube_opener=Mock(return_value=('Solicitud enviada.','Búsqueda abierta.'))
        self.start_auto();self.browser_result(YouTubeAction('search','musica'))
        self.speak_auto();self.pump(lambda:len(self.app.speech.calls)==1)
        self.pump(lambda:self.app._speech_future is None and self.app.automatic_capture.listening.is_set())
        self.app.youtube_opener.return_value=('No se pudo abrir el navegador.',None)
        self.speak_auto();self.pump(lambda:self.app.youtube_opener.call_count==2)
        self.pump(lambda:not self.app._youtube_pending and self.app.automatic_capture.listening.is_set())
        self.assertTrue(self.app.connected)
        self.assertEqual(len(self.app.speech.calls),1)
        self.assertEqual(self.session.actions,[])
        self.assertIn('No se pudo',self.app.recognition_message.get())

    def test_reset_during_recognition_discards_browser_action(self):
        import threading
        self.app.youtube_opener=Mock()
        self.recognizer.gate=threading.Event()
        self.browser_result(YouTubeAction('open'));self.speak()
        self.pump(lambda:self.app.audio_phase=='recognizing')
        self.app.new_conversation();self.recognizer.gate.set()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.app.youtube_opener.assert_not_called()
