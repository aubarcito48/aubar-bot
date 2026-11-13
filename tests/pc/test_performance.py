import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import numpy as np

from pc.aubar_control.ai_avatar import parse_avatar_reply
from pc.aubar_control import kokoro_speech
from pc.aubar_control.speech import KokoroBackend
import test_ai_avatar as avatar_tests


def plan():
    return {'text':'Nahuel, vas a lograrlo.', 'segments':[{
        'text':'Nahuel, vas a lograrlo.','gesture':'animation:angry',
        'delivery':'Enojado y firme','speed':1.07,'energy':1.15,'pause_ms':200}]}


class PerformanceTests(unittest.TestCase):
    def test_plan_keeps_literal_text_and_model_choices(self):
        reply=parse_avatar_reply(json.dumps(plan()))
        self.assertEqual(reply.action.argument,'angry')
        self.assertEqual(reply.text,'Nahuel, vas a lograrlo.')
        self.assertEqual(reply.segments[0].speed,1.07)
        self.assertEqual(reply.segments[0].delivery,'Enojado y firme')

    def test_invalid_plan_cannot_inject_usb_or_change_spoken_text(self):
        for key,value in [('gesture','animation:angry\nMODE auto'),('speed',5),
                          ('energy',float('nan')),('pause_ms',-1),('text','Otra frase.'),
                          ('delivery','x'*161)]:
            data=plan();data['segments'][0][key]=value
            with self.assertRaises(ValueError):
                parse_avatar_reply(json.dumps(data))

    def test_worker_controls_audio_and_announces_real_segment_timing(self):
        data=plan()
        data['text']+=' Respirá.'
        data['segments'].append({'text':'Respirá.','gesture':'animation:happy',
            'delivery':'Más tranquilo','speed':.9,'energy':.7,'pause_ms':0})
        reply=parse_avatar_reply(json.dumps(data))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'model').write_bytes(b'm');(root/'voices').write_bytes(b'v')
            marker=root/'playback.json'
            engine=Mock();engine.create.return_value=(np.ones(1000,dtype=np.float32)*.5,1000)
            audio=Mock();seen=[]
            audio.wait.side_effect=lambda:seen.append(json.loads(marker.read_text()))
            with patch.object(kokoro_speech,'MODEL_DIR',root),patch.object(kokoro_speech,'ASSETS',(('model',1,''),('voices',1,''))),patch.dict(sys.modules,{'kokoro_onnx':SimpleNamespace(Kokoro=Mock(return_value=engine)),'sounddevice':audio}):
                response=kokoro_speech.execute({'action':'speak','text':reply.text,'volume':50,'rate':0,
                    'segments':[s.payload() for s in reply.segments],'playback_state':str(marker)})
            self.assertTrue(response['ok'])
            self.assertEqual(engine.create.call_count,2)
            self.assertAlmostEqual(engine.create.call_args_list[0].kwargs['speed'],1.08*1.07)
            self.assertAlmostEqual(engine.create.call_args_list[1].kwargs['speed'],1.08*.9)
            samples=audio.play.call_args.args[0]
            self.assertEqual(len(samples),2200)
            self.assertAlmostEqual(float(samples[0]),.5*1.15*.5,places=6)
            self.assertTrue(np.all(samples[1000:1200]==0))
            self.assertAlmostEqual(float(samples[-1]),.5*.7*.5,places=6)
            self.assertEqual(seen[0]['timeline'][0]['avatar_id'],'angry')
            self.assertEqual(seen[0]['timeline'][0]['speech_end'],1)
            self.assertEqual(seen[0]['timeline'][0]['until'],1.2)
            self.assertEqual(seen[0]['timeline'][1]['from'],1.2)
            self.assertEqual(seen[0]['timeline'][1]['avatar_id'],'happy')
            self.assertEqual(json.loads(marker.read_text()),{})

    def test_timeline_holds_emotion_but_closes_mouth_during_directed_pause(self):
        with tempfile.TemporaryDirectory() as directory:
            backend=KokoroBackend();backend._playback_state=Path(directory)/'state.json'
            backend._playback_state.write_text(json.dumps({'start':10,'end':13,'timeline':[
                {'from':0,'speech_end':1,'until':1.3,'avatar_type':'animation','avatar_id':'angry','delivery':'Firme'},
                {'from':1.3,'speech_end':3,'until':3,'avatar_type':'animation','avatar_id':'happy','delivery':'Cálido'}]}))
            with patch('pc.aubar_control.speech.time.monotonic',return_value=11.1):
                self.assertTrue(backend.playing)
                self.assertFalse(backend.articulating)
                self.assertEqual(backend.performance['avatar_id'],'angry')
            with patch('pc.aubar_control.speech.time.monotonic',return_value=11.5):
                self.assertTrue(backend.articulating)
                self.assertEqual(backend.performance['avatar_id'],'happy')


class PerformancePanelTests(unittest.TestCase):
    setUp=avatar_tests.AIAvatarPanelTests.setUp
    tearDown=avatar_tests.AIAvatarPanelTests.tearDown
    pump=avatar_tests.AIAvatarPanelTests.pump
    text_question=avatar_tests.AIAvatarPanelTests.text_question
    def test_replay_preserves_plan_and_mid_audio_gestures_follow_timeline(self):
        self.client.answer=parse_avatar_reply(json.dumps(plan()))
        settings=[]
        original=self.voice.speak
        def speak(text,**options):
            settings.append(options)
            return original(text,**options)
        self.voice.speak=speak
        self.app.chat_voice_enabled.set(True)
        self.text_question();self.client.release.set()
        self.pump(lambda:bool(self.voice.calls))
        self.assertEqual(settings[0]['performance'][0].action.argument,'angry')
        self.voice.performance={'index':1,'avatar_type':'animation','avatar_id':'sad','delivery':'Más tranquilo'}
        self.pump(lambda:self.session.actions[-1].argument=='sad' and not self.app.busy)
        self.voice.performance=None
        self.voice.finish();self.pump(lambda:self.app._speech_future is None)
        self.app.read_ai_response()
        self.assertEqual(settings[-1]['performance'],settings[0]['performance'])
        self.app.new_conversation()
        self.assertIsNone(self.app._last_ai_performance)
