import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from test_speech import FakeProcess
from pc.aubar_control import kokoro_speech
from pc.aubar_control.speech import KokoroBackend, SpeechEngine, SpeechError
from pc.aubar_control.tts_assets import VOICE
from tools.install_tts_model import install, verified


class KokoroAdapterTests(unittest.TestCase):
    def test_default_engine_uses_dora_and_hidden_python_with_literal_json(self):
        process=FakeProcess({'ok':True,'voice':VOICE})
        calls=[]
        def factory(command,**options):
            calls.append((command,options));return process
        with patch.object(sys,'executable',r'C:\venv\Scripts\pythonw.exe'):
            engine=SpeechEngine(KokoroBackend(factory))
            try:
                text='Hola, <voice>texto</voice>; $(Get-Date).'
                self.assertEqual(engine.speak(text,volume=25).result(1).id,'ef_dora')
                command,options=calls[0]
                self.assertEqual(Path(command[0]).name,'python.exe')
                self.assertEqual(Path(command[-1]).name,'kokoro_speech.py')
                self.assertEqual(json.loads(process.input)['text'],text)
                self.assertEqual(json.loads(process.input)['volume'],25)
                self.assertNotIn(text,' '.join(command))
                self.assertNotIn('shell',options)
            finally:
                engine.close()
        default=SpeechEngine()
        self.assertIsInstance(default.backend,KokoroBackend)
        default.close()

    def test_missing_model_and_dependencies_are_actionable_without_sapi_fallback(self):
        for code,word in [('MODEL_MISSING','modelo'),('DEPENDENCY_MISSING','dependencias')]:
            engine=SpeechEngine(KokoroBackend(lambda *a,**k:FakeProcess({'ok':False,'code':code},returncode=1)))
            try:
                with self.assertRaisesRegex(SpeechError,word):
                    engine.speak('Hola.').result(1)
            finally:
                engine.close()


class KokoroWorkerTests(unittest.TestCase):
    def test_local_synthesis_selects_spanish_dora_applies_volume_and_closes_output(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            (directory/'model').write_bytes(b'm')
            (directory/'voices').write_bytes(b'v')
            samples=Mock()
            model=Mock()
            model.create.return_value=(samples,24000)
            loader=Mock(return_value=model)
            audio=Mock()
            modules={'kokoro_onnx':SimpleNamespace(Kokoro=loader),'sounddevice':audio}
            with patch.object(kokoro_speech,'MODEL_DIR',directory), \
                 patch.object(kokoro_speech,'ASSETS',[('model',1,''),('voices',1,'')]), \
                 patch.dict(sys.modules,modules):
                # Mock arithmetic explicitly to check requested amplitude, not just settings.
                samples.__mul__=Mock(return_value='scaled samples')
                request=dict(action='speak',text='Estoy contento.',volume=30,rate=0)
                self.assertEqual(kokoro_speech.execute(request),{'ok':True,'voice':VOICE})
                model.create.assert_called_once_with('Estoy contento.',voice='ef_dora',speed=.95,lang='es')
                samples.__mul__.assert_called_once_with(.3)
                audio.play.assert_called_once_with('scaled samples',24000)
                audio.wait.assert_called_once()
                audio.stop.assert_called_once()
                # Failure during playback still closes the audio device.
                audio.wait.side_effect=OSError('Output unavailable')
                with self.assertRaises(OSError):
                    kokoro_speech.execute(request)
                self.assertEqual(audio.stop.call_count,2)

    def test_missing_assets_prevent_synthesis(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(kokoro_speech,'MODEL_DIR',Path(temp)):
            self.assertEqual(kokoro_speech.execute({'action':'speak'}),{'ok':False,'code':'MODEL_MISSING'})


class TtsInstallTests(unittest.TestCase):
    def test_verified_assets_work_offline_and_corrupted_files_are_repaired_atomically(self):
        data=b'model bytes'
        digest=hashlib.sha256(data).hexdigest()
        assets=[('test.onnx',len(data),digest)]
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp);path=target/'test.onnx'
            path.write_bytes(b'wrong bytes')
            download=Mock(return_value=io.BytesIO(data))
            install(target,download,assets)
            self.assertTrue(verified(path,len(data),digest))
            download.assert_called_once()
            offline=Mock(side_effect=AssertionError('Network should not be used'))
            install(target,offline,assets)
            offline.assert_not_called()

    def test_failed_download_preserves_existing_file_and_removes_partial(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp);path=target/'test.onnx'
            path.write_bytes(b'old')
            assets=[('test.onnx',4,hashlib.sha256(b'good').hexdigest())]
            with self.assertRaises(RuntimeError):
                install(target,lambda *a,**k:io.BytesIO(b'bad!'),assets)
            self.assertEqual(path.read_bytes(),b'old')
            self.assertFalse(path.with_suffix('.onnx.partial').exists())
