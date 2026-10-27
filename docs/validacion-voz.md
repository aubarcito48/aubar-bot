# Validación de voz y conversación

El flujo esperado es: detectar una frase, comprobar «Aubar» y el comando,
enviar una única orden USB, esperar su confirmación y estado, reproducir la
respuesta y volver a escuchar después de la protección contra el eco.
Si la frase activada no es un comando local, se consulta a Groq con el contexto
completado, se valida su selección visual y Dora lee únicamente la respuesta.
Las consultas escritas comparten ese contexto, pero no se leen automáticamente.

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

Para la conversación, ejecutar también:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/pc -p test_voice_conversation.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests/pc -p test_ai_avatar.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests/pc -p test_ai_cancellation.py -v
.\.venv\Scripts\python.exe -m pip check
```

Estas pruebas simulan Groq y los dispositivos: no gastan cuota ni necesitan
credenciales. Comprueban contexto compartido, prioridad de comandos locales,
selecciones visuales válidas y reemplazo por neutral, pausa de escucha,
cancelación, fallos de API y audio, respuestas tardías y reconexiones.

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
4. Con escucha automática, probar **«contento»** sin «Aubar» y **«Aubar»**
   solo. No deben enviar órdenes ni generar respuestas. Una nueva frase válida
   debe seguir funcionando. Con IA configurada, **«Aubar, hoy hace frío»** y
   **«Aubar, no te pongas contento»** son consultas abiertas: no se interpretan
   como comandos locales, aunque la respuesta de IA puede proponer una pose.
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

## Comprobación de conversación con IA

Además de los requisitos anteriores, configurar Groq en el `.env` local según
la [guía de IA](groq.md). Se necesita internet para las consultas a Groq;
Vosk, Dora y los comandos locales funcionan sin ese servicio. No copiar la clave
en capturas, incidencias ni registros. No hace falta modificar el firmware.

1. En **IA**, recargar la configuración y usar **Probar conexión**. Debe
   responder sin bloquear las pestañas, sin agregar un turno al contexto ni
   leer la prueba en voz alta.
2. Conectar la placa. Mantener pulsado el botón del micrófono, esperar a
   **Escuchando**, decir **«Mi mascota se llama Luna»** y soltar. Debe verse
   **Pensar** durante la espera y luego una selección visual válida; Dora lee
   una única respuesta, sin JSON ni identificadores. En este modo no hace
   falta decir «Aubar».
3. Preguntar **«¿Cómo se llama mi mascota?»** mediante el botón o el campo
   de IA. Debe recordar Luna. Una consulta escrita solo muestra el texto.
4. Activar la escucha automática y esperar la calibración. Decir
   **«Aubar, contame algo interesante»**. Debe responder una sola vez y volver
   a escuchar. La entrada se pausa durante la espera y reproducción: el audio
   de Dora no debe producir otra consulta ni un comando.
5. Decir **«Aubar, enojado derecha»** y luego **«Aubar, celebrar izquierda»**,
   esperando entre frases. Deben ejecutarse como comandos locales, con su
   confirmación USB y frase predefinida, sin consumir una consulta de Groq.
6. Hacer una consulta nueva y pulsar **Cancelar** durante la espera o mientras
   habla. Debe detener el turno pendiente sin repetirlo; el historial completado
   se conserva. Si la respuesta ya se incorporó antes de cancelar su narración,
   su texto sigue en el historial. Una consulta nueva debe funcionar.
7. Apagar la escucha automática mientras Dora habla. Al finalizar debe seguir
   apagada. Reactivarla requiere una acción explícita. **Detener** en Voz corta
   la narración; **Cancelar** en IA cancela el turno pendiente completo.
8. Desconectar el USB durante una consulta. Tras reconectar desde el panel, no
   deben ejecutarse respuestas o poses pendientes. La escucha permanece apagada;
   reactivarla y comprobar una consulta y un comando nuevos.
9. Pulsar **Nueva conversación**: se vacía el contexto y se restaura neutral si
   la IA todavía controla la pose. Preguntar por la mascota sin volver a dar su
   nombre: Aubar debe indicar que no tiene ese dato. Cerrar el panel mientras
   habla debe detener el audio y liberar micrófono y puerto USB.

Ante un fallo de red, límite de cuota, tiempo de espera o credencial inválida,
el panel debe informar un error sin exponer la clave ni inventar una respuesta.
El turno fallido no se agrega al contexto ni se reintenta automáticamente.
Los controles locales siguen disponibles; una consulta posterior puede realizarse
cuando se restablezca el servicio. Los fallos y las cancelaciones durante la
conexión HTTP se verifican de forma controlada en las pruebas automáticas.

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

### Conversación con Groq — cierre técnico de TK34

Validación del 27 de octubre de 2026 sobre Windows y Python 3.14.3, con
Vosk español, Groq, Kokoro / Dora y Waveshare ESP32-S3-LCD-1.47B en COM3:

- **194 pruebas aprobadas** y `pip check` sin incompatibilidades.
- Entrada PCM sintética a través del panel, Vosk y Groq reales, respuesta con
  Dora, y regreso a la escucha sin repetir la entrada durante la reproducción.
  Esta comprobación no sustituye la prueba acústica con el micrófono físico.
- Consultas manual y automática con contexto compartido; Pensar y selección
  visual final confirmadas por la placa antes de la narración. El historial
  contiene el texto de respuesta y no los metadatos de selección visual.
- Comando local posterior confirmado en COM3 y narrado sin otra llamada a Groq.
  Nueva conversación elimina el contexto acumulado.
- Cancelación de una consulta HTTPS real sin historial ni audio tardíos;
  consulta nueva después de cancelar; cierre durante una consulta que interrumpe
  la conexión y libera COM3. Los controles caben en una ventana de 760 × 650.
- Los fallos de API y audio, las selecciones inválidas y las carreras de
  reconexión se cubren con simulaciones controladas en la suite automática.
- El usuario confirmó con su micrófono y parlantes el recuerdo de Luna entre
  consultas, una sola respuesta con Dora y expresiones, regreso a la escucha
  y ejecución del comando local combinado. También confirmó que Nueva
  conversación elimina el dato anterior y que Cancelar corta la respuesta
  y permite continuar con una consulta nueva.

El reconocimiento depende del ruido ambiente y de la pronunciación. La escucha
se pausa mientras Aubar habla: no acepta interrupciones por voz durante su
respuesta; se usa **Detener** para cortar la lectura o **Cancelar** para cancelar
el turno de IA. Los comandos locales conservan sus frases predefinidas; las
consultas abiertas reciben respuestas generadas por Groq.
