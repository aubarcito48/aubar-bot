# Habla de Botbar

El video original está en `../videos/botbar-hablando.mp4`: 240 cuadros a 24 fps.
Se conservan todos en la preparación local. El firmware incorpora los cuadros
36 a 215 (180 consecutivos), respetando su velocidad original. Recorre la
secuencia hacia adelante y atrás para evitar un corte entre extremos.

## Probar

1. Cargar el firmware nuevo y volver a abrir el panel.
2. Conectar el ESP32 en **Dispositivo**.
3. En **Voz**, escribir una frase y pulsar **Probar voz**.
4. La boca empieza cuando comienza el audio, después de la síntesis.
5. Probar **Detener** y una respuesta larga del chat con voz activada.

También acompaña las respuestas por micrófono y **Escuchar respuesta**. Se
mantiene la expresión lógica anterior y se recupera mediante un fundido al
terminar. No se cambia a una imagen fija entre sílabas. Esta versión acompaña
la duración del audio; todavía no representa los fonemas exactos del texto.

El comando USB opcional `SPEECH on` renueva una señal de reproducción cada
700 ms; `SPEECH off` termina el habla. Si la app se cierra o desconecta,
la señal caduca a los 4 segundos. Los firmwares anteriores pueden rechazar
esta extensión sin impedir que el panel y la voz sigan funcionando.

## Regenerar

Desde la raíz, con Pillow, NumPy, SciPy y FFmpeg disponibles:

```powershell
python tools/prepare_speech_frames.py --ffmpeg RUTA/ffmpeg.exe
python tools/generate_portrait_firmware.py
```

Compilar con `--clean` después de regenerar `portrait_assets.dat`: Arduino
puede reutilizar el objeto de ensamblador que contiene el banco anterior.
Consultar los demás argumentos en el README principal.

El primer firmware de habla tenía 666 cuadros y 11.187.880 bytes en su banco.
La integración del tramo 02 incorpora compresión entre cuadros sin pérdida;
consultar el tamaño vigente en la guía principal del firmware.

La máscara reutiliza el encuadre vertical aprobado. Verificar cabello, manos
y computadora en `../frames-preparados/hablar/revision-sin-fondo.jpg`.
Los originales y los videos de otros tramos se conservan intactos.

Prueba física automatizada, con el panel cerrado:

```powershell
.venv/Scripts/python.exe tools/test_portrait_usb.py --port COM3
```
