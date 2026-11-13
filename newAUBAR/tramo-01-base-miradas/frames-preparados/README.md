# Cuadros preparados de AUBAR

Se procesaron los dos videos aportados por Nahuel: 10 segundos y 240 cuadros a 24 fps por video. Los originales y las imágenes aportadas se conservan sin modificar.

## Dónde mirar primero

- `vertical/vista-previa.webp`: vista animada del video vertical sobre fondo oscuro.
- `horizontal/vista-previa.webp`: vista animada del video horizontal sobre fondo oscuro.
- `vertical/poses.jpg` y `horizontal/poses.jpg`: selección de poses en una imagen.
- `revision-con-fondo.jpg` dentro de cada carpeta: cuadros cada 0,25 segundos, con índice y tiempo.
- `revision-sin-fondo.jpg`: revisión del recorte sobre un fondo oscuro.

Las vistas animadas se abren en un navegador compatible con WebP animado. Son vistas de revisión, no archivos que el firmware actual pueda reproducir directamente.

## Qué contiene cada carpeta

| Archivo o carpeta | Contenido |
| --- | --- |
| `con-fondo/000.webp` a `239.webp` | Todos los cuadros recortados y redimensionados, con su fondo original, en WebP sin pérdida adicional. |
| `sin-fondo/000.webp` a `239.webp` | Los mismos cuadros con máscara de transparencia. |
| `atlas.webp` | Hoja de 8 columnas con los 240 cuadros, en orden, a 24 fps. |
| `neutral.webp` | Cuadro inicial del propio video. |
| `vista-previa.webp` | Animación para revisar la secuencia completa sobre fondo oscuro. |
| `poses.jpg` | Ocho cuadros de referencia seleccionados. |

`manifest.json` registra el origen, recorte, tamaño, orden, tiempos y tramos de cada movimiento. Las direcciones izquierda/derecha se refieren a la pantalla desde el punto de vista del espectador.

`poses-estaticas.webp` reúne las seis imágenes WebP transparentes aportadas: boca abierta, boca semiabierta, dormido, frente, mira-pc y pensando. Sus nombres y posiciones están en `manifest.json`. Se mantienen separadas de los cuadros del video: no se supone que coincidan exactamente en escala y rostro.

## Movimientos disponibles

En ambos videos hay reposo, giros hacia derecha e izquierda, miradas arriba y abajo, regresos y parpadeos. El video vertical además termina con una sonrisa más marcada. Los rangos son cortes editoriales de estos videos, no equivalencias definitivas de las 23 animaciones del avatar geométrico.

Se mantienen los dos videos separados. El horizontal usa cuadros de 320 × 320 y el vertical de 180 × 320, conservando proporciones. El atlas horizontal mide 2560 × 9600 y el vertical 1440 × 9600. No hay una transición garantizada entre tomas generadas por separado.

## Fondo y límites del recorte

El fondo de estos videos es una habitación con tonos claros y grises. El método de eliminar blanco conectado al borde usado en clima no funciona directamente: quedan muebles y paredes visibles.

Aquí se usa una máscara local por silueta: detecta el personaje dentro de una región definida para cada cámara y conserva la computadora y la franja inferior del escritorio mediante polígonos fijos. No se usa una API ni un modelo de segmentación. Los polígonos y umbrales están en `../aubar-assets.json`.

La transparencia es una primera preparación utilizable para revisar; el contorno del cabello, los brazos y la computadora puede requerir retoques. La franja del escritorio se conserva deliberadamente, al igual que en las imágenes sin fondo aportadas. Las copias con fondo permiten cambiar la máscara sin extraer otra vez el video.

No se generaron movimientos nuevos ni boca animada. Las bocas disponibles son imágenes estáticas. Estos recursos ya se incorporaron al nuevo firmware del ESP32; ver [implementación y comprobaciones en placa](../guia/FIRMWARE_AVATAR.md).

## Reproducir la preparación

Desde la raíz de `botbar`, con Python, Pillow, NumPy, SciPy y FFmpeg disponibles:

```powershell
python tools/prepare_aubar_frames.py --ffmpeg RUTA/ffmpeg.exe
```

Para ajustar las máscaras o los rangos sin decodificar otra vez:

```powershell
python tools/prepare_aubar_frames.py --ffmpeg RUTA/ffmpeg.exe --reuse-frames
```

No usar `--reuse-frames` si cambia el video, el recorte o el tamaño. La ejecución es explícita y secuencial, con FFmpeg limitado a un hilo. No se ejecuta al abrir el panel ni al compilar. Los PNG de trabajo quedan en `../revision-video/horizontal` y `../revision-video/vertical`.
