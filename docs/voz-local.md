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
panel durante estas pruebas de terminal: el script es independiente del panel
y no comparte su estado de micrófono. Las reproducciones iniciadas desde el
panel sí utilizan la coordinación automática descrita abajo.

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
5. Pulsar **Detener** para cortar la reproducción actual y descartar cualquier
   respuesta pendiente. Se puede iniciar otra prueba sin reiniciar el panel.

Desmarcar **Activar voz** detiene el audio en curso y bloquea nuevos pedidos
desde el panel. Al volver a marcarlo no se repite la frase anterior.
El volumen se aplica a la próxima reproducción y no modifica el volumen
global de Windows. El texto y el volumen se editan cuando no hay audio activo.

Se puede probar la voz con la escucha automática activada: el panel pausa el
micrófono antes de comenzar a reproducir. Hay que terminar cualquier captura
manual o reconocimiento en curso antes de iniciar una prueba.
Mientras suena la voz y durante la espera posterior no se puede iniciar una
captura manual. El panel y las consultas USB siguen funcionando durante el audio.

Si la voz falla o falta una voz española, el estado muestra el error y permite
reintentar; la conexión con el ESP32 se mantiene. Los ajustes de esta pestaña
se conservan durante la sesión del panel.

## Respuestas a acciones confirmadas

Con **Activar voz** marcado, el panel responde después de recibir la
confirmación del ESP32 y consultar su estado. Funciona con comandos de voz
manuales, escucha automática y selecciones desde **Catálogo**.

| Acción confirmada | Ejemplo de respuesta |
| --- | --- |
| Contento | «Estoy contento». |
| Enojado + derecha | «Estoy enojado mirando a la derecha». |
| Celebrar + izquierda | «Voy a celebrar mirando a la izquierda». |
| Mirada al centro | «Miro al centro». |
| Modo automático | «Activo el modo automático». |

Las 28 expresiones, las 23 animaciones y las 153 combinaciones tienen texto
de respuesta. Las expresiones menos habituales se anuncian por su nombre de
catálogo. Las frases desconocidas, consultas de estado y conexiones no generan
respuestas. Si falta la confirmación USB, no se anuncia la acción como realizada.
Si falla la voz después de confirmar una acción, el avatar conserva la acción
y el panel informa el error sin volver a enviar la orden.

## Reproducción e interrupciones

El panel reproduce **una sola frase a la vez**. Mientras habla, se pueden
seleccionar nuevas acciones desde **Catálogo**: el avatar las aplica al recibir
la orden y el panel conserva únicamente la respuesta confirmada más reciente.
Al terminar la frase actual, reproduce esa última respuesta; no anuncia todas
las acciones intermedias. La espera máxima es de **15 segundos** desde la
confirmación: una respuesta que supera ese plazo se descarta.

- **Detener** corta el audio y descarta la respuesta pendiente.
- Desactivar **Activar voz** hace lo mismo y bloquea nuevas reproducciones.
  Volver a activarlo no repite ninguna frase anterior.
- Desconectar el ESP32 descarta lo pendiente y detiene una respuesta del
  dispositivo que estuviera sonando. Una prueba de texto independiente puede
  continuar. Reconectar no reproduce respuestas antiguas.
- Cerrar el panel cancela el audio y descarta lo pendiente; no se guarda una
  cola entre sesiones.
- Un error de reproducción descarta lo pendiente y se informa en **Voz**, sin
  reintentar automáticamente. Se puede iniciar una nueva prueba o acción.

Detener o silenciar también invalida las respuestas de órdenes enviadas o
frases reconocidas anteriormente cuya confirmación todavía no llegó. Esto
evita que un resultado tardío vuelva a crear audio cancelado, incluso si se
reactiva la voz antes de recibirlo. Las acciones ya enviadas al avatar siguen
su curso; estos controles interrumpen su respuesta hablada.

**Probar voz** no acumula pedidos: se habilita cuando no hay una reproducción
ni respuesta pendiente. El ayudante de voz se termina y libera en su trabajador
al finalizar, cancelar o fallar; la interfaz sigue atendiendo eventos durante
esa limpieza.

## Coordinación entre voz y micrófono

Las pruebas de la pestaña **Voz**, las respuestas confirmadas y cualquier texto
entregado a `app.speak_text` usan la misma protección:

- Pausan la detección antes de iniciar el motor de voz.
- Descartan la frase parcial, el audio previo y cualquier captura pendiente.
- Ignoran el audio recibido mientras habla Aubar, sin transcribirlo ni enviarlo
  al ESP32.
- Mantienen el micrófono protegido durante **350 ms** después del final, una
  cancelación o un error de reproducción.
- Solo reanudan la escucha automática si la casilla sigue activada y la conexión
  USB y el micrófono continúan disponibles.

Si se apaga el micrófono durante una reproducción, queda apagado al terminar.
Una desconexión tampoco reactiva la escucha al reconectar. Cerrar el panel
cancela la reproducción y la captura. Desactivar únicamente la voz permite
recuperar la escucha, si esta sigue activada, después de la breve espera.

La captura manual nunca se abre automáticamente: su botón vuelve a habilitarse
cuando finaliza la protección. Si se interrumpe la calibración del ruido
ambiente para hablar, se vuelve a calibrar antes de aceptar nuevas frases.
El panel indica cuándo está en pausa y cuándo vuelve a estar listo para escuchar.

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
volumen y la coordinación con el micrófono. Esta entrada se utiliza desde el
hilo de Tk; las respuestas generadas por otro trabajador se entregan a ese hilo.
Las llamadas directas al motor de bajo nivel no sustituyen esta entrada del panel.
`responses.confirmation_text(action)`
es la fuente inicial de respuestas predefinidas y no depende del motor de voz.
La aplicación permite sustituirla mediante `reply_provider`; esa función debe
ser rápida y local. Una futura integración de IA puede generar texto en su
propio trabajador y entregarlo a la misma salida de voz desde la interfaz.

## Validación

Las pruebas de `tests/pc/test_speech.py` cubren ejecución asíncrona, continuidad
del panel y USB, texto literal, ausencia de voz española, errores del ayudante,
tiempo de espera y cierre de la aplicación. No reproducen audio real ni abren
el micrófono. Las pruebas de `tests/pc/test_responses.py` también verifican las
respuestas del catálogo, confirmación previa, silenciamiento, errores y pausa
de escucha. `tests/pc/test_playback_gate.py` cubre la coordinación de pruebas
y texto libre, descarte del audio propio, espera posterior, interrupciones,
errores, apagado del micrófono, reconexión y recalibración.
`tests/pc/test_reply_queue.py` verifica ráfagas de acciones, reemplazo por la
última respuesta, vencimiento, confirmaciones tardías, interrupciones y
recuperación sin repetir audio. Las pruebas del motor también simulan fallos
de comunicación y comprueban que el proceso de voz se termine antes de permitir
otra reproducción.
La comprobación audible se realiza por separado.
El [procedimiento de validación del flujo completo](validacion-voz.md) reúne
los escenarios automáticos y los pasos para comprobar placa, micrófono y voz.

Referencia del tratamiento de texto:
[SpeechVoiceSpeakFlags de Microsoft SAPI](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee125223(v=vs.85)).
