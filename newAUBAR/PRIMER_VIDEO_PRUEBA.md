# Primer video de prueba

> **Propuesta anterior, pendiente de reemplazo:** este prompt se escribió para las imágenes antiguas de `ani`. Tras reiniciar el avatar, las imágenes vigentes están en `animaciones-original` y `animaciones-sin-fondo`. Preparar un nuevo prompt a partir de ellas antes de generar el video. Ver `GUIA_AVATAR.md` para los usos acordados de cada formato.

## Decisión actual

Se pausa la generación de las 28 poses. Ya hay diez imágenes en `ani`, pero algunas cambian las facciones y las manos. Primero probaremos si un video proporciona movimiento suave y mantiene el personaje.

Las diez imágenes fueron revisadas visualmente. La 01 sigue en tres cuartos; no necesitamos corregir ese ángulo para esta prueba. En la 07 y la 08 cambian las manos. Las direcciones de los nombres no siempre se traducen en un giro de cabeza visible.

## Referencias elegidas

- `ani/01-frente.jfif`: imagen principal y pose inicial/final.
- `ani/02-arriba.jfif`: referencia secundaria de mirada elevada.
- `ani/03-abajo.jfif`: referencia secundaria de mirada baja.

Si el generador admite una sola imagen, usar la 01. Si admite varias referencias, adjuntar estas tres e indicar cuál es la principal. Las secundarias orientan el gesto; la 01 define la identidad. No hace falta adjuntar las diez ni generar otras imágenes para esta prueba.

## Prompt para copiar

```text
Animá al personaje de la imagen principal en un único plano continuo de 10 segundos. La imagen principal es la de expresión neutral con la mirada a cámara. Las otras dos imágenes, si están adjuntas, son únicamente referencias para la mirada hacia arriba y hacia abajo.

Conservá exactamente el personaje y el estilo anime semirrealista de pintura digital de la imagen principal: mismo rostro, edad aparente, proporciones, cabello, auriculares, vestimenta, colores y sombreado. Mantené su orientación inicial de tres cuartos.

La cámara está completamente fija. Conservá el encuadre, el tamaño del personaje, la iluminación y el fondo blanco uniforme. Torso, hombros y manos permanecen inmóviles en la posición de la imagen principal.

Secuencia:
0–1 segundos: permanece en la pose inicial, con expresión neutral y mirada a cámara.
1–3 segundos: eleva suavemente la mirada y acompaña con un movimiento muy leve de la cabeza; mantiene brevemente esa posición.
3–5 segundos: vuelve suavemente a la pose y mirada iniciales; hace una breve pausa.
5–7 segundos: baja suavemente la mirada y acompaña con una inclinación muy leve de la cabeza; mantiene brevemente esa posición.
7–9 segundos: vuelve suavemente a la pose y mirada iniciales.
9–10 segundos: permanece quieto en la misma pose del comienzo.

El movimiento debe tener aceleración y frenado suaves, con anatomía estable en todos los cuadros intermedios. Los ojos se desplazan de forma coordinada. La boca permanece cerrada y la expresión tranquila.

Sin cortes, montaje, fundidos entre imágenes, cambios de escena, zoom ni movimiento de cámara. Sin gestos de manos, habla, cambios de ropa, deformaciones de rostro o accesorios, texto ni elementos nuevos. Sin desenfoque de movimiento fuerte: necesitamos cuadros nítidos para extraer una animación de avatar. Video silencioso.
```

## Qué revisar al terminar

1. El personaje conserva su rostro y sus accesorios durante todo el movimiento.
2. La cámara, las manos y el torso permanecen estables.
3. Los ojos y la cabeza se mueven de manera continua, sin saltos ni deformaciones.
4. Hay pausas que permiten seleccionar las poses.
5. El final se aproxima a la pose inicial y los cuadros están nítidos.

Guardar el archivo de video original descargado en esta carpeta. Después Codex revisará los cuadros para determinar qué tramos sirven. Este primer video prueba miradas y transiciones; las demás emociones se prepararán según el resultado.
