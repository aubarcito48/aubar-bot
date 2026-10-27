# Panel de Aubar Bot

Aplicación de escritorio para seleccionar el puerto USB, conectar la placa y
consultar su expresión, modo y mirada. Requiere firmware con protocolo **v2**
(TK16 o posterior). La conexión y las consultas no cambian el modo del avatar.
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
- Internet solo para instalar las dependencias por primera vez.

Validado con Python 3.14.3 en Windows y la Waveshare ESP32-S3-LCD-1.47B.

## Abrir la herramienta

Desde PowerShell, en la raíz del repositorio:

```powershell
.\tools\start_control.ps1
```

El lanzador crea `.venv` si no existe, comprueba las dependencias y abre la
ventana. También descarga el modelo español de unos 39 MB la primera vez,
verificando su SHA256. No instala paquetes globales de Python. Si Python no está en PATH,
se puede indicar su ejecutable:

```powershell
.\tools\start_control.ps1 -PythonExecutable 'C:\ruta\a\python.exe'
```

También se puede preparar y ejecutar manualmente:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r pc\requirements.txt
.\.venv\Scripts\python.exe tools\install_voice_model.py
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

La captura se detiene al perder el foco de la ventana, minimizarla, cerrarla
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

Se ignoran mayúsculas, tildes y puntuación. Se acepta «Kirby» al principio
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

En TK19 las acciones **solo se muestran**: el envío al ESP32 corresponde a TK20.
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
