# Protocolo USB — Aubar Bot

## Transporte

USB CDC a 115200 baudios, mensajes ASCII terminados en LF o CRLF.
Máximo 64 bytes antes de LF, incluido el CR opcional. Comandos en mayúsculas,
argumentos en minúsculas y un solo espacio. La PC espera una respuesta antes
de enviar la siguiente orden. No se intercalan anuncios ni mensajes de depuración.

## Comandos y respuestas — versión 4

| Mensaje | Respuesta |
| --- | --- |
| `PING` | `OK PONG 4` |
| `STATUS` | Estado actual, como el ejemplo siguiente |
| `EXPRESSION <id>` | `OK APPLIED EXPRESSION <id>` |
| `ANIMATION <id>` | `OK APPLIED ANIMATION <id>` |
| `EXPRESSION <id> <mirada>` | `OK APPLIED EXPRESSION <id> <mirada>` |
| `ANIMATION <id> <mirada>` | `OK APPLIED ANIMATION <id> <mirada>` |
| `LOOK izquierda`, `LOOK centro`, `LOOK derecha` | `OK APPLIED LOOK <dirección>` |
| `MODE manual`, `MODE auto` | `OK APPLIED MODE <modo>` |

Los 28 IDs de expresión y 23 de animación están en el
[catálogo del avatar](catalogo-avatar.md). Se conservan los IDs originales del
protocolo: neutral, contento, sorprendido, dormido y enojado.

```text
OK STATUS mode=manual expression=enojado look=izquierda animation=none
```

`animation=none` indica una pose fija. Con una secuencia activa, el campo
contiene su ID y `expression` identifica el paso actual. La mirada informada
es el destino manual efectivo; durante una secuencia es centro porque la
dirección forma parte de los datos de cada pose, salvo que haya una mirada
explícita, que se informa y conserva durante toda la secuencia.

APPLIED confirma el destino lógico. El dibujo continúa después de responder:
las poses fijas se interpolan durante 450 ms; las miradas, durante 350 ms.
Las secuencias usan los tiempos exportados (transiciones de 500 ms más su
permanencia). Repetir una expresión fija no reinicia el parpadeo.

La versión 3 agregó ANIMATION y el campo animation. La versión 4 agrega la
mirada opcional de las expresiones y animaciones. La combinación se valida
completa antes de aplicar un único estado y emitir su confirmación. Un argumento
inválido no aplica ninguna parte de la orden. El panel acepta v2 y v3 para
las órdenes anteriores, pero exige v4 antes de enviar una combinación.

## Reglas de control

- Al encender, muestra neutral y centro durante un segundo; luego reproduce
  idle y continúa con todas las animaciones, una vuelta completa de cada una.
- ANIMATION activa manual y repite la secuencia elegida desde su primer paso.
- EXPRESSION detiene una secuencia y activa manual. LOOK activa manual y cambia
  la mirada sin detener la animación actual. MODE manual detiene la secuencia
  en la expresión actual.
- Las expresiones despiertas siguen parpadeando. Las poses cerradas conservan
  los ojos cerrados; también respetan una mirada explícita.
- La mirada explícita orienta la cabeza y añade desplazamiento de ojos dentro
  de los márgenes del cuerpo. Se conserva entre pasos y nuevas selecciones.
- Sin mirada explícita se respetan las orientaciones del catálogo.
- Las animaciones usan sus propios intervalos de parpadeo y poses exportadas.
- MODE auto elimina la orientación explícita y reinicia la lista desde neutral.
- BOOT adelanta a la siguiente animación cuando hay una secuencia activa o
  el modo es automático. En manual con pose fija recorre las 28 expresiones.
- USB tiene prioridad si coincide con BOOT o un paso automático.
- STATUS y PING no alteran los temporizadores. Desconectar USB conserva el
  estado; RESET vuelve al modo automático.

## Errores y límites

| Respuesta | Motivo |
| --- | --- |
| `ERR EMPTY` | Línea vacía |
| `ERR UNKNOWN_COMMAND` | Comando desconocido |
| `ERR INVALID_ARGUMENT` | Argumento ausente, desconocido o adicional |
| `ERR LINE_TOO_LONG` | Más de 64 bytes antes de LF |
| `ERR INVALID_CHARACTER` | ASCII no imprimible u otro carácter inválido |

Una línea inválida no cambia el estado. Las líneas largas se descartan hasta
LF, sin ejecutar su sufijo. Los mensajes incompletos esperan LF.
Cada iteración procesa hasta 128 bytes y una línea. La recepción tiene un
búfer de 2048 bytes; las respuestas se envían parcialmente según el espacio
USB disponible, sin esperar a que la PC lea. El LF final se encola por separado
cuando el resto de la respuesta salió del búfer: esto evita que un paquete
completo de 64 bytes del HWCDC quede pendiente en el host. Cada consulta sigue
siendo una única línea ASCII, sin pausas bloqueantes ni reenvíos.

## Pruebas

Cerrar el panel y ejecutar con el firmware normal:

```powershell
.\tools\test_usb_protocol.ps1 -Port COM3
.\tools\test_avatar_control.ps1 -Port COM3
.\.venv\Scripts\python.exe tools/test_catalog_usb.py --port COM3
```

Las primeras dos prueban mensajes fragmentados, errores, recuperación, estados,
persistencia manual y retorno al modo automático. La última recorre las 51
opciones y las 153 combinaciones, confirma cada acción y comprueba que la
animación conserva la mirada entre pasos, dejando el modo automático al terminar.

El sketch separado `tests/CatalogValidation` reúne además las comprobaciones
de control, transporte simulado con contrapresión, secuencias y renderizado.
Después de usarlo hay que volver a cargar `firmware/KirbyPantalla`.
El sketch `tests/CombinedControls` verifica todas las combinaciones, sus pasos,
la mirada aislada durante una animación, el parser y los márgenes del dibujo.
