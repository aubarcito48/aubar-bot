# Avatar nuevo en el ESP32

## Implementación

`firmware/KirbyPantalla/KirbyPantalla.ino` usa el nuevo `PortraitPlayer`. El
controlador, los comandos USB v4 y el catálogo del panel se mantienen. La voz,
el micrófono y YouTube siguen funcionando desde la PC; esta actualización cambia
el dibujo en la pantalla.

Se incluyen los 240 cuadros verticales, 240 horizontales y las seis poses
estáticas. Se adaptan a un lienzo de 172 × 320 sin deformar las proporciones,
componiendo la transparencia sobre el fondo oscuro. El video horizontal queda
centrado con márgenes porque su encuadre es más ancho.

El generador usa una paleta compartida de 256 colores sin tramado, convierte los
colores de salida a RGB565 y comprime cada cuadro por separado con zlib. La placa
usa el descompresor de su ROM y buffers en RAM/PSRAM. Los fundidos entre recursos
independientes duran 220 ms. Dentro de los videos se siguen los cuadros a 24 fps;
si el procesamiento tarda más que un intervalo, se avanza según el tiempo real.

El banco `portrait_assets.dat` ocupa 11.187.880 bytes y contiene 666 cuadros, incluyendo
180 del [tramo de habla](../../tramo-04-hablar/guia/HABLA.md).
`portrait_assets.S` lo incorpora al firmware sin generar millones de literales
C++. `portrait_asset_path.h` contiene la ruta local del banco; ejecutar el
generador si se mueve el proyecto.

El controlador ST7789 usa `RAMCTRL=0x00,0xE0`, con el bit ENDIAN desactivado.
Los buffers RGB565 ya se serializan MSB primero para SPI. La configuración
anterior `0xE8` invertía otra vez los bytes en la pantalla y producía colores
incorrectos (fondo rosado y tonos falsos en el rostro). La configuración se
ajustó después de revisar la fotografía enviada por Nahuel.

## Correspondencias actuales

| Acción | Material mostrado |
| --- | --- |
| Neutral / despertar | Imagen frontal. |
| Dormido / dormir / adormecerse / aburrirse / tristeza | Imagen dormido; algunas son equivalencias temporales. |
| Pensar / confusión / sospecha / enojo | Imagen pensando como equivalencia temporal. |
| Trabajar / mirada suave abajo | Imagen mirando a la PC. |
| Sorpresa / miedo | Imagen de boca abierta como equivalencia temporal. |
| Reír | Imagen de boca semiabierta, sin sincronización con voz. |
| Contento / orgullo | Sonrisa del video vertical. |
| Alegría / entusiasmo / juego / celebración | Tramo de sonrisa del video vertical, de ida y vuelta. |
| Reposo | Video vertical completo. |
| Buscar | Video horizontal completo. |
| Escuchar | Tramo de miradas del video vertical, de ida y vuelta. |
| Curiosidad | Tramo de mirada arriba del video vertical, de ida y vuelta. |
| Miradas izquierda / derecha | Recorrido de los cuadros del giro y pose final sostenida. |
| Miradas arriba / abajo / timidez | Recorrido del giro correspondiente y pose final sostenida. |

Las correspondencias completas están en `portrait_routes.h`. En un comando
combinado con izquierda/derecha, la mirada tiene prioridad visual: todavía no hay
imágenes dormido/enojado para cada orientación. `LOOK centro` devuelve al frente
las secuencias direccionales, sin cancelar el identificador lógico de animación.
`STATUS` sigue describiendo el estado lógico del catálogo; `PORTRAIT` informa el
cuadro realmente dibujado y los errores del reproductor.

Los archivos del renderizador geométrico anterior se conservan como referencia.
No se dibujan ni se utiliza Kirby como fallback. No se generan movimientos nuevos
de boca; se podrán incorporar los siguientes videos sin cambiar los comandos.

## Compilar y cargar

