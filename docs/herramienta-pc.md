# Panel de conexión de Aubar Bot

Aplicación de escritorio para seleccionar el puerto USB, conectar la placa y
consultar su expresión, modo y mirada. Requiere firmware con protocolo **v2**
(TK16 o posterior). La conexión y las consultas no cambian el modo del avatar.

## Requisitos

- Windows con [Python 3.11 o superior](https://www.python.org/downloads/).
  La instalación oficial debe incluir Tcl/Tk y tkinter; se recomienda instalar
  también el lanzador `py`.
- Placa conectada con cable USB de datos y firmware cargado.
- [pySerial 3.5](https://pyserial.readthedocs.io/en/latest/), instalado por el
  lanzador en el entorno local `.venv`.
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

El panel actual consulta el dispositivo; la captura de micrófono y el control
por voz se incorporarán en las siguientes tareas. La interfaz trabaja en el
hilo de Tk y el USB en un trabajador separado, con tiempos de espera limitados.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests\pc -v
```

Las pruebas usan puertos simulados y una ventana Tk temporal, sin necesitar
el ESP32. La validación de conexión con la placa física se realiza por separado.

Los errores inesperados se registran en `pc/aubar-control.log`, excluido de Git.
El código de la aplicación está en `pc/aubar_control/`; el protocolo está en
[protocolo-usb.md](protocolo-usb.md).
