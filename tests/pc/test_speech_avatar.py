import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pc.aubar_control.app import AubarApp
from pc.aubar_control.session import DeviceSession
from pc.aubar_control.speech import KokoroBackend, ProcessSpeechBackend
from test_session import FakeSerial


class SpeechAvatarTests(unittest.TestCase):
    def test_supported_firmware_acknowledges_without_touching_pose(self):
        class SpeechSerial(FakeSerial):
            def write(self, data):
                if data.startswith(b'SPEECH '):
                    self.requests.append(data)
                    self.response.extend(b'OK APPLIED '+data)
                    return len(data)
                return super().write(data)
        session = DeviceSession(SpeechSerial, timeout=.02)
        original = session.connect('COM3')
        self.assertTrue(session.set_speaking(True))
        self.assertTrue(session.set_speaking(False))
        self.assertEqual(session.status(), original)
        session.close()

    def test_generation_is_not_playback_and_marker_cleans_up(self):
        backend = KokoroBackend()
        marker = None
        def request(_self, payload, *args, **kwargs):
            nonlocal marker
            marker = Path(payload['playback_state'])
            self.assertFalse(backend.playing)
            marker.write_text(json.dumps({'start': 99, 'end': 102}))
            with patch('pc.aubar_control.speech.time.monotonic', return_value=100):
                self.assertTrue(backend.playing)
            with patch('pc.aubar_control.speech.time.monotonic', return_value=103):
                self.assertFalse(backend.playing)
            marker.write_text('{}')
            self.assertFalse(backend.playing)
            return {'ok': True}
        with patch.object(ProcessSpeechBackend, '_request', request):
            backend._request({'action': 'speak'})
        self.assertFalse(marker.exists())
        self.assertFalse(backend.playing)

    def test_dispatch_starts_only_with_audio_refreshes_lease_and_stops(self):
        app = AubarApp.__new__(AubarApp)
        calls = []
        app.connected = True
        app.busy = False
        app._speech_avatar_sent = False
        app._speech_avatar_at = 0
        app.session = SimpleNamespace(speech_supported=None, set_speaking=lambda state: calls.append(state))
        app.speech = SimpleNamespace(playing=False, busy=True)
        app._submit = lambda name, action: action()
        with patch('pc.aubar_control.app.time.monotonic', return_value=10):
            app._dispatch_speech_avatar()
            self.assertEqual(calls, [])
            app.speech.playing = True
            app._dispatch_speech_avatar()
            app._dispatch_speech_avatar()
            self.assertEqual(calls, [True])
        with patch('pc.aubar_control.app.time.monotonic', return_value=11):
            app._dispatch_speech_avatar()
        app.speech.playing = False
        app._dispatch_speech_avatar()
        self.assertEqual(calls, [True, True, False])

    def test_old_firmware_declines_once_without_disconnect(self):
        class OldSerial(FakeSerial):
            def write(self, data):
                if data.startswith(b'SPEECH '):
                    self.requests.append(data)
                    self.response.extend(b'ERR UNKNOWN_COMMAND\n')
                    return len(data)
                return super().write(data)
        session = DeviceSession(OldSerial, timeout=.02)
        session.connect('COM3')
        self.assertFalse(session.set_speaking(True))
        self.assertFalse(session.set_speaking(False))
        self.assertTrue(session.connected)
        self.assertEqual(session._serial.requests.count(b'SPEECH on\n'), 1)
        self.assertNotIn(b'SPEECH off\n', session._serial.requests)
        session.close()
