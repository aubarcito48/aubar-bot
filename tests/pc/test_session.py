import unittest
import serial

from pc.aubar_control.protocol import DeviceError, DeviceStatus, parse_status, encode_action
from pc.aubar_control.voice_commands import VoiceAction, match_command
from pc.aubar_control.session import DeviceSession


class FakeSerial:
    def __init__(self, *, version=2, bad_status=False, unplug=False, **kwargs):
        self.is_open = False
        self.version, self.bad_status, self.unplug = version, bad_status, unplug
        self.response = bytearray()
        self.requests = []
        self.ack = None
        self.drop_ack = False
        self.break_status = False

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
        elif data.startswith((b'EXPRESSION ', b'LOOK ', b'MODE ', b'ANIMATION ')):
            if self.unplug:
                raise serial.SerialException('unplugged')
            if not self.drop_ack:
                self.response.extend(self.ack if self.ack is not None else b'OK APPLIED '+data)
            if self.break_status:
                self.unplug = True
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

    def test_send_requires_exact_ack_and_does_not_retry(self):
        port = FakeSerial()
        session = DeviceSession(lambda **_: port, timeout=0.02)
        session.connect('COM3')
        session.apply_action(match_command('enojado'))
        self.assertEqual(port.requests.count(b'EXPRESSION enojado\n'), 1)
        port.ack = b'OK APPLIED EXPRESSION contento\n'
        with self.assertRaisesRegex(DeviceError, 'no se reenviará'):
            session.apply_action(match_command('enojado'))
        self.assertFalse(session.connected)
        self.assertEqual(port.requests.count(b'EXPRESSION enojado\n'), 2)

    def test_lost_ack_is_uncertain_not_resent(self):
        port = FakeSerial()
        session = DeviceSession(lambda **_: port, timeout=0.01)
        session.connect('COM3')
        port.drop_ack = True
        with self.assertRaisesRegex(DeviceError, 'Puede haberse aplicado'):
            session.apply_action(match_command('contento'))
        self.assertEqual(port.requests.count(b'EXPRESSION contento\n'), 1)
        self.assertFalse(session.connected)

    def test_acknowledged_action_with_lost_status_is_reported_honestly(self):
        port = FakeSerial()
        session = DeviceSession(lambda **_: port, timeout=0.02)
        session.connect('COM3')
        port.break_status = True
        with self.assertRaisesRegex(DeviceError, 'confirmó la orden'):
            session.apply_action(match_command('contento'))

    def test_invalid_action_cannot_inject_serial_messages(self):
        with self.assertRaises(DeviceError):
            encode_action(VoiceAction('EXPRESSION', 'contento\nMODE auto', 'invalid'))


if __name__ == "__main__":
    unittest.main()
