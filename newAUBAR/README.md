# Recursos del avatar por tramos

Todo el material de creación del avatar se organiza dentro de `newAUBAR`.

| Tramo | Contenido | Estado |
| --- | --- | --- |
| [01 — Base y miradas](tramo-01-base-miradas/guia/GUIA_AVATAR.md) | Seis poses iniciales, dos videos, miradas, parpadeos, sonrisa y cuadros del avatar actual. | Integrado en el ESP32. |
| [02 — Emociones](tramo-02-emociones/guia/INTEGRACION.md) | Enojado, sospechoso, confundido, triste, asustado y tímido. | Integrado en el ESP32. |
| [03 — Gestos restantes](tramo-03-gestos-restantes/guia/INTEGRACION.md) | Aburrimiento, sorpresa, orgullo, risa y variantes alegres. | Integrado en el ESP32. |
| [04 — Habla](tramo-04-hablar/guia/HABLA.md) | Boca animada durante la reproducción de Onyx. | Integrado en el ESP32. |

Cada tramo tiene esta estructura:

```text
tramo-XX-nombre/
  animaciones-original/
    formato jfif/          Originales con fondo de Gemini
    formato webp/          Copias optimizadas con fondo
  animaciones-sin-fondo/
    formato png/           Fuentes sin fondo
    formato webp/          Copias para usar en la app
  videos/                  Videos originales descargados
  frames-preparados/       Cuadros y vistas preparadas
  revision-video/          Material de revisión y extracción temporal
  guia/                    Plan, instrucciones y revisión del tramo
```

Si Gemini entrega otro formato original, conservarlo sin convertir en `animaciones-original` o crear su subcarpeta de formato. No reemplazar ni mezclar los archivos de un tramo con los de otro.

Los archivos `.gitkeep` solo conservan las carpetas vacías en Git. Podés guardar tus archivos junto a ellos.

`nahue_pick.png` se conserva en esta raíz como referencia histórica del estilo anterior. La referencia vigente para generar las nuevas emociones es el frontal original del tramo 01.

`prepare_aubar_frames.py` prepara las miradas del tramo 01.
`prepare_speech_frames.py --stage emotions`, `--stage gestures` o `--stage speech`
prepara respectivamente los tramos 02, 03 y 04. El empaquetador incorpora los
cuatro tramos y conserva cuadros nativos a 24 fps con compresión sin pérdida.

Al iniciar otra tanda, crear una carpeta nueva con la misma estructura.
