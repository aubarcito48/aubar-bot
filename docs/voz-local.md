# Voz local de Aubar

El motor de texto a voz recibe texto independiente de las expresiones y
animaciones. Puede leer una frase de prueba, una respuesta predefinida o,
en una integración futura, texto generado por una IA.

## Requisitos y funcionamiento

- Windows con PowerShell integrado y una voz **SAPI en español** instalada.
- Parlantes o auriculares seleccionados como salida predeterminada de Windows.
- Python 3.11 o superior, usando el entorno del proyecto.

No requiere conexión a internet, claves de API, modelos de voz descargados por
el proyecto ni nuevas dependencias de Python. Selecciona la primera voz SAPI
en español disponible; no cambia a una voz inglesa si falta una española.
En la PC de validación se utilizó **Microsoft Sabina Desktop, es-MX**.

El ayudante de PowerShell se ejecuta sin abrir otra ventana y recibe el texto
mediante JSON por entrada estándar. El texto no se inserta en instrucciones de
PowerShell ni se interpreta como XML. La reproducción sale por el dispositivo
predeterminado del sistema, sin crear un archivo de audio.

## Probar desde la terminal

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe tools/test_speech.py --list-voices
.\.venv\Scripts\python.exe tools/test_speech.py
.\.venv\Scripts\python.exe tools/test_speech.py --text "Hola, esta es una respuesta de prueba."
```

La prueba predeterminada dice: **«Hola, soy Aubar. Esta es mi voz en español»**.
No abre el micrófono ni necesita el ESP32. Apagar la escucha automática del
panel durante estas pruebas: su coordinación con la reproducción se implementará
en la tarea correspondiente del sprint.

Si no hay una voz española compatible con SAPI, la herramienta lo informa.
Las voces disponibles para otros servicios de Windows pueden no estar expuestas
a SAPI. Después de instalar una compatible, repetir la consulta de voces.

## Controles en el panel

Abrir la pestaña **Voz**. Esta prueba funciona sin conectar el ESP32.

1. Mantener **Activar voz** marcado.
2. Ajustar **Volumen** de 0 a 100; el valor inicial es 80.
3. Usar el texto predeterminado o escribir otro en **Texto para probar**.
4. Pulsar **Probar voz**. El estado muestra **Hablando…** y al terminar informa
   la voz utilizada.
5. Pulsar **Detener** para cortar la reproducción actual. Se puede iniciar
   otra prueba sin reiniciar el panel.

Desmarcar **Activar voz** detiene el audio en curso y bloquea nuevos pedidos
desde el panel. Al volver a marcarlo no se repite la frase anterior.
El volumen se aplica a la próxima reproducción y no modifica el volumen
global de Windows. El texto y el volumen se editan cuando no hay audio activo.

Para esta prueba debe estar apagada la escucha automática y terminada cualquier
captura manual. Mientras suena la voz no se puede iniciar una captura.
La pausa y reanudación automática del micrófono se integran en la tarea de
coordinación. El panel y las consultas USB siguen funcionando durante el audio.

Si la voz falla o falta una voz española, el estado muestra el error y permite
reintentar; la conexión con el ESP32 se mantiene. Los ajustes de esta pestaña
se conservan durante la sesión del panel.

## API para el panel y la futura IA

`SpeechEngine.speak(text)` devuelve un `Future` inmediatamente. La conversión y
reproducción ocurren en un trabajador separado del hilo de Tk y del trabajador
USB. El panel posee el motor como `app.speech` y lo cierra al salir.

```python
from pc.aubar_control.speech import SpeechEngine, SpeechError

engine = SpeechEngine()
future = engine.speak("Este texto puede venir de cualquier fuente.")
# El panel continúa atendiendo eventos y consultando el ESP32.
# Consultar future.done() desde root.after; solo entonces leer future.result().
# Future.result() sin comprobar done() bloquearía el hilo de la interfaz.
```

- `voices()` devuelve un futuro con las voces españolas disponibles.
- `speak(text, volume=100, rate=0)` admite volumen de 0 a 100 y velocidad
  SAPI de -10 a 10.
- El texto debe ser no vacío, de hasta 2000 caracteres y no contener NUL.
- Se admite una operación a la vez. Un segundo pedido mientras está ocupado
  devuelve `SpeechError`, sin acumular reproducciones.
- El futuro termina cuando finaliza el audio o devuelve un error. No confundir
  la aceptación del pedido con el final de la reproducción.
- `stop()` cancela la reproducción actual y permite volver a hablar usando
  el mismo motor. El futuro de esa reproducción termina con `SpeechCancelled`
  o queda cancelado si todavía no había comenzado.
- `close()` detiene el ayudante activo y libera el trabajador; no vuelve a
  reproducir pedidos antiguos.

El panel usa `app.speak_text(text)` para respetar la activación de voz, el
volumen y los estados de reproducción. Las respuestas tras confirmar comandos
y la coordinación automática con el micrófono se conectan en las siguientes tareas.

## Validación

Las pruebas de `tests/pc/test_speech.py` cubren ejecución asíncrona, continuidad
del panel y USB, texto literal, ausencia de voz española, errores del ayudante,
tiempo de espera y cierre de la aplicación. No reproducen audio real ni abren
el micrófono. La comprobación audible se hace por separado con el script anterior.

Referencia del tratamiento de texto:
[SpeechVoiceSpeakFlags de Microsoft SAPI](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee125223(v=vs.85)).
