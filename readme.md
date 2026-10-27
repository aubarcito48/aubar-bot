# Aubar Bot

Bot de escritorio en desarrollo, con un avatar de Kirby en una pantalla
Waveshare ESP32-S3-LCD-1.47B. Reproduce 28 expresiones y 23 animaciones,
con parpadeo, miradas y control por voz desde el micrófono de la PC.

El firmware funciona de forma autónoma después de cargarlo: basta con alimentar
la placa por USB. Para controlarlo por voz se utiliza el panel de la PC;
también permite conversar con Groq, escuchar las respuestas con la voz local
Dora y abrir, buscar y reproducir videos de YouTube en el navegador.

## Usar el panel de PC

Con Python 3.11 o superior instalado y el firmware cargado, ejecutar desde
PowerShell en la raíz del proyecto:

```powershell
.\tools\start_control.ps1
```

El lanzador prepara el entorno, las dependencias y los modelos de voz. La primera
ejecución necesita internet para descargarlos; el modelo completo de español
ocupa unos 1,4 GB. Esperar **Reconocimiento listo** antes de hablar: la carga
inicial del modelo puede tardar unos 25 segundos.

En **Dispositivo**, conectar el puerto del ESP32. En **Micrófono**, elegir la
entrada y activar la escucha automática, o mantener pulsado el botón para hablar.
Los dos modos aceptan comandos y preguntas **sin decir «Aubar»**. El nombre
es opcional. **Probar micrófono** permite escuchar una muestra de la entrada
sin ejecutar comandos.

Para conversar, copiar `.env.example` a `.env` si todavía no existe ese archivo,
completar `GROQ_API_KEY` y recargar la configuración en **IA**. La clave permanece
en el archivo local, excluido de Git. Groq y YouTube necesitan internet; el
reconocimiento, la voz Dora y los comandos del avatar funcionan localmente.

## Conversación y YouTube

Se puede decir **«contame algo interesante»** o **«cómo estás»** directamente.
Las respuestas conservan el contexto de la conversación, se leen con Dora si
**Activar voz** está marcado y acompañan al avatar con una expresión o animación.
**Nueva conversación** borra el contexto; **Cancelar** interrumpe el turno pendiente.
La escucha se pausa mientras Aubar responde y vuelve si la automática sigue activa.

| Acción | Ejemplo de voz |
| --- | --- |
| Abrir YouTube | «abrí YouTube» |
| Mostrar resultados de búsqueda | «buscá videos de gatos en YouTube» |
| Buscar y abrir el primer video para reproducirlo | «poné videos de gatos en YouTube» |
| Pedir la reproducción con otro verbo | «reproducí música relajante en YouTube» |
| Abrir, buscar y reproducir con una sola frase | «abrí YouTube y buscá videos de gatos y reproducilo» |

Las acciones de YouTube se ejecutan en el navegador predeterminado de la PC y
no necesitan Groq. «Buscá» muestra los resultados; «poné» y «reproducí» abren el
primer video con reproducción automática, sujeta a los controles del navegador
y de YouTube.

## Comandos de voz aislados

