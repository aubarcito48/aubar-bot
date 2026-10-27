# Panel de Aubar Bot

Aplicación de escritorio para seleccionar el puerto USB, conectar la placa y
consultar su expresión, modo, mirada y animación. El catálogo completo requiere
firmware con protocolo **v3**; los comandos combinados necesitan **v4**.
Las funciones anteriores también aceptan v2.
La conexión y las consultas no cambian el modo del avatar.
La pestaña Micrófono permite capturar audio local sin necesitar conectar la placa.

## Requisitos

- Windows con [Python 3.11 o superior](https://www.python.org/downloads/).
  La instalación oficial debe incluir Tcl/Tk y tkinter; se recomienda instalar
  también el lanzador `py`.
- Placa conectada con cable USB de datos y firmware cargado.
- [pySerial 3.5](https://pyserial.readthedocs.io/en/latest/), instalado por el
  lanzador en el entorno local `.venv`.
- [sounddevice 0.5.5](https://python-sounddevice.readthedocs.io/en/0.5.5/),
  para enumerar y capturar entradas de audio; el paquete de Windows incluye PortAudio.
- [Vosk 0.3.45](https://alphacephei.com/vosk/) y el modelo
  [vosk-model-small-es-0.42](https://alphacephei.com/vosk/models), para reconocer
  español localmente. El modelo tiene licencia Apache 2.0.
- Micrófono habilitado en Windows para aplicaciones de escritorio.
- [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx) y el modelo
  Kokoro v1.0 para la voz femenina Dora en español, instalados por el lanzador.
- Internet solo para instalar dependencias y descargar modelos por primera vez.

Validado con Python 3.14.3 en Windows y la Waveshare ESP32-S3-LCD-1.47B.

## Abrir la herramienta

Desde PowerShell, en la raíz del repositorio:

```powershell
.\tools\start_control.ps1
```

El lanzador crea `.venv` si no existe, comprueba las dependencias y abre la
ventana. También descarga el modelo de reconocimiento español de unos 39 MB
y el modelo de voz con sus estilos (unos 354 MB) la primera vez, verificando
sus SHA256. No instala paquetes globales de Python. Si Python no está en PATH,
se puede indicar su ejecutable:

```powershell
.\tools\start_control.ps1 -PythonExecutable 'C:\ruta\a\python.exe'
```

También se puede preparar y ejecutar manualmente:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r pc\requirements.txt
.\.venv\Scripts\python.exe tools\install_voice_model.py
.\.venv\Scripts\python.exe tools\install_tts_model.py
.\.venv\Scripts\python.exe -m pc.aubar_control
```

## Uso

1. Cerrar Arduino Monitor Serie u otra herramienta que ocupe el puerto.
2. Abrir el panel y seleccionar el puerto. Se propone el del ESP32 si aparece
   identificado como dispositivo de Espressif, pero no se conecta automáticamente.
3. Pulsar **Conectar**. La aplicación verifica `PING` y consulta `STATUS`.
4. Consultar los valores de expresión, modo y mirada. Se actualizan cada 1,5 segundos.
   **Consultar estado** permite solicitar una actualización inmediata.
5. Pulsar **Desconectar** para liberar el puerto. La placa conserva su modo.

Ante un error de comunicación, el panel deja de consultar, cierra el puerto y
limpia los valores para no presentar información antigua como actual.
Reconectar el cable, pulsar **Buscar puertos**, seleccionar el puerto y volver a
**Conectar**. El número COM puede cambiar. La reconexión es manual.

La interfaz trabaja en el hilo de Tk; USB y audio usan trabajadores separados.
Una operación del micrófono no bloquea la conexión USB.

## Capturar voz

1. Abrir la pestaña **Micrófono**. La búsqueda no abre ningún flujo de captura.
2. Seleccionar la entrada. Se propone el micrófono predeterminado de Windows.
   Una misma entrada puede aparecer varias veces por sus distintas interfaces
   (MME, DirectSound o WASAPI); el nombre incluye la interfaz y el índice.
3. Mantener pulsado **Mantené pulsado para hablar** mientras se habla.
   También funciona la barra espaciadora cuando el botón tiene el foco.
   Esperar la indicación **Escuchando** antes de empezar la frase: aparece al
   recibir el primer bloque del micrófono, no solo al abrir el dispositivo.
4. Durante la captura se muestra **Escuchando**, un nivel de entrada y la duración.
5. Soltar el botón para finalizar. La indicación cambia a **Micrófono apagado**
   y muestra la duración capturada. Las capturas menores de 0,15 s se descartan.

La captura manual se detiene al perder el foco de la ventana, minimizarla, cerrarla
o alcanzar 10 segundos. Al soltar el botón se rechazan inmediatamente nuevas
muestras, incluso si la apertura del dispositivo todavía está pendiente.

El audio queda en memoria y se reemplaza en la próxima captura; no se guarda
automáticamente ni se envía a servicios externos o al ESP32. Se captura PCM
mono de 16 bits, preferentemente a 16 kHz;
si el dispositivo no admite esa frecuencia, se utiliza su frecuencia nativa
y se conserva ese dato junto con el audio.

Si no hay nivel, elegir otra entrada y comprobar que el micrófono no esté silenciado.
Si falla la apertura, revisar los permisos de **Micrófono** en Configuración de
Windows, habilitar el acceso para aplicaciones de escritorio y volver a buscar.
Un error del micrófono no desconecta el ESP32.

## Reconocimiento de comandos

Al soltar el botón, el micrófono se cierra y la captura se transcribe con Vosk
en un trabajador de audio. La interfaz y el USB siguen funcionando. El modelo
se carga en la primera captura con voz y se reutiliza en las siguientes.
La sección **Lo que escuché** muestra el texto y la acción asociada.

| Frase de ejemplo | Acción detectada |
| --- | --- |
| «Contento» | Expresión contenta |
| «Ponete enojado» | Expresión enojada |
| «Dormite» / «Duerme» / «A dormir» | Expresión dormida |
| «Neutral» / «Sorprendido» | Expresión indicada |
| «Mirá a la izquierda» / «Mirá a la derecha» | Mirada indicada |
| «Mirá al centro» | Mirada centrada |
| «Modo automático» / «Modo manual» | Modo indicado |

Se ignoran mayúsculas, tildes y puntuación. Se acepta «Aubar» al principio
y «por favor» al final. Se admite la separación «dormí te» que puede producir
el modelo al transcribir el voseo.
Para la expresión contenta se utiliza solamente «contento», sin «ponete»,
«ponte» ni «pone». El texto mostrado conserva lo transcrito.
La coincidencia debe ser con la frase completa:
«no te pongas enojado» o «creo que está contento» no se convierten en órdenes.
No se usa una gramática restringida que fuerce cualquier audio a una orden.

El silencio, las frases desconocidas y los resultados de confianza baja quedan
sin acción y muestran un mensaje para repetir. La confianza del motor es una
heurística y no garantiza que toda transcripción sea correcta; el texto permite
comprobar qué entendió. Se rechazan palabras con confianza menor a 0,35 o un
promedio menor a 0,45. Una frase nueva borra la acción anterior.

## Enviar acciones por voz

Conectar primero el ESP32 en la pestaña **Dispositivo**. Luego, en **Micrófono**,
mantener el botón, esperar **Escuchando**, decir una frase conocida y soltar.
El panel muestra el texto, envía una sola orden y espera la respuesta exacta
`OK APPLIED`. Después consulta `STATUS`, actualiza los valores y muestra
**Confirmado por el ESP32**. La confirmación se refiere al destino lógico;
la transición visual termina de ejecutarse en la placa.

«Contento», «dormite» y las miradas activan el modo manual según las reglas del
firmware. «Modo automático» reinicia la demo desde neutral y centro.
Las frases desconocidas, el silencio y los resultados de baja confianza no envían
órdenes ni reutilizan la acción de una captura anterior.

La captura y el reconocimiento pueden probarse sin conectar la placa, pero la
acción no se enviará después de conectar: hay que repetir la frase.
Una captura iniciada en otra conexión tampoco se ejecuta tras reconectar.
Si el USB está consultando el estado, la orden espera ese resultado en la misma
conexión; no compite con otro hilo por el puerto.

Si se pierde la respuesta, la orden puede haberse aplicado. El panel lo informa,
cierra la conexión y **no reintenta automáticamente**. Si ya recibió la confirmación
pero falla la consulta de estado, distingue ambos resultados. Reconectar,
comprobar el estado y repetir la frase solamente si corresponde.

Para validar desconexiones: retirar el cable, esperar el aviso del panel,
volver a conectar y buscar el puerto si cambió. Una frase anterior no debe
ejecutarse al reconectar. Volver a hablar para enviar una orden nueva.

## Escucha automática con «Aubar»

1. Conectar el ESP32 en **Dispositivo** y elegir la entrada en **Micrófono**.
2. Activar **Escucha automática · «Aubar» + comando o pregunta**. Esperar la breve
   calibración del ruido ambiente sin hablar.
3. Cuando indique **Escucha automática activa**, decir una frase completa como
   **«Aubar, contento»**, **«Aubar, celebrar»** o **«Aubar, mirá a la izquierda»**.
4. Hacer una pausa de **0,8 segundos**: el panel transcribe, comprueba el nombre
   y la frase. Para un comando, espera la confirmación del ESP32 antes de
   volver a escuchar; una consulta abierta se identifica localmente.

No hay que mantener pulsado el botón. En este modo un comando sin «Aubar» no
actúa. El modo manual sigue disponible al apagar la casilla, y conserva sus
comandos anteriores sin exigir el nombre.

La escucha automática continúa al cambiar de ventana o minimizar. Se apaga al
desmarcar la casilla, cerrar el panel o perder la conexión USB. Al reconectar
hay que activarla nuevamente; no se ejecutan frases pendientes de una conexión
anterior. Desactivarla también descarta reconocimientos que aún no se enviaron.
Una orden que ya fue enviada puede terminar de aplicarse.

La detección usa el nivel de audio y conserva hasta 500 ms previos al comienzo
para no recortar las primeras sílabas. Descarta sonidos breves y frases que
superen 10 segundos, en vez de actuar sobre una frase truncada. Mientras se
reconoce o ejecuta una acción se pausa la recepción de nuevas frases. El audio
se procesa localmente y no se guarda en archivos. Conviene esperar a que el
panel vuelva a indicar que está escuchando antes de dar otra orden.

El modelo español distribuido no contiene «Aubar» en su diccionario. Para
verificar el nombre se usa un segundo reconocimiento fonético con «au bar»
y una opción de palabra desconocida, mientras el comando debe aparecer en
la transcripción libre con confianza suficiente. No se acepta «ayudar» como
alias de texto: ese texto puede aparecer en la transcripción de «Aubar», pero
el audio del nombre se comprueba por separado. Por eso el texto mostrado puede
diferir del nombre aunque la orden sea válida. Este mecanismo usa la
[adaptación de vocabulario de Vosk](https://alphacephei.com/vosk/adaptation);
no modifica ni reemplaza el modelo descargado.

Si la transcripción omite el nombre por completo y muestra solamente
«contento», el reconocedor también comprueba el audio anterior a esa primera
palabra. Solo acepta la activación si verifica allí el sonido de «Aubar»;
decir «contento» sin el nombre sigue sin activar la escucha automática.
El audio previo de 500 ms ayuda a conservar una activación más suave que el
resto de la frase. Si el nombre no llegó a capturarse, se descarta el resultado
en lugar de inferirlo a partir del comando.

## Identificar consultas abiertas

La sección **Lo que escuché** distingue los comandos del avatar de preguntas
y frases conversacionales. Ejemplos:

| Frase | Resultado |
| --- | --- |
| «Aubar, cómo estás» | Consulta: «cómo estás». |
| «Aubar, contame algo interesante» | Consulta: «contame algo interesante». |
| «Aubar, hola» | Consulta: «hola». |
| «Aubar, enojado derecha» | Comando local, con prioridad sobre la conversación. |
| «Aubar, no te pongas enojado» | Consulta; no ejecuta la expresión enojada. |
| «Cómo estás» sin el nombre | No se activa una consulta. |
| «Aubar» sin otra palabra | No genera una consulta ni una acción. |

Las consultas requieren **«Aubar» en la escucha automática**. En captura
manual, mantener pulsado el botón ya activa la consulta: se puede decir
directamente «contame algo interesante» sin el nombre. Los comandos manuales
conservan sus formas anteriores sin exigirlo. Si se dice el nombre y el audio
permite verificarlo, se retira de la consulta; en caso contrario se conserva
la transcripción completa, sin tratar palabras como «ahogar» como alias.
El nombre se verifica con el audio, sin convertir «ayudar» en un alias de texto.
Se admite una pausa de hasta 0,6 segundos después del nombre dentro de la misma
frase; una pausa de 0,8 segundos termina la captura. La comprobación también
alinea el final del nombre con la transcripción para no recortar una palabra
de la pregunta ni convertir una negación en un comando.

Las consultas aceptadas tienen hasta 1000 caracteres, confianza mínima por
palabra de 0,35 y promedio de 0,55. Los comandos automáticos mantienen los
umbrales de 0,55 y 0,65 respectivamente. Son filtros heurísticos, no garantías
de una transcripción perfecta. El silencio, los resultados poco claros o sin
activación válida no generan consultas.

En esta etapa el panel muestra **Consulta reconocida** y el contenido sin el
nombre de activación. Todavía no envía esa frase a Groq, no cambia el avatar
por ella ni reproduce una respuesta. Al terminar vuelve a escuchar si la
escucha automática sigue activa. La consulta identificada no se acumula para
enviarla después; una captura nueva, el apagado de la escucha, la desconexión
o el cierre descartan ese estado. **Probar conexión** en **IA** sigue siendo
una prueba independiente.

El ruido, las voces de fondo o una pronunciación parecida pueden producir
errores: la palabra de activación reduce las activaciones involuntarias sin
eliminarlas por completo. Revisar lo transcrito y la acción confirmada.

## Comandos combinados

Se puede añadir **izquierda**, **centro** o **derecha** a cualquier expresión
o animación:

- «Aubar, enojado derecha».
- «Aubar, contento izquierda».
- «Aubar, celebrar izquierda».
- «Aubar, pensar centro».
- «Aubar, dormir derecha».

También se aceptan «enojado mirando a la derecha», «celebrar y izquierda» y
«celebrar a la izquierda». En manual no hace falta decir el nombre; la escucha
automática siempre exige «Aubar».

Las 28 expresiones y 23 animaciones admiten las tres direcciones: **153
combinaciones**. Para una expresión con un nombre que ya incluye una dirección,
usar «expresión» y «mirando» para distinguir el nombre de la mirada solicitada.
Por ejemplo, «Aubar, expresión enojado izquierda mirando a la derecha» elige
la pose del catálogo *Enojado izquierda* y la orienta a la derecha.
«Aubar, enojado izquierda» elige la expresión básica enojado y mirada izquierda.

La combinación se aplica en **una sola orden USB** y se confirma completa;
no se envían dos órdenes independientes. Si falla la confirmación, no se repite.
Los firmwares anteriores a v4 rechazan la combinación desde el panel sin enviar
una parte de ella.

Las órdenes aisladas siguen disponibles: «Aubar, derecha», «Aubar, enojado»,
«Aubar, celebrar». Una mirada aislada cambia la orientación y conserva la
animación que esté reproduciéndose. La dirección explícita se mantiene al
cambiar de paso, de animación o de expresión; **«Aubar, centro»** la centra y
**«Aubar, modo automático»** restaura las orientaciones originales del catálogo.
Las poses dormidas conservan los ojos cerrados y también pueden orientarse.

## Configuración de IA

La pestaña **IA** permite revisar y recargar la configuración local de Groq.
La [guía de configuración](groq.md) explica `.env`, el modelo y el tiempo de
espera. **Probar conexión** envía una pregunta breve y muestra la respuesta
como texto, sin bloquear los controles locales. Abrir o recargar la
configuración no envía consultas al servicio.

El campo **Mensaje** permite conversar por texto con Aubar y mantener preguntas
de seguimiento. **Nueva conversación** borra el contexto de la sesión y
descarta respuestas anteriores pendientes. Se conservan como máximo seis
intercambios y 12 000 caracteres de historial; la [guía de Groq](groq.md#personalidad-y-conversación-por-texto)
detalla la personalidad, los límites y los reinicios. Las consultas reconocidas
por micrófono todavía no se envían automáticamente a la IA.

## Motor de salida de voz

El panel utiliza **Dora**, voz femenina española de Kokoro, que funciona en la
PC sin internet después de instalar el modelo. Es independiente de los
comandos del avatar. La pestaña **Voz** permite activarla, probar un texto,
ajustar el volumen y detener la reproducción. Muestra cuándo está hablando,
la voz utilizada y los posibles errores sin bloquear el panel ni el USB.

Desactivar la voz corta el audio actual; volver a activarla no repite la frase.
La prueba de voz también funciona con la escucha automática activada: el
micrófono se pausa antes de reproducir y se recupera después. Hay que terminar
una captura manual o reconocimiento en curso antes de iniciar la prueba.
Con la voz activada, Aubar responde después de confirmar la acción en el ESP32.
Por ejemplo: «Aubar, enojado derecha» produce «Estoy enojado mirando a la derecha».
Las selecciones del catálogo también tienen respuesta; las consultas de estado
y las órdenes no confirmadas no la generan.

Todas las reproducciones del panel pausan la detección mientras suena Aubar,
descartan el audio de ese intervalo y esperan 350 ms antes de recuperar la
escucha, siempre que siga activada. Si se apaga el micrófono durante la voz,
queda apagado; una desconexión o cierre tampoco lo reactiva.
La voz reproduce una frase a la vez y conserva únicamente la última respuesta
pendiente, por hasta 15 segundos. **Detener**, silenciar o desconectar descarta
lo pendiente; volver a activar o reconectar no repite frases anteriores.
La [guía de voz local](voz-local.md) explica las interrupciones, los controles,
las respuestas y la API de texto independiente que podrá utilizar una futura IA.

## Modelo local

El modelo está en `models/`, excluido de Git; el lanzador permite descargarlo
nuevamente. Las pruebas y la ejecución posterior a la instalación funcionan
sin internet. El instalador usa la URL oficial y fija el SHA256
`09b239888f633ef2f0b4e09736e3d9936acfd810bc65d53fad45261762c6511f`.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests\pc -v
```

Las pruebas usan puertos y entradas de audio simulados y una ventana Tk temporal,
sin necesitar el ESP32 ni activar el micrófono real. La validación con dispositivos
físicos se realiza por separado.

Los errores inesperados se registran en `pc/aubar-control.log`, excluido de Git.
El código de la aplicación está en `pc/aubar_control/`; el protocolo está en
[protocolo-usb.md](protocolo-usb.md).

## Catálogo completo

La pestaña **Catálogo** permite elegir las 28 expresiones y las 23 animaciones.
Conectar primero en **Dispositivo**, elegir una opción y pulsar **Mostrar** o
**Reproducir**. Cada animación se repite hasta elegir otra acción. **Recorrer todas
las animaciones** activa la lista automática. El estado muestra la animación activa.
Las expresiones fijas conservan el parpadeo cuando corresponde.

También se pueden decir los nombres de animación: «pensar», «escuchar», «reír»,
«celebrar», «dormir», «jugar», etc. «Dormido» o «dormite» siguen eligiendo la pose
fija; «dormir» reproduce la secuencia. Para una expresión del catálogo usar el
prefijo «expresión», por ejemplo «expresión tímido» o «expresión cejas enojadas».
Para distinguir una secuencia se acepta «animación pensar», por ejemplo.

El [catálogo del avatar](catalogo-avatar.md) enumera todas las opciones y explica
la adaptación visual a la pantalla. El micrófono y el reconocimiento conservan
las mismas reglas de activación y confirmación; las frases desconocidas no actúan.
