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
- Micrófono habilitado en Windows para aplicaciones de escritorio.
- Internet solo para instalar las dependencias por primera vez.

Validado con Python 3.14.3 en Windows y la Waveshare ESP32-S3-LCD-1.47B.

## Abrir la herramienta

Desde PowerShell, en la raíz del repositorio:

```powershell
.\tools\start_control.ps1
```

El lanzador crea `.venv` si no existe, comprueba las dependencias y abre la
ventana. No instala paquetes globales de Python. Si Python no está en PATH,
se puede indicar su ejecutable:

```powershell
.\tools\start_control.ps1 -PythonExecutable 'C:\ruta\a\python.exe'
```

También se puede preparar y ejecutar manualmente:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r pc\requirements.txt
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
4. Durante la captura se muestra **Escuchando**, un nivel de entrada y la duración.
5. Soltar el botón para finalizar. La indicación cambia a **Micrófono apagado**
   y muestra la duración capturada. Las capturas menores de 0,15 s se descartan.

La captura se detiene al perder el foco de la ventana, minimizarla, cerrarla
o alcanzar 10 segundos. Al soltar el botón se rechazan inmediatamente nuevas
muestras, incluso si la apertura del dispositivo todavía está pendiente.

El audio queda en memoria y se reemplaza en la próxima captura; no se guarda
automáticamente ni se envía a servicios externos o al ESP32. TK19 incorporará
el reconocimiento. Se captura PCM mono de 16 bits, preferentemente a 16 kHz;
si el dispositivo no admite esa frecuencia, se utiliza su frecuencia nativa
y se conserva ese dato junto con el audio.

Si no hay nivel, elegir otra entrada y comprobar que el micrófono no esté silenciado.
Si falla la apertura, revisar los permisos de **Micrófono** en Configuración de
Windows, habilitar el acceso para aplicaciones de escritorio y volver a buscar.
Un error del micrófono no desconecta el ESP32.

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