Para usar la voz, abrir el [panel de PC](#usar-el-panel-de-pc), conectar el
ESP32 y seleccionar el micrófono. En **escucha automática**, activar la casilla,
esperar la calibración y decir **el comando directamente**. Una pausa de
**0,8 segundos** termina la frase. En captura manual, esperar **Escuchando**,
hablar y soltar el botón para terminar. Ninguno de los modos exige «Aubar».

Se ignoran mayúsculas, tildes y puntuación. El panel muestra lo reconocido y
la confirmación del ESP32. Los siguientes comandos seleccionan una sola acción.

### Expresiones fijas — 28

| Expresión | Comando de voz |
| --- | --- |
| Neutral | «neutral» |
| Contento | «contento» |
| Sorprendido | «sorprendido» |
| Dormido | «dormido» |
| Enojado | «enojado» |
| Mirada lateral arriba | «expresión mirada lateral arriba» |
| Mirada abajo | «expresión mirada abajo» |
| Escéptico derecha | «expresión escéptico derecha» |
| Atento pequeño | «expresión atento pequeño» |
| Mirada amplia abajo | «expresión mirada amplia abajo» |
| Sorpresa izquierda | «expresión sorpresa izquierda» |
| Somnoliento | «expresión somnoliento» |
| Curioso izquierda | «expresión curioso izquierda» |
| Asimétrico abajo derecha | «expresión asimétrico abajo derecha» |
| Atento izquierda | «expresión atento izquierda» |
| Alegre abajo derecha | «expresión alegre abajo derecha» |
| Escéptico izquierda | «expresión escéptico izquierda» |
| Mirada derecha | «expresión mirada derecha» |
| Enojado izquierda | «expresión enojado izquierda» |
| Juguetón derecha | «expresión juguetón derecha» |
| Asimétrico arriba izquierda | «expresión asimétrico arriba izquierda» |
| Mirada suave abajo | «expresión mirada suave abajo» |
| Mirada amplia abajo izquierda | «expresión mirada amplia abajo izquierda» |
| Adormilado | «expresión adormilado» |
| Sospechoso derecha | «expresión sospechoso derecha» |
| Tímido | «expresión tímido» |
| Cejas enojadas | «expresión cejas enojadas» |
| Inquieto izquierda | «expresión inquieto izquierda» |

También se aceptan **«dormite»**, **«duerme»** y **«a dormir»**
para la expresión dormida. Para contento, usar **«contento»**.
El prefijo «expresión» también se puede usar con las cinco expresiones básicas.

### Animaciones en bucle — 23

| Animación | Comando de voz |
| --- | --- |
| Dormir | «dormir» |
| Despertar | «despertar» |
| Reposo | «reposo» |
| Escuchar | «escuchar» |
| Pensar | «pensar» |
| Buscar | «buscar» |
| Trabajar | «trabajar» |
| Entusiasmarse | «entusiasmarse» |
| Aburrirse | «aburrirse» |
| Sospechar | «sospechar» |
| Enojarse | «enojarse» |
| Adormecerse | «adormecerse» |
| Alegría | «alegría» |
| Curiosear | «curiosear» |
| Confundirse | «confundirse» |
| Sorprenderse | «sorprenderse» |
| Orgullo | «orgullo» |
| Timidez | «timidez» |
| Tristeza | «tristeza» |
| Reír | «reír» |
| Asustarse | «asustarse» |
| Jugar | «jugar» |
| Celebrar | «celebrar» |

También se acepta «animación» antes del nombre: **«animación celebrar»**.
**«dormido»** elige una pose fija; **«dormir»** reproduce la
animación de sueño.

### Miradas y modos

| Acción | Comando de voz |
| --- | --- |
| Mirar a la izquierda | «izquierda» o «mirá a la izquierda» |
| Mirar al centro | «centro» o «mirá al centro» |
| Mirar a la derecha | «derecha» o «mirá a la derecha» |
| Recorrer automáticamente todas las animaciones | «modo automático» |
| Detener la secuencia en la expresión actual | «modo manual» |

Una mirada aislada conserva la animación que se esté reproduciendo.
El modo automático restaura las orientaciones originales del catálogo.

## Comandos de voz combinados

Combinar **una expresión o una animación** con **izquierda, centro o derecha**.
Hay **153 combinaciones**: 28 expresiones × 3 miradas y 23 animaciones × 3 miradas.

Ejemplos: **«enojado derecha»**, **«celebrar izquierda»** y
**«pensar centro»**. También se acepta **«enojado mirando a la
derecha»** o **«celebrar y izquierda»**.

La combinación se aplica en una sola orden y la mirada se mantiene durante
los pasos de la animación y las selecciones siguientes. **«centro»**
la centra; **«modo automático»** recupera las orientaciones originales.
Los ojos dormidos siguen cerrados y también pueden orientarse.

Los combinados requieren el firmware con **protocolo USB v4**. Para los nombres
de expresiones que ya incluyen una dirección se usa «expresión» y «mirando»,
como en la lista, para distinguir el nombre de la pose de la mirada solicitada.

<details>
<summary>Lista completa: expresiones con mirada — 84 combinaciones</summary>

| Expresión | Comandos combinados |
| --- | --- |
| Neutral | «neutral izquierda»<br>«neutral centro»<br>«neutral derecha» |
| Contento | «contento izquierda»<br>«contento centro»<br>«contento derecha» |
| Sorprendido | «sorprendido izquierda»<br>«sorprendido centro»<br>«sorprendido derecha» |
| Dormido | «dormido izquierda»<br>«dormido centro»<br>«dormido derecha» |
| Enojado | «enojado izquierda»<br>«enojado centro»<br>«enojado derecha» |
| Mirada lateral arriba | «expresión mirada lateral arriba mirando a la izquierda»<br>«expresión mirada lateral arriba mirando al centro»<br>«expresión mirada lateral arriba mirando a la derecha» |
| Mirada abajo | «expresión mirada abajo mirando a la izquierda»<br>«expresión mirada abajo mirando al centro»<br>«expresión mirada abajo mirando a la derecha» |
| Escéptico derecha | «expresión escéptico derecha mirando a la izquierda»<br>«expresión escéptico derecha mirando al centro»<br>«expresión escéptico derecha mirando a la derecha» |
| Atento pequeño | «expresión atento pequeño mirando a la izquierda»<br>«expresión atento pequeño mirando al centro»<br>«expresión atento pequeño mirando a la derecha» |
| Mirada amplia abajo | «expresión mirada amplia abajo mirando a la izquierda»<br>«expresión mirada amplia abajo mirando al centro»<br>«expresión mirada amplia abajo mirando a la derecha» |
| Sorpresa izquierda | «expresión sorpresa izquierda mirando a la izquierda»<br>«expresión sorpresa izquierda mirando al centro»<br>«expresión sorpresa izquierda mirando a la derecha» |
| Somnoliento | «expresión somnoliento mirando a la izquierda»<br>«expresión somnoliento mirando al centro»<br>«expresión somnoliento mirando a la derecha» |
| Curioso izquierda | «expresión curioso izquierda mirando a la izquierda»<br>«expresión curioso izquierda mirando al centro»<br>«expresión curioso izquierda mirando a la derecha» |
| Asimétrico abajo derecha | «expresión asimétrico abajo derecha mirando a la izquierda»<br>«expresión asimétrico abajo derecha mirando al centro»<br>«expresión asimétrico abajo derecha mirando a la derecha» |
| Atento izquierda | «expresión atento izquierda mirando a la izquierda»<br>«expresión atento izquierda mirando al centro»<br>«expresión atento izquierda mirando a la derecha» |
| Alegre abajo derecha | «expresión alegre abajo derecha mirando a la izquierda»<br>«expresión alegre abajo derecha mirando al centro»<br>«expresión alegre abajo derecha mirando a la derecha» |
| Escéptico izquierda | «expresión escéptico izquierda mirando a la izquierda»<br>«expresión escéptico izquierda mirando al centro»<br>«expresión escéptico izquierda mirando a la derecha» |
| Mirada derecha | «expresión mirada derecha mirando a la izquierda»<br>«expresión mirada derecha mirando al centro»<br>«expresión mirada derecha mirando a la derecha» |
| Enojado izquierda | «expresión enojado izquierda mirando a la izquierda»<br>«expresión enojado izquierda mirando al centro»<br>«expresión enojado izquierda mirando a la derecha» |
| Juguetón derecha | «expresión juguetón derecha mirando a la izquierda»<br>«expresión juguetón derecha mirando al centro»<br>«expresión juguetón derecha mirando a la derecha» |
| Asimétrico arriba izquierda | «expresión asimétrico arriba izquierda mirando a la izquierda»<br>«expresión asimétrico arriba izquierda mirando al centro»<br>«expresión asimétrico arriba izquierda mirando a la derecha» |
| Mirada suave abajo | «expresión mirada suave abajo mirando a la izquierda»<br>«expresión mirada suave abajo mirando al centro»<br>«expresión mirada suave abajo mirando a la derecha» |
| Mirada amplia abajo izquierda | «expresión mirada amplia abajo izquierda mirando a la izquierda»<br>«expresión mirada amplia abajo izquierda mirando al centro»<br>«expresión mirada amplia abajo izquierda mirando a la derecha» |
| Adormilado | «expresión adormilado mirando a la izquierda»<br>«expresión adormilado mirando al centro»<br>«expresión adormilado mirando a la derecha» |
| Sospechoso derecha | «expresión sospechoso derecha mirando a la izquierda»<br>«expresión sospechoso derecha mirando al centro»<br>«expresión sospechoso derecha mirando a la derecha» |
| Tímido | «expresión tímido mirando a la izquierda»<br>«expresión tímido mirando al centro»<br>«expresión tímido mirando a la derecha» |
| Cejas enojadas | «expresión cejas enojadas mirando a la izquierda»<br>«expresión cejas enojadas mirando al centro»<br>«expresión cejas enojadas mirando a la derecha» |
| Inquieto izquierda | «expresión inquieto izquierda mirando a la izquierda»<br>«expresión inquieto izquierda mirando al centro»<br>«expresión inquieto izquierda mirando a la derecha» |

</details>

<details>
<summary>Lista completa: animaciones con mirada — 69 combinaciones</summary>

| Animación | Comandos combinados |
| --- | --- |
| Dormir | «dormir izquierda»<br>«dormir centro»<br>«dormir derecha» |
| Despertar | «despertar izquierda»<br>«despertar centro»<br>«despertar derecha» |
| Reposo | «reposo izquierda»<br>«reposo centro»<br>«reposo derecha» |
| Escuchar | «escuchar izquierda»<br>«escuchar centro»<br>«escuchar derecha» |
| Pensar | «pensar izquierda»<br>«pensar centro»<br>«pensar derecha» |
| Buscar | «buscar izquierda»<br>«buscar centro»<br>«buscar derecha» |
| Trabajar | «trabajar izquierda»<br>«trabajar centro»<br>«trabajar derecha» |
| Entusiasmarse | «entusiasmarse izquierda»<br>«entusiasmarse centro»<br>«entusiasmarse derecha» |
| Aburrirse | «aburrirse izquierda»<br>«aburrirse centro»<br>«aburrirse derecha» |
| Sospechar | «sospechar izquierda»<br>«sospechar centro»<br>«sospechar derecha» |
| Enojarse | «enojarse izquierda»<br>«enojarse centro»<br>«enojarse derecha» |
| Adormecerse | «adormecerse izquierda»<br>«adormecerse centro»<br>«adormecerse derecha» |
| Alegría | «alegría izquierda»<br>«alegría centro»<br>«alegría derecha» |
| Curiosear | «curiosear izquierda»<br>«curiosear centro»<br>«curiosear derecha» |
| Confundirse | «confundirse izquierda»<br>«confundirse centro»<br>«confundirse derecha» |
| Sorprenderse | «sorprenderse izquierda»<br>«sorprenderse centro»<br>«sorprenderse derecha» |
| Orgullo | «orgullo izquierda»<br>«orgullo centro»<br>«orgullo derecha» |
| Timidez | «timidez izquierda»<br>«timidez centro»<br>«timidez derecha» |
| Tristeza | «tristeza izquierda»<br>«tristeza centro»<br>«tristeza derecha» |
| Reír | «reír izquierda»<br>«reír centro»<br>«reír derecha» |
| Asustarse | «asustarse izquierda»<br>«asustarse centro»<br>«asustarse derecha» |
| Jugar | «jugar izquierda»<br>«jugar centro»<br>«jugar derecha» |
| Celebrar | «celebrar izquierda»<br>«celebrar centro»<br>«celebrar derecha» |

</details>

El catálogo también está disponible en la pestaña **Catálogo** del panel.

## Requisitos

Esta guía está orientada a Windows y al modelo de placa indicado.

### Hardware

| Elemento | Detalle |
| --- | --- |
| **Waveshare ESP32-S3-LCD-1.47B** | ESP32-S3, pantalla ST7789 de 172 × 320 píxeles, 16 MB de flash y 8 MB de PSRAM |
| **Cable USB-C de datos** | Para alimentar la placa y transferir el programa |
| **PC con Windows y puerto USB** | Para instalar las herramientas, compilar y cargar el firmware |

Información de la placa: [documentación oficial de Waveshare](https://docs.waveshare.com/ESP32-S3-LCD-1.47B)
y [página del producto](https://www.waveshare.com/esp32-s3-lcd-1.47b.htm).

### Software

| Herramienta | Versión / uso | Enlace |
| --- | --- | --- |
| **Arduino IDE** | Versión 2; editor, compilación y carga por USB | [Descarga oficial](https://www.arduino.cc/en/software/) |
| **esp32 by Espressif Systems** | **3.3.8**, versión utilizada para validar este proyecto; incluye el compilador, Arduino y SPI para ESP32 | [Instalación oficial](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html) |
| **Arduino CLI** — opcional | Permite compilar y cargar desde la terminal | [Documentación oficial](https://docs.arduino.cc/arduino-cli/) |
| **Python 3.11 o superior** | Para el panel de PC y los comandos de voz; también permite regenerar los datos del avatar | [Descarga oficial](https://www.python.org/downloads/) |

Se necesita internet para descargar las herramientas y el paquete ESP32.
El firmware actual no requiere conexión a internet, microSD, micrófono,
parlantes, credenciales ni bibliotecas adicionales del gestor de bibliotecas.

## Avatar y recursos de origen

El personaje se creó y exportó con [Bible Strong Avatar Lab](https://avatars.bible-strong.app/).
La exportación original está incluida en [avatar-original/](avatar-original/),
junto con su demo web e instrucciones.

Esta versión adapta las formas, dimensiones, colores y poses del personaje
a una proyección ortográfica para el ESP32. Las 28 expresiones y las 23
animaciones de la exportación están incorporadas, con un reproductor local
que conserva sus pasos y tiempos. La adaptación no ejecuta el motor web original.

Los datos necesarios ya están incluidos en `avatar_data.h`. Para compilar este
proyecto no hace falta abrir Avatar Lab, volver a exportar el personaje ni
instalar React, Angular, Node.js o npm.

## Instalación y carga

### 1. Obtener el proyecto

Descargar el repositorio desde **Code > Download ZIP** en GitHub y extraerlo
en una carpeta local. También se puede clonar con Git.

Abrir los archivos desde la carpeta extraída, no desde el ZIP.

### 2. Instalar Arduino IDE y el soporte ESP32

1. Descargar e instalar [Arduino IDE 2 para Windows](https://www.arduino.cc/en/software/).
2. Abrir **Archivo > Preferencias**.
3. Agregar la siguiente dirección en **URLs adicionales de gestor de placas**,
   conservando las direcciones existentes:

   ```text
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```

4. Abrir el **Gestor de placas**, buscar **esp32 by Espressif Systems** e
   instalar la versión **3.3.8**.

El paquete instala las herramientas de compilación y carga necesarias.
No hay que instalar bibliotecas adicionales para esta versión.

### 3. Abrir y configurar el firmware

Abrir [firmware/KirbyPantalla/KirbyPantalla.ino](firmware/KirbyPantalla/KirbyPantalla.ino)
en Arduino IDE. Mantener juntos todos los archivos de la carpeta
`KirbyPantalla` y conservar su nombre.

En **Herramientas > Placa > esp32**, seleccionar **ESP32S3 Dev Module**.
Configurar:

| Opción | Valor |
| --- | --- |
| Flash Size | 16MB (128Mb) |
| PSRAM | OPI PSRAM |
| USB CDC On Boot | Enabled |
| USB Mode | Hardware CDC and JTAG |
| Partition Scheme | Default (la predeterminada de esta placa) |

Las demás opciones pueden quedar por defecto. Si estas opciones no aparecen,
revisar la placa seleccionada y la versión del paquete ESP32.

### 4. Conectar y cargar

1. Conectar la placa a la PC con el cable USB-C de datos.
2. En **Herramientas > Puerto**, seleccionar el puerto que aparece al conectarla.
   El número `COM` depende de la PC.
3. Pulsar **Subir** y esperar a que termine la carga.
4. Si no arranca automáticamente, pulsar **RESET**.
5. Comprobar que el personaje aparece centrado y parpadea cada pocos segundos.

La carga reemplaza el programa anterior de la placa. No hace falta borrar
la memoria previamente. Una vez cargado, se puede cerrar Arduino IDE:
el avatar vuelve a arrancar cada vez que la placa recibe alimentación.

### Solución de problemas

| Problema | Qué revisar |
| --- | --- |
| No aparece un puerto al conectar | Usar un cable de datos y probar otro puerto USB |
| No entra en modo de carga | Mantener **BOOT**, pulsar y soltar **RESET**, y después soltar **BOOT**; volver a seleccionar el puerto |
| Puerto ocupado | Cerrar el monitor serie u otros programas que usen ese puerto |
| La compilación no encuentra los archivos del proyecto | Abrir el `.ino` desde la carpeta extraída y mantener juntos todos los archivos de `KirbyPantalla` |
| Opciones de placa diferentes | Seleccionar **ESP32S3 Dev Module** del paquete **esp32 by Espressif Systems 3.3.8** |

## Carga desde la terminal — opcional

Requiere Arduino CLI y el paquete ESP32 instalado. La instalación con Arduino IDE
de la sección anterior es suficiente si la CLI utiliza su misma configuración.

Desde la raíz del proyecto, con `arduino-cli` disponible en PATH:

```powershell
arduino-cli board list
arduino-cli compile --fqbn "esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=opi" --upload --port COM3 firmware/KirbyPantalla
```

Reemplazar `COM3` por el puerto detectado. Para compilar sin cargar, quitar
`--upload --port COM3`.

En una instalación de Arduino IDE para el usuario de Windows, la CLI incluida
puede ejecutarse desde PowerShell de esta manera:

```powershell
$kirbyCli = "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
$kirbyConfig = "$env:USERPROFILE\.arduinoIDE\arduino-cli.yaml"
& $kirbyCli --config-file $kirbyConfig board list
& $kirbyCli --config-file $kirbyConfig compile --fqbn "esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=opi" --upload --port COM3 firmware/KirbyPantalla
```

La ubicación de la CLI puede variar según la instalación. Usar Arduino IDE
es la alternativa si estas rutas no existen.

## Estructura del proyecto

```text
firmware/KirbyPantalla/
  KirbyPantalla.ino       Inicio y secuencia de parpadeo
  Display_ST7789.cpp      Controlador de la pantalla
  Display_ST7789.h        Pines y configuración de la pantalla
  avatar_data.h          Datos del avatar listos para compilar
  avatar_render.h        Dibujo del personaje
avatar-original/         Exportación del avatar y demo web
pc/aubar_control/        Panel, micrófono, voz, IA y control de YouTube
tools/                   Lanzador, instaladores y generador del avatar
tests/pc/                Pruebas automáticas del panel y sus componentes
docs/images/             Imágenes del prototipo
.env.example             Plantilla de configuración local de Groq
.gitignore               Exclusiones de Git
readme.md                Requisitos e instrucciones del proyecto
```

Los archivos de `firmware/KirbyPantalla/` contienen lo necesario para
compilar y cargar esta versión. Los archivos compilados se generan localmente.

La carpeta `referencias/`, excluida de Git, contiene los ejemplos completos
descargados de Waveshare. El controlador usado está incluido en
`firmware/KirbyPantalla/`; descargar esos ejemplos es opcional.
Las cachés, los temporales y las dependencias locales también se excluyen de Git.

## Modificar los datos del avatar — opcional

Para regenerar `avatar_data.h` desde
`avatar-original/kirby.avatar.json`, instalar Python 3 y ejecutar desde
la raíz del proyecto:

```powershell
python tools/generate_avatar_data.py
```

El generador usa la biblioteca estándar de Python. Después de regenerar los
datos, compilar y cargar nuevamente el firmware. El generador adapta la
geometría, las 28 expresiones y los pasos de las 23 animaciones para el reproductor
local; no convierte el motor de animaciones web.

## Imágenes del prototipo

<img src="docs/images/kirby-ojos-semicerrados-ilustracion.png" alt="Ilustración editada con IA: ojos a medio cerrar" width="240"><img src="docs/images/kirby-ojos-cerrados-ilustracion.png" alt="Ilustración editada con IA: ojos cerrados" width="240"><img src="docs/images/kirby-pantalla.png" alt="Fotografía del avatar en la pantalla de la Waveshare" width="240">


## Validación

Versión compilada con **esp32 by Espressif Systems 3.3.8** y cargada por USB
en una **Waveshare ESP32-S3-LCD-1.47B**, el **26 de octubre de 2026**.
La herramienta verificó los datos escritos y se confirmó visualmente
que el avatar aparecía en la pantalla.

El panel de PC pasó **217 pruebas automáticas** y la comprobación de dependencias
con `pip check`. Se probó con Vosk, Groq, Dora, navegador y ESP32 reales, y se
confirmó el funcionamiento con micrófono y parlantes el **27 de octubre de 2026**.

## Créditos y documentación

- Avatar: [Bible Strong Avatar Lab](https://avatars.bible-strong.app/).
- Hardware: [Waveshare ESP32-S3-LCD-1.47B](https://docs.waveshare.com/ESP32-S3-LCD-1.47B).
- Configuración y ejemplos: [guía de Arduino de Waveshare](https://docs.waveshare.com/ESP32-S3-LCD-1.47B/Arduino).
- Controlador de pantalla: adaptado del ejemplo **LCD_Image** del
  [paquete oficial de ejemplos de Waveshare](https://files.waveshare.com/wiki/ESP32-S3-LCD-1.47B/ESP32-S3-LCD-1.47B-Demo.zip).
  Se ajustó SPI a 40 MHz y se eliminó un buffer de lectura innecesario.
- Entorno: [Arduino](https://www.arduino.cc/en/software/) y
  [Arduino ESP32 de Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/).
