# Validación del flujo de voz

El flujo esperado es: detectar una frase, comprobar «Aubar» y el comando,
enviar una única orden USB, esperar su confirmación y estado, reproducir la
respuesta y volver a escuchar después de la protección contra el eco.

## Pruebas automáticas

Desde la raíz del proyecto, con el entorno preparado:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/pc -q
```

Para ejecutar únicamente los escenarios que atraviesan los componentes:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/pc -p test_voice_workflow.py -v
```

Estos escenarios usan la aplicación Tk, el detector de voz, el reconocedor
local y la sesión USB del proyecto. Sustituyen los dispositivos de entrada,
el decodificador de palabras, el transporte serie y la salida audible por
simulaciones controladas. No cargan el modelo Vosk, abren COM3 ni reproducen
sonido. La simulación serie devuelve ACK y estado; puede aplicar una orden y
perder su ACK para comprobar que el panel no la repita ni anuncie un éxito.

Cubren un recorrido con expresiones, animaciones, miradas y cambio de modo;
rechazo de frases sin activación, desconocidas y negadas; descarte de audio
durante una respuesta; pérdida de confirmación y reconexión; silenciamiento,
interrupción y apagado explícito del micrófono.

## Comprobación con la placa y el micrófono

Se necesita la Waveshare ESP32-S3-LCD-1.47B con el firmware del proyecto,
protocolo USB 4, el modelo de reconocimiento español y la voz Dora instalados,
y un micrófono de la PC. Usar el puerto de la placa; en la PC de validación es **COM3**.
Cerrar otros paneles o monitores serie que estén usando ese puerto.

1. Abrir `.\tools\start_control.ps1`, conectar el dispositivo, elegir el
   micrófono y activar **Activar voz** y la escucha automática. Esperar la
   calibración antes de hablar.
2. Decir **«Aubar, enojado derecha»**. Debe cambiar la expresión y la mirada,
   mostrar la confirmación USB y decir «Estoy enojado mirando a la derecha»
   una sola vez. Esperar a que vuelva a escuchar.
3. Decir **«Aubar, celebrar izquierda»**. Debe animarse mirando a la izquierda
   y responder «Voy a celebrar mirando a la izquierda». Después decir
   **«Aubar, derecha»**: debe conservar la animación y cambiar la mirada.
4. Probar **«contento»** sin «Aubar», **«Aubar, hoy hace frío»** y
   **«Aubar, no te pongas contento»**. No deben enviar órdenes ni generar
   respuestas. Una nueva frase válida debe seguir funcionando.
5. Desactivar **Activar voz** y decir **«Aubar, contento»**. Debe aplicar la
   expresión sin hablar. Reactivar la voz no debe reproducir esa respuesta
   anterior. Una nueva orden válida debe responder normalmente.
6. En **Voz**, iniciar una prueba de texto larga y aplicar varias animaciones
   desde **Catálogo** mientras habla. Debe terminar la frase actual y anunciar
   únicamente la última respuesta pendiente, sin voces superpuestas. Repetir
   y pulsar **Detener**: no debe reproducir lo pendiente.
7. Apagar el micrófono mientras habla. Al terminar debe seguir apagado; volver
   a activarlo explícitamente permite nuevos comandos.
8. Desconectar el cable USB, esperar el aviso, volver a enchufarlo y conectar
   desde el panel. La escucha debe permanecer apagada y no deben repetirse
   órdenes ni respuestas anteriores. Activar la escucha y probar una orden
   nueva.
9. Decir **«Aubar, modo automático»** para volver a la demostración del avatar.
   Cerrar el panel mientras reproduce una prueba de voz: debe detener el audio
   y liberar la entrada de micrófono y el puerto USB.

La orden puede haberse aplicado si se pierde su confirmación. El panel debe
informar esa incertidumbre, sin reenvío ni respuesta hablada de éxito.
Los controles de reproducción y sus límites se detallan en la
[guía de voz local](voz-local.md#reproducción-e-interrupciones).

## Registro de validación

Validación del 27 de octubre de 2026, sobre Windows, con Python 3.14.3,
modelo `vosk-model-small-es-0.42`, Microsoft Sabina Desktop (`es-MX`) y la placa
en COM3 con protocolo 4.

- **113 pruebas automáticas aprobadas**, incluidas las tres del flujo completo.
- La comprobación técnica utiliza audio sintético de entrada: no equivale a
  una prueba acústica con el micrófono físico. Comprueba la segmentación,
  Vosk real, las órdenes y estados del ESP32 real y la reproducción SAPI real.
  Se verificaron enojado/derecha, celebrar/izquierda, derecha conservando la
  animación, contento con voz desactivada y pensar/centro después de reconectar.
  Se rechazaron una frase negada y una activación con «Kirby», se descartó la
  entrada durante el audio y no hubo repeticiones al reactivar o reconectar.
- **Comprobación acústica y visual confirmada por el usuario** con su
  micrófono, placa y parlantes: comandos combinados y aislados, respuesta
  única, regreso a la escucha y rechazo de una frase desconocida. También
  confirmó el apagado del micrófono durante la respuesta, reconexión sin
  repeticiones, una orden nueva después de reconectar y cierre del panel
  interrumpiendo el audio.

### Cambio a Dora, voz femenina local

También el 27 de octubre de 2026 se cambió la salida predeterminada a
**Kokoro v1.0 / `ef_dora`**, ejecutada en CPU con `kokoro-onnx==0.4.7`.
La validación anterior con Sabina queda como registro de la primera versión.

- **119 pruebas aprobadas** después del cambio, más comprobación de
  dependencias sin incompatibilidades (`pip check`).
- Se repitió el recorrido técnico con Vosk real, entrada sintética y COM3,
  ahora reproduciendo con Dora: expresiones, animaciones, miradas, frases
  rechazadas, voz desactivada y reconexión sin repeticiones.
- Se verificó que detener durante la generación termina el ayudante y que
  el mismo motor vuelve a reproducir una frase nueva.
- El usuario confirmó la muestra inicial y luego el funcionamiento en el
  panel con comandos de voz, regreso a la escucha y **Detener**.

El reconocimiento depende del ruido ambiente y de la pronunciación. La escucha
se pausa mientras Aubar habla: no acepta interrupciones por voz durante su
respuesta; se usa **Detener** para cortarla. Las respuestas actuales son
predefinidas y este flujo todavía no incorpora una IA conversacional.
