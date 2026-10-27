# Catálogo del avatar

Los datos provienen de `avatar-original/kirby.avatar.json`: **28 expresiones,
23 animaciones y 74 pasos**. No es necesario descargar opciones por separado.

El firmware adapta el modelo a una proyección ortográfica en la pantalla de
172 × 320. Importa las formas de ojos, inclinaciones de cabeza, colores y
movimientos `shake`/`slowDrift`. Usa interpolación suave de ángulos y formas;
no ejecuta el motor web de resortes ni su interpolación de cuaterniones. Los
movimientos de temblor y deriva se recrean con oscilaciones locales. Por eso la
apariencia y el movimiento no son idénticos al renderizado del navegador.

Las secuencias conservan el orden, las transiciones, las permanencias y los
intervalos de parpadeo exportados. Una animación seleccionada se repite; el modo
automático reproduce una vuelta de cada una. BOOT adelanta a la siguiente
animación o, en modo manual con pose fija, a la siguiente expresión.

Todas las opciones admiten mirada izquierda, centro o derecha con firmware
v4: **153 combinaciones**. La mirada explícita se mantiene durante la secuencia.
Los comandos y ejemplos están en [la guía del panel](herramienta-pc.md#comandos-combinados).

## Expresiones

Se eligen en **Catálogo → Expresión fija**. Por voz: «expresión» seguido de la
etiqueta en español. Los cinco comandos anteriores siguen disponibles.

| Etiqueta | ID USB | Nombre original |
| --- | --- | --- |
| Neutral | `neutral` | `neutral` |
| Contento | `contento` | `joyful-wide` |
| Sorprendido | `sorprendido` | `surprised-wide-left` |
| Dormido | `dormido` | `eyes-closed` |
| Enojado | `enojado` | `angry-right` |
| Mirada lateral arriba | `upward-side-glance` | `upward-side-glance` |
| Mirada abajo | `downward-gaze` | `downward-gaze` |
| Escéptico derecha | `skeptical-right` | `skeptical-right` |
| Atento pequeño | `small-attentive` | `small-attentive` |
| Mirada amplia abajo | `wide-downward-gaze` | `wide-downward-gaze` |
| Sorpresa izquierda | `surprised-left` | `surprised-left` |
| Somnoliento | `sleepy-squint` | `sleepy-squint` |
| Curioso izquierda | `curious-left` | `curious-left` |
| Asimétrico abajo derecha | `asymmetric-down-right` | `asymmetric-down-right` |
| Atento izquierda | `attentive-left` | `attentive-left` |
| Alegre abajo derecha | `joyful-down-right` | `joyful-down-right` |
| Escéptico izquierda | `skeptical-left` | `skeptical-left` |
| Mirada derecha | `far-right-glance` | `far-right-glance` |
| Enojado izquierda | `angry-left` | `angry-left` |
| Juguetón derecha | `playful-right` | `playful-right` |
| Asimétrico arriba izquierda | `asymmetric-up-left` | `asymmetric-up-left` |
| Mirada suave abajo | `gentle-downward-gaze` | `gentle-downward-gaze` |
| Mirada amplia abajo izquierda | `wide-down-left` | `wide-down-left` |
| Adormilado | `drowsy-closed` | `drowsy-closed` |
| Sospechoso derecha | `suspicious-right` | `suspicious-right` |
| Tímido | `shy-downward` | `shy-downward` |
| Cejas enojadas | `angry-brows` | `angry-brows` |
| Inquieto izquierda | `uneasy-left` | `uneasy-left` |

## Animaciones

Se eligen en **Catálogo → Animación en bucle**. Por voz basta la etiqueta; también
se acepta «animación» antes de ella. La coincidencia es con la frase completa.

| Comando de voz | ID USB |
| --- | --- |
| Dormir | `sleeping` |
| Despertar | `waking` |
| Reposo | `idle` |
| Escuchar | `listening` |
| Pensar | `thinking` |
| Buscar | `searching` |
| Trabajar | `working` |
| Entusiasmarse | `excited` |
| Aburrirse | `bored` |
| Sospechar | `suspicious` |
| Enojarse | `angry` |
| Adormecerse | `drowsy` |
| Alegría | `happy` |
| Curiosear | `curious` |
| Confundirse | `confused` |
| Sorprenderse | `surprised` |
| Orgullo | `proud` |
| Timidez | `shy` |
| Tristeza | `sad` |
| Reír | `laughing` |
| Asustarse | `scared` |
| Jugar | `playful` |
| Celebrar | `celebrate` |

## Regeneración y validación

Ejecutar `python tools/generate_avatar_data.py` después de editar el JSON original.
Genera `avatar_ids.h`, `avatar_data.h`, `animation_data.h` y el catálogo del panel.
Los cinco IDs de expresiones existentes se mantienen al principio para conservar
los comandos anteriores. El generador rechaza tipos de movimiento o transición
no soportados; no omite datos silenciosamente.

`tests/CatalogValidation` reúne pruebas de botones, parpadeos, parser, transporte,
las 23 secuencias, el recorrido automático, interrupciones, rollover del reloj y
las 784 parejas de expresiones. En la placa de pruebas, enviar `R` ejecuta las
comprobaciones y devuelve el resultado y el tiempo máximo de renderizado.
Este sketch reemplaza temporalmente el programa normal: volver a cargar
`firmware/KirbyPantalla` al terminar.

Con el firmware normal se puede ejecutar
`python tools/test_catalog_usb.py --port COM3` para comprobar las 51 opciones y 153 combinaciones,
sus confirmaciones y la cancelación de animaciones mediante expresiones fijas.
Cerrar el panel antes de estas pruebas para liberar el puerto.
