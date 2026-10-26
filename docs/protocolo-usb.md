# Protocolo USB — Aubar Bot

## Transporte

Puerto serie USB CDC, configurado por la herramienta de PC a **115200 baudios**.
Mensajes ASCII, uno por línea, terminados en LF (\n). También se acepta CRLF.
Máximo: **64 bytes antes de LF**, incluido el CR opcional. No enviar bytes NUL,
tabuladores, caracteres de control ni texto UTF-8. Las frases en español se
convertirán a estos comandos en la PC.

Las palabras de comando se escriben en mayúsculas y los argumentos en minúsculas,
con exactamente un espacio. No se aceptan espacios iniciales, finales o adicionales.
La PC debe esperar una respuesta completa antes de enviar el siguiente mensaje.

## Comandos

| Mensaje | Significado |
| --- | --- |
| `PING` | Consultar disponibilidad y versión del protocolo |
| `STATUS` | Consultar modo, expresión y mirada seleccionados |
| `EXPRESSION neutral` | Seleccionar expresión neutral |
| `EXPRESSION contento` | Seleccionar expresión contenta |
| `EXPRESSION sorprendido` | Seleccionar expresión sorprendida |
| `EXPRESSION dormido` | Seleccionar expresión dormida |
| `EXPRESSION enojado` | Seleccionar expresión enojada |
| `LOOK izquierda` | Seleccionar mirada a la izquierda |
| `LOOK centro` | Seleccionar mirada al centro |
| `LOOK derecha` | Seleccionar mirada a la derecha |
| `MODE manual` | Seleccionar modo manual |
| `MODE auto` | Seleccionar demostración automática |

## Respuestas — versión 2

`PING` responde `OK PONG 2`, donde `2` es la versión del protocolo.
Los comandos de control válidos responden `OK APPLIED`, seguido del comando
y argumento, por ejemplo: `OK APPLIED EXPRESSION enojado`.

**APPLIED confirma que se aplicó el estado lógico de destino.** La transición
visual sigue ejecutándose sin bloquear: expresiones en 450 ms y miradas en 350 ms.
Repetir la expresión actual no reinicia su parpadeo.

`STATUS` devuelve una línea con este formato y orden de campos:

```text
OK STATUS mode=manual expression=enojado look=izquierda
```

Los valores de `mode`, `expression` y `look` son los de los comandos anteriores.
La mirada informada es el destino efectivo, no la posición de un cuadro
intermedio durante una transición. Consultar `STATUS` o `PING` no cambia el
modo ni reinicia los temporizadores.

La versión 1 de TK15 respondía `VALIDATED` sin aplicar acciones. Los clientes
deben usar las respuestas de la versión 2 para este firmware.

## Reglas de control

- Al encender, arranca la demo en modo automático desde neutral y centro.
- `EXPRESSION` y `LOOK` activan el modo manual y conservan la otra selección.
- `MODE manual` congela la expresión y el destino de mirada actuales.
- En manual, la demo y las miradas periódicas quedan detenidas; el parpadeo
  sigue activo en las expresiones despiertas.
- Dormido mantiene los ojos cerrados y centrados. Una mirada manual solicitada
  se conserva para cuando se seleccione una expresión despierta.
- `MODE auto` reinicia la demo desde neutral y centro, con un nuevo intervalo
  de 12 segundos. Esto también ocurre si ya estaba en automático.
- BOOT avanza una expresión en ambos modos. En automático reinicia el tiempo
  de esa expresión; en manual conserva el modo y la mirada solicitada.
- Si un comando USB coincide con BOOT o un cambio automático, USB tiene prioridad.
- Cerrar la conexión USB conserva el modo seleccionado. RESET vuelve a iniciar
  el modo automático.

Cada respuesta termina en LF. El puerto se reserva para el protocolo:
no intercala mensajes de depuración ni anuncios al arrancar.

| Error | Motivo |
| --- | --- |
| `ERR EMPTY` | Línea vacía |
| `ERR UNKNOWN_COMMAND` | Palabra de comando desconocida |
| `ERR INVALID_ARGUMENT` | Argumento ausente, desconocido o adicional |
| `ERR LINE_TOO_LONG` | Mensaje que excede 64 bytes antes de LF |
| `ERR INVALID_CHARACTER` | Carácter que no pertenece al ASCII imprimible |

Una línea inválida no genera un comando ni modifica el avatar. Las líneas
demasiado largas se descartan completas hasta LF; su sufijo no se interpreta
como otro mensaje. Un mensaje incompleto no tiene efecto hasta recibir LF.

## Límites de procesamiento

Cada iteración procesa como máximo 128 bytes de entrada y una línea completa.
La cola de recepción USB se configura a 2048 bytes para absorber ráfagas mientras
se dibuja un cuadro. Este límite no cambia el máximo de 64 bytes por mensaje ni
la regla de esperar una respuesta antes de enviar el siguiente comando.
Los buffers tienen tamaño fijo. Las respuestas se escriben solamente cuando
el puerto dispone de espacio y se retoman en siguientes iteraciones si falta.
El tiempo de espera de escritura del controlador USB se configura a cero.
Si la PC deja de leer, se pausa la recepción del protocolo y las animaciones
siguen actualizándose. No hay espera por la conexión ni por el fin de una línea.
Al conectar un cliente puede enviarse LF y luego `PING`, descartando las respuestas
anteriores hasta recibir `OK PONG 2`, para terminar una línea que otro cliente
hubiera dejado incompleta. Esta sincronización no cambia el estado del avatar.

## Prueba manual

Cerrar cualquier otra herramienta que use el puerto. Desde el monitor serie
de Arduino IDE, seleccionar el puerto de la placa, 115200 baudios y fin de línea
**Nueva línea** o **Ambos NL y CR**.

Enviar `PING`: debe responder `OK PONG 2`.
Enviar `EXPRESSION enojado`: debe responder `OK APPLIED EXPRESSION enojado`
y activar la expresión en modo manual.
Enviar `LOOK izquierda` y después `STATUS`: debe informar
`OK STATUS mode=manual expression=enojado look=izquierda`.
Enviar `MODE auto`: debe responder `OK APPLIED MODE auto` y reiniciar la demo.
Enviar `LOOK arriba`: debe responder `ERR INVALID_ARGUMENT`.

El número de puerto COM varía según la PC. El micrófono y la interpretación de
frases pertenecen a la herramienta de PC de las siguientes tareas del sprint.

## Pruebas automatizadas

Desde PowerShell, en la raíz del proyecto y con el firmware cargado:

```powershell
.\tools\test_usb_protocol.ps1 -Port COM3
.\tools\test_avatar_control.ps1 -Port COM3
```

La prueba abre el puerto, envía comandos válidos e inválidos, verifica respuestas,
comprueba mensajes fragmentados y confirma recuperación después de una línea
demasiado larga. La segunda prueba verifica la persistencia manual durante
13 segundos y la reanudación automática durante otros 13; deja enojado mirando
a la izquierda en manual para la comprobación visual. Cerrar el monitor serie
antes de ejecutar las pruebas.

`tests/AvatarControl/AvatarControl.ino` verifica las reglas del controlador
durante la compilación, incluidos BOOT, prioridades, sueño y consultas.

`tests/UsbProtocol/UsbProtocol.ino` prueba el parser y el transporte con un puerto
simulado, incluidos límites de procesamiento y respuestas enviadas byte a byte
por falta de espacio. Es un sketch de pruebas separado del firmware normal.
