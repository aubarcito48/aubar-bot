"""Serial operations. Call from a worker, not the Tk event loop."""
from dataclasses import dataclass
import time

import serial
from serial.tools import list_ports

from .protocol import DeviceError, DeviceStatus, parse_status


@dataclass(frozen=True)
class DevicePort:
    device: str
    description: str
    is_esp32: bool = False

    @property
    def label(self) -> str:
        return f"{self.device} — {self.description}"


def available_ports() -> list[DevicePort]:
    return [DevicePort(p.device, p.description or "Puerto serie", p.vid == 0x303A)
            for p in sorted(list_ports.comports())]


class DeviceSession:
    def __init__(self, serial_factory=serial.Serial, timeout: float = 2.5):
        self._factory = serial_factory
        self._timeout = timeout
        self._serial = None
        self.port: str | None = None

    @property
    def connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def close(self) -> None:
        connection, self._serial = self._serial, None
        self.port = None
        if connection is not None:
            try:
                connection.close()
            except (serial.SerialException, OSError):
                pass

    def _readline(self, deadline: float) -> str:
        data = bytearray()
        while time.monotonic() < deadline:
            byte = self._serial.read(1)
            if not byte:
                continue
            if byte == b"\n":
                try:
                    return data.decode("ascii").rstrip("\r")
                except UnicodeDecodeError as exc:
                    raise DeviceError("La respuesta USB no pertenece al protocolo de Aubar Bot.") from exc
            data.extend(byte)
            if len(data) > 128:
                raise DeviceError("El dispositivo envió una respuesta demasiado larga.")
        raise DeviceError("El dispositivo no responde. Revisá el cable y volvé a conectar.")

    def connect(self, port: str) -> DeviceStatus:
        self.close()
        try:
            # Configure lines before opening to avoid an RTS/DTR reset pulse.
            self._serial = self._factory(port=None, baudrate=115200, timeout=0.1, write_timeout=1)
            self._serial.dtr = True
            self._serial.rts = False
            self._serial.port = port
            self._serial.open()
            self._serial.reset_input_buffer()
            self._serial.write(b"\nPING\n")
            deadline = time.monotonic() + self._timeout
            while True:
                reply = self._readline(deadline)
                if reply == "OK PONG 2":
                    break
                if reply.startswith("OK PONG "):
                    raise DeviceError("El firmware usa otra versión del protocolo; se necesita la versión 2.")
            self.port = port
            return self.status()
        except DeviceError:
            self.close()
            raise
        except (serial.SerialException, OSError, ValueError) as exc:
            self.close()
            raise DeviceError(f"No se pudo abrir {port}. Revisá el cable y cerrá otros monitores serie.") from exc

    def status(self) -> DeviceStatus:
        if not self.connected:
            raise DeviceError("Primero conectá el dispositivo.")
        try:
            self._serial.write(b"STATUS\n")
            reply = self._readline(time.monotonic() + self._timeout)
            return parse_status(reply)
        except DeviceError:
            self.close()
            raise
        except (serial.SerialException, OSError) as exc:
            self.close()
            raise DeviceError("Se perdió la conexión USB. Revisá el cable y volvé a conectar.") from exc
