import threading
import time
import tkinter as tk
import unittest
from array import array
from audio_fakes import FakeAudio, FakeRecognizer

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

    def connect(self, port):
        if self.gate:
            self.gate.wait(2)
        self.port = port
        return self.status()

    def status(self):
        if self.fail:
            raise DeviceError("Se perdió la conexión USB. Revisá el cable y volvé a conectar.")
        return DeviceStatus("manual", "enojado", "izquierda")

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
                           self.recognizer)
        self.pump(lambda: not self.app.busy and not self.app.audio_scan_busy)

    def tearDown(self):
        if self.session.gate:
            self.session.gate.set()
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


if __name__ == "__main__":
    unittest.main()
