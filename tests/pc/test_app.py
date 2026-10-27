import threading
import time
import tkinter as tk
import unittest

from pc.aubar_control.app import AubarApp
from pc.aubar_control.protocol import DeviceError, DeviceStatus
from pc.aubar_control.session import DevicePort


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
        self.app = AubarApp(self.root, self.session, lambda: self.ports)
        self.pump(lambda: not self.app.busy)

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


if __name__ == "__main__":
    unittest.main()