La placa comprobada tiene ESP32-S3, flash de 16 MB y PSRAM de 8 MB.
`partitions.csv` reserva una aplicación de 12 MiB. Esta distribución usa carga
por USB; no tiene una segunda aplicación para actualización OTA.

Después de clonar o mover el proyecto, actualizar solamente la ruta local del
banco incluido (Python estándar; conserva exactamente los cuadros ya aprobados):

```powershell
python tools/generate_portrait_firmware.py --refresh-path
```

Para regenerar el banco porque cambiaron las fuentes, primero reconstruir los
cuadros locales desde los videos (Pillow, NumPy, SciPy y FFmpeg), y después
empaquetarlos (Pillow):

```powershell
python tools/prepare_aubar_frames.py --ffmpeg RUTA/ffmpeg.exe
python tools/generate_portrait_firmware.py
```

Compilar secuencialmente con Arduino CLI y el core ESP32 3.3.8:

```powershell
arduino-cli compile --clean --fqbn "esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=opi" --jobs 1 --build-property upload.maximum_size=12582912 --build-path build/portrait --output-dir build/portrait-output firmware/KirbyPantalla
arduino-cli upload --fqbn "esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=opi" --port COM3 --input-dir build/portrait-output firmware/KirbyPantalla
```

Adaptar el puerto a la placa. El generador no se ejecuta al iniciar el panel y no
necesita internet. Se conserva intacto el material original de Nahuel.

## Comprobar por USB

Con el panel desconectado del puerto:

```powershell
.venv/Scripts/python.exe tools/test_portrait_usb.py --port COM3
.venv/Scripts/python.exe tools/test_catalog_usb.py --port COM3
```

La primera prueba compara los checksums de los cuadros descomprimidos en la placa
contra el banco local, comprueba las seis poses, las miradas, ambos videos,
memoria y avance de cuadros. La segunda comprueba todos los identificadores y
las combinaciones del panel. Ambas devuelven el dispositivo al modo automático.

Las vistas previas del banco ya cuantizado al tamaño de pantalla están en
`frames-preparados/firmware/lcd-172x320.jpg`.

## Registro de verificación — 13 de noviembre de 2026

- Placa detectada en COM3: ESP32-S3, flash 16 MB y PSRAM 8 MB.
- Compilación con un proceso: 7.818.781 bytes de aplicación y 23.548 bytes de
  variables globales. Partición máxima: 12.582.912 bytes.
- Primera carga USB completada y verificada por hash.
- Prueba del retrato aprobada: las seis poses descomprimidas en placa coinciden
  con sus checksums locales; las tres miradas y ambos videos funcionan;
  cero errores de descompresión, con 8.388.608 bytes de PSRAM detectados.
- Catálogo USB aprobado: 51 opciones individuales y 153 combinaciones, incluyendo
  persistencia de mirada durante animaciones. Modo automático restaurado.
- La primera revisión visual detectó el problema de orden de color descrito
  arriba. Se corrigió, recompiló y completó la segunda carga USB con verificación
  de hash. La prueba del retrato volvió a pasar sin errores.
- Nahuel confirmó después de la segunda carga que el fondo y los colores del
  personaje se ven correctamente en la pantalla física. Modo automático activo.
- En una segunda fotografía confirmó el resultado general y señaló un halo claro
  leve en algunos movimientos. Se conserva como detalle pendiente de pulido del
  recorte; no se cambian los recursos aprobados en este commit.

## Archivos que se versionan

Se incluyen los videos originales, las seis imágenes con fondo optimizadas en
WebP, las seis imágenes transparentes WebP, scripts, configuración, documentación,
hojas de revisión JPG y el banco comprimido que reproduce el firmware aprobado.

Los originales duplicados JFIF/PNG, los PNG decodificados y los atlas/cuadros WebP
regenerables se conservan en la PC, excluidos de Git. No se borra ningún original.
La ruta de ensamblado también es local y se crea con `--refresh-path` al clonar.
