# Tramo 02: emociones

Video revisado: `gemini_generated_video_dda76b2e.mp4`, 240 cuadros a 24 fps.
Se prepararon todos los cuadros con la misma máscara vertical del avatar base.
La imagen de revisión está en `../frames-preparados/emociones/revision-sin-fondo.jpg`.

Cada orden reproduce su entrada natural y sostiene el gesto elegido. No recorre
las otras emociones del video para llegar al gesto solicitado.

| Orden del catálogo | Cuadros originales | Gesto final |
| --- | --- | --- |
| `suspicious` | 16–40 | Sospecha |
| `confused` | 64–88 | Confusión |
| `angry` | 96–112 | Enojo |
| `sad` | 136–160 | Tristeza |
| `scared` | 168–192 | Miedo |
| `shy` | 208–222 | Timidez |

Las expresiones de enojo, sospecha y timidez también utilizan estas rutas.
El habla conserva prioridad mientras suena Onyx y luego vuelve al gesto.
Las miradas explícitas conservan su comportamiento anterior.

## Memoria y reproducción

El banco ahora usa compresión zlib de cuadros completos y diferencias XOR sin
pérdida. Cada grupo tiene cuadros completos al menos cada 12 cuadros; una
búsqueda requiere reconstruir como máximo 11 diferencias. La reproducción
continua reutiliza el cuadro anterior y puede invertir la diferencia para
retroceder. Se conservan resolución, colores de la paleta y velocidad de origen.

Esta versión tiene 906 cuadros y un banco de 7.602.385 bytes, dentro de la
misma partición de 12 MiB. No se cambió la distribución de flash.

## Regenerar

```powershell
python tools/prepare_speech_frames.py --stage emotions --ffmpeg RUTA/ffmpeg.exe
python tools/generate_portrait_firmware.py
```

Compilar con `--clean` como indica el README y cargar el firmware. Para comprobar
poses, movimiento, lectura del banco y habla con el panel cerrado:

```powershell
.venv/Scripts/python.exe tools/test_portrait_usb.py --port COM3
```
