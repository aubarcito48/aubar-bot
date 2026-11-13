# Tramo 03: gestos restantes

Video revisado: `gemini_generated_video_fec8b636.mp4`, 240 cuadros a 24 fps.
Se conserva completo en la preparación y en el banco del ESP32.
El banco conjunto tiene 1146 cuadros y ocupa 11.009.820 bytes.
Incluye diferencias inversas en los cuadros completos para que los bucles de
risa, alegría y habla también retrocedan directamente, sin reconstruir cadenas.
Se conserva la partición actual de 12 MiB.
El firmware compilado ocupa 11.368.457 bytes de los 12.582.912 disponibles.

| Orden | Cuadros originales | Reproducción |
| --- | --- | --- |
| `bored` | 20–44 | Entrada y sostén con ojos pesados; se distingue de dormir. |
| `surprised` | 56–88 | Entrada y sostén de sorpresa. |
| `proud` | 100–120 | Entrada y sostén de sonrisa satisfecha. |
| `laughing` | 128–168 | Risa con boca abierta y ojos cerrados, ida y vuelta continua. |
| `excited` | 172–196 | Sonrisa abierta y animada, ida y vuelta. |
| `happy` | 188–204 | Entrada y sostén de alegría. |
| `playful` | 204–224 | Sonrisa con inclinación, ida y vuelta. |
| `celebrate` | 172–208 | Variante más amplia de la secuencia alegre, ida y vuelta. |

Las expresiones de alegría, sorpresa y juego también usan este material.
Entusiasmo, alegría y celebración comparten parte del mismo gesto; el video
no ofrece tres actuaciones completamente independientes. No se crean gestos
con las manos que no existan en la fuente.

La secuencia de habla del tramo 04 conserva prioridad mientras suena la voz.
Luego se recupera el gesto seleccionado. El tramo 02 conserva sus rutas.

## Preparar y probar

```powershell
python tools/prepare_speech_frames.py --stage gestures --ffmpeg RUTA/ffmpeg.exe
python tools/generate_portrait_firmware.py
```

Compilar con `--clean` y cargar según el README principal. La prueba física
verifica ambos tramos, el habla, las miradas, la decodificación y el movimiento:

```powershell
.venv/Scripts/python.exe tools/test_portrait_usb.py --port COM3
```

Revisión visual: `../frames-preparados/gestos/revision-sin-fondo.jpg`.

## Verificación en placa

- Firmware cargado por USB y verificado por hash en el ESP32-S3 de 16 MB.
- 1146 cuadros reconstruidos localmente; diferencias inversas verificadas.
- Emociones del tramo 02 y gestos del tramo 03 comprobados por checksum en LCD.
- Bucles de risa, entusiasmo, juego y celebración comprobados durante 2,2 s
  cada uno, incluyendo avance y retroceso, con al menos 46 cuadros dibujados.
- Habla, renovación de señal, detención y caducidad de seguridad comprobadas.
- Cero errores de descompresión y 8 MiB de PSRAM detectados.
- Catálogo USB: 51 opciones y 153 combinaciones comprobadas, con persistencia
  de miradas durante las animaciones y regreso al modo automático.
