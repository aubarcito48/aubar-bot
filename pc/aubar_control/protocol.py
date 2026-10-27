from dataclasses import dataclass


class DeviceError(Exception):
    """Actionable device/connection error shown by the desktop tool."""


@dataclass(frozen=True)
class DeviceStatus:
    mode: str
    expression: str
    look: str


def parse_status(line: str) -> DeviceStatus:
    prefix = "OK STATUS "
    if not line.startswith(prefix):
        raise DeviceError("El dispositivo no devolvió un estado válido.")
    fields = line[len(prefix):].split()
    pairs = [field.split("=", 1) for field in fields]
    if any(len(pair) != 2 for pair in pairs):
        raise DeviceError("La respuesta de estado está incompleta.")
    values = dict(pairs)
    allowed = {
        "mode": {"auto", "manual"},
        "expression": {"neutral", "contento", "sorprendido", "dormido", "enojado"},
        "look": {"izquierda", "centro", "derecha"},
    }
    if len(pairs) != 3 or set(values) != set(allowed) or any(
        values[key] not in choices for key, choices in allowed.items()
    ):
        raise DeviceError("El estado recibido no corresponde a esta versión de Aubar Bot.")
    return DeviceStatus(**values)
