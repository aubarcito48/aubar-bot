import unittest
import serial

from pc.aubar_control.protocol import DeviceError, DeviceStatus, parse_status
from pc.aubar_control.session import DeviceSession


class FakeSerial:
    def __init__(self, *, version=2, bad_status=False, unplug=False, **kwargs):
        self.is_open = False
        self.version, self.bad_status, self.unplug = version, bad_status, unplug
        self.response = bytearray()
        self.requests = []

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def reset_input_buffer(self):
        self.response.clear()

    def write(self, data):
        self.requests.append(data)
        if data == b"\nPING\n":
            self.response.extend(f"ERR EMPTY\nOK PONG {self.version}\n".encode())
        elif data == b"STATUS\n":
            if self.unplug:
                raise serial.SerialException("cable disconnected")
            self.response.extend(b"OK STATUS mode=manual expression=enojado look=izquierda\n"
                                 if not self.bad_status else b"OK STATUS mode=unknown\n")
        return len(data)

    def read(self, size):
        if not self.response:
            return b""
        byte = bytes(self.response[:size])
        del self.response[:size]
        return byte


class SessionTests(unittest.TestCase):
    def test_connect_query_close_and_reconnect(self):
        ports = []
        def factory(**kwargs):
            ports.append(FakeSerial(**kwargs))
            return ports[-1]
        session = DeviceSession(factory, timeout=0.02)
        self.assertEqual(session.connect("COM3"), DeviceStatus("manual", "enojado", "izquierda"))
        self.assertTrue(session.connected)
        self.assertEqual(session.port, "COM3")
        self.assertEqual(session.status().expression, "enojado")
        session.close()
        self.assertFalse(ports[0].is_open)
        session.connect("COM8")
        self.assertEqual(session.port, "COM8")
        self.assertEqual(ports[1].requests, [b"\nPING\n", b"STATUS\n"])
        session.close()

    def test_incompatible_firmware_releases_port(self):
        port = FakeSerial(version=1)
        session = DeviceSession(lambda **_: port, timeout=0.02)
        with self.assertRaisesRegex(DeviceError, "versión 2"):
            session.connect("COM3")
        self.assertFalse(port.is_open)
        self.assertIsNone(session.port)

    def test_unplug_closes_and_clears_connection(self):
        port = FakeSerial()
        session = DeviceSession(lambda **_: port, timeout=0.02)
        session.connect("COM3")
        port.unplug = True
        with self.assertRaisesRegex(DeviceError, "perdió"):
            session.status()
        self.assertFalse(session.connected)
        self.assertIsNone(session.port)

    def test_bad_status_is_not_shown_as_connected(self):
        port = FakeSerial(bad_status=True)
        session = DeviceSession(lambda **_: port, timeout=0.02)
        with self.assertRaises(DeviceError):
            session.connect("COM3")
        self.assertFalse(port.is_open)

    def test_silent_device_has_bounded_timeout(self):
        port = FakeSerial()
        port.write = lambda _: None
        session = DeviceSession(lambda **_: port, timeout=0.01)
        with self.assertRaisesRegex(DeviceError, "no responde"):
            session.connect("COM3")
        self.assertFalse(port.is_open)

    def test_strict_status_fields(self):
        bad = ["ERR UNKNOWN_COMMAND", "OK STATUS mode=auto", "OK STATUS mode=auto mode=manual look=centro",
               "OK STATUS mode=auto expression=neutral look=arriba", "OK STATUS malformed"]
        for response in bad:
            with self.subTest(response=response), self.assertRaises(DeviceError):
                parse_status(response)


if __name__ == "__main__":
    unittest.main()
