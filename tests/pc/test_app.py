import threading
import time
import tkinter as tk
import unittest
from array import array
from dataclasses import replace
from audio_fakes import FakeAudio, FakeRecognizer, FakeSpeechEngine

from pc.aubar_control.app import AubarApp
from pc.aubar_control.protocol import DeviceError, DeviceStatus
from pc.aubar_control.session import DevicePort
from pc.aubar_control.audio import InputDevice, MicrophoneCapture
from pc.aubar_control.recognition import RecognitionResult


class FakeSession:
    def __init__(self):
        self.fail = False
        self.port = None
        self.gate = None
        self.actions = []
        self.state = DeviceStatus('manual', 'enojado', 'izquierda')

    def connect(self, port):
        if self.gate:
            self.gate.wait(2)
        self.port = port
        return self.status()

    def status(self):
        if self.fail:
            raise DeviceError("Se perdió la conexión USB. Revisá el cable y volvé a conectar.")
        return self.state

    def apply_action(self, action):
        if self.fail:
            raise DeviceError('No se pudo confirmar la orden. No se reenviará.')
        self.actions.append(action)
        if action.command == 'EXPRESSION':
            self.state = replace(self.state, mode='manual', expression=action.argument)
        elif action.command == 'LOOK':
            self.state = replace(self.state, mode='manual', look=action.argument)
        elif action.command == 'ANIMATION':
            self.state = replace(self.state, mode='manual', animation=action.argument)
        else:
            self.state = DeviceStatus('auto', 'neutral', 'centro') if action.argument == 'auto' else replace(self.state, mode='manual')
        if action.look is not None:
            self.state = replace(self.state, look=action.look)
        return self.state

    def close(self):
        self.port = None


class AppTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.session = FakeSession()
        self.ports = [DevicePort("COM1", "Serie"), DevicePort("COM3", "ESP32", True)]
        self.audio = FakeAudio()
        self.recognizer = FakeRecognizer()
        self.app = AubarApp(self.root, self.session, lambda: self.ports,
                           MicrophoneCapture(self.audio), lambda: [InputDevice(1, 'Microfono', 'Prueba', True)],
                           self.recognizer,speech=FakeSpeechEngine())
        self.pump(lambda: not self.app.busy and not self.app.audio_scan_busy)

    def tearDown(self):
        if self.session.gate:
            self.session.gate.set()
        if self.recognizer.gate:
            self.recognizer.gate.set()
        self.app.close()

    def pump(self, condition, timeout=2):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.005)
        self.assertTrue(condition(), "UI operation did not finish")

    def start_microphone(self):
        self.app.start_recording()
        self.pump(lambda: self.app.audio_phase == 'warming')
        self.assertIn('Preparando', self.app.audio_message.get())
        self.app.capture.ready.set()
        self.pump(lambda: self.app.audio_phase == 'recording')

    def speak(self):
        self.start_microphone()
        self.audio.streams[-1].emit(array('h', [4000]*4000).tobytes())
        self.app.stop_recording()

    def test_connect_status_disconnect_and_reconnect_to_new_port(self):
        self.assertTrue(self.app.port_value.get().startswith("COM3"))
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.assertTrue(self.app.connected)
        self.assertEqual(self.app.values["expression"].get(), "Enojado")
        self.assertEqual(str(self.app.port_combo.cget("state")), "disabled")
        self.app.disconnect()
        self.pump(lambda: not self.app.busy)
        self.assertFalse(self.app.connected)
        self.assertEqual(self.app.values["expression"].get(), "—")
        self.ports[:] = [DevicePort("COM8", "ESP32", True)]
        self.app.refresh_ports()
        self.pump(lambda: not self.app.busy)
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.assertEqual(self.app.active_port, "COM8")

    def test_loss_clears_old_values_and_allows_reconnect(self):
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.session.fail = True
        self.app.refresh_status()
        self.pump(lambda: not self.app.busy)
        self.assertFalse(self.app.connected)
        self.assertIn("perdió", self.app.banner_value.get())
        self.assertEqual(self.app.values["look"].get(), "—")
        self.session.fail = False
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.assertTrue(self.app.connected)

    def test_window_remains_responsive_during_connection(self):
        self.session.gate = threading.Event()
        heartbeat = []
        self.app.connect()
        self.root.after(10, lambda: heartbeat.append(True))
        self.pump(lambda: bool(heartbeat))
        self.assertTrue(self.app.busy)
        self.assertFalse(self.app.connected)
        self.session.gate.set()
        self.pump(lambda: not self.app.busy)
        self.assertTrue(self.app.connected)

    def test_push_to_talk_records_only_while_held(self):
        self.start_microphone()
        pcm = array('h', [4000]*4000).tobytes()
        self.audio.streams[-1].emit(pcm)
        self.app.stop_recording()
        self.audio.streams[-1].emit(pcm)
        self.pump(lambda: self.app.audio_phase == 'idle')
        self.assertEqual(self.app.last_recording.pcm, pcm)
        self.assertIn('apagado', self.app.audio_message.get())
        self.assertTrue(self.audio.streams[-1].closed)
        self.assertEqual(self.app.recognized_action.argument, 'contento')

    def test_unknown_phrase_clears_previous_action(self):
        for text, action in [('contento', self.recognizer.result.action), ('hoy hace frio', None)]:
            self.recognizer.result = RecognitionResult(text, action, 'Resultado de prueba')
            self.start_microphone()
            self.audio.streams[-1].emit(array('h', [4000]*4000).tobytes())
            self.app.stop_recording()
            self.pump(lambda: self.app.audio_phase == 'idle')
            self.assertEqual(self.app.recognition_text.get(), text)
            self.assertEqual(self.app.recognized_action, action)
        self.assertIsNone(self.session.port)  # Recognition alone does not open USB.

    def test_audio_errors_do_not_disconnect_usb(self):
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.audio.reject_open = True
        self.app.start_recording()
        self.pump(lambda: self.app.audio_phase == 'idle')
        self.assertTrue(self.app.connected)
        self.assertIsNone(self.app.last_recording)
        self.assertIn('No se pudo abrir', self.app.audio_message.get())

    def test_focus_loss_stops_capture(self):
        self.start_microphone()
        self.audio.streams[-1].emit(array('h', [4000]*4000).tobytes())
        self.app._focus_out(None)  # Withdrawn test window has no application focus.
        self.pump(lambda: self.app.audio_phase == 'idle')
        self.assertFalse(self.app.capture.requested.is_set())
        self.assertTrue(self.audio.streams[-1].closed)

    def test_limit_stops_capture_without_release(self):
        self.start_microphone()
        self.audio.streams[-1].emit(array('h', [4000]*161000).tobytes())
        self.pump(lambda: self.app.audio_phase == 'idle')
        self.assertEqual(self.app.last_recording.duration, 10)
        self.assertTrue(self.audio.streams[-1].closed)

    def test_voice_sends_once_and_updates_confirmed_state(self):
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.speak()
        self.pump(lambda: self.app.audio_phase == 'idle' and not self.app.busy)
        self.assertEqual(len(self.session.actions), 1)
        self.assertEqual(self.app.values['expression'].get(), 'Contento')
        self.assertIn('Confirmado por el ESP32', self.app.recognition_message.get())

    def test_unknown_phrase_never_sends(self):
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.recognizer.result = RecognitionResult('hoy hace frio', None, 'Frase no reconocida como comando.')
        self.speak()
        self.pump(lambda: self.app.audio_phase == 'idle')
        self.assertEqual(self.session.actions, [])

    def test_capture_from_previous_connection_is_not_replayed(self):
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.recognizer.gate = threading.Event()
        self.speak()
        self.pump(lambda: self.app.audio_phase == 'recognizing')
        self.app.disconnect()
        self.pump(lambda: not self.app.busy)
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.recognizer.gate.set()
        self.pump(lambda: self.app.audio_phase == 'idle')
        self.assertEqual(self.session.actions, [])
        self.assertIn('no enviada', self.app.recognition_message.get())

    def test_failed_send_is_not_replayed_after_reconnect(self):
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.session.fail = True
        self.speak()
        self.pump(lambda: self.app.audio_phase == 'idle' and not self.app.busy)
        self.assertFalse(self.app.connected)
        self.assertIsNone(self.app.pending_action)
        self.session.fail = False
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        self.assertEqual(self.session.actions, [])

    def test_voice_waits_for_busy_usb_without_being_lost(self):
        self.app.connect()
        self.pump(lambda: not self.app.busy)
        # Simulate an in-flight periodic query while recognition completes.
        self.app.busy = True
        self.speak()
        self.pump(lambda: self.app.pending_action is not None)
        self.assertEqual(self.session.actions, [])
        self.app.busy = False
        self.app._dispatch_voice()
        self.pump(lambda: self.app.audio_phase == 'idle' and not self.app.busy)
        self.assertEqual(len(self.session.actions), 1)


if __name__ == "__main__":
    unittest.main()
