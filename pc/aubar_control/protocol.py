from dataclasses import dataclass
from .catalog import EXPRESSIONS, ANIMATIONS


class DeviceError(Exception):
    """Actionable device/connection error shown by the desktop tool."""


@dataclass(frozen=True)
class DeviceStatus:
    mode: str
    expression: str
    look: str
    animation: str = 'none'


def encode_action(action) -> bytes:
    allowed = {
        'EXPRESSION': set(EXPRESSIONS),
        'ANIMATION': set(ANIMATIONS),
        'LOOK': {'izquierda', 'centro', 'derecha'},
        'MODE': {'manual', 'auto'},
    }
    if action.command not in allowed or action.argument not in allowed[action.command]:
        raise DeviceError('La acción reconocida no es un comando válido.')
    return f'{action.command} {action.argument}\n'.encode('ascii')


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
        "expression": set(EXPRESSIONS),
        "look": {"izquierda", "centro", "derecha"},
        "animation": set(ANIMATIONS) | {'none'},
    }
    # Accept the old three-field status for existing v2 devices.
    if 'animation' not in values:
        values['animation'] = 'none'
    if len(pairs) not in (3, 4) or len(dict(pairs))!=len(pairs) or set(values) != set(allowed) or any(
        values[key] not in choices for key, choices in allowed.items()
    ):
        raise DeviceError("El estado recibido no corresponde a esta versión de Aubar Bot.")
    return DeviceStatus(**values)
