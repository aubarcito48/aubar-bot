# Nuevo avatar de Botbar: guía de trabajo

## Material vigente después del reinicio

**Videos recibidos y extracción preparada:** ver [Cuadros preparados](../frames-preparados/README.md). Hay dos fuentes independientes con 240 cuadros cada una, atlas WebP y secuencias por movimiento. Las seis imágenes estáticas están incluidas aparte. El firmware del retrato ya está implementado y cargado; ver [registro y correspondencias](./FIRMWARE_AVATAR.md). Las nuevas emociones y la boca animada quedan para futuros recursos.

Se reinició la creación del avatar desde una nueva referencia personal de Nahuel, siguiendo el proceso de IsaBot: resolver las imágenes, generar un video coherente y extraer sus cuadros. Las instrucciones anteriores sobre `nahue_pick.png` y las 28 imágenes quedan como historial; no son requisitos para continuar.

Hay seis poses nuevas: `frente`, `mira-pc`, `pensando`, `dormido`, `boca-semi-abierta` y `boca-abierta`.

| Carpeta | Uso acordado |
| --- | --- |
| `animaciones-original/formato jfif` | Originales con fondo entregados por Gemini. Conservar como fuente y para generar el video. |
| `animaciones-original/formato webp` | Copias optimizadas de las imágenes con fondo. |
| `animaciones-sin-fondo/formato png` | Fuentes sin fondo que se conservan; no se usan en la aplicación. |
| `animaciones-sin-fondo/formato webp` | Imágenes sin fondo elegidas para usar en Botbar. |

Los dos videos nuevos ya están disponibles en `../videos/`. El prompt anterior de `PRIMER_VIDEO_PRUEBA.md` se conserva como historial. El estado de la integración y la revisión de pantalla se registra en `FIRMWARE_AVATAR.md`.

---

## Historial de la propuesta anterior

Esta guía registra lo que acordamos para preparar el nuevo avatar. Primero creamos las imágenes; después, los videos que aportarán los cuadros intermedios para darle movimiento suave.

> **Cambio de plan:** ya se generaron diez imágenes y se pausa la creación de las restantes para hacer una primera prueba de video. Seguir [Primer video de prueba](./PRIMER_VIDEO_PRUEBA.md), que incluye las referencias elegidas y el prompt. La lista de 28 poses queda como referencia para etapas posteriores.

## 1. Personaje y estilo elegidos

La referencia es [nahue_pick.png](../../nahue_pick.png).

El estilo es **anime semirrealista con pintura digital**: proporciones naturales, rasgos suavizados de anime y sombreado con volumen, como una ilustración de personaje de videojuego.

Conservar el rostro, cabello, auriculares y vestimenta de esa imagen. Esta elección reemplaza la propuesta anterior de usar estilo Pixar.

La imagen actual tiene expresión neutral y está en vista de tres cuartos: la cabeza y el torso están algo girados. Sirve como referencia de identidad. Una pose neutral estrictamente frontal debe mostrar la cabeza y el torso de frente.

## 2. Generar las 28 imágenes

Generar primero todas las poses de la lista. Usar siempre la referencia original y, una vez aprobada, la imagen neutral como apoyo para mantener la consistencia.

En cada pedido conservar:

- El mismo personaje, estilo, ropa y accesorios.
- El mismo tamaño de lienzo, encuadre y escala del personaje.
- La misma cámara, iluminación y fondo.
- Espacio alrededor de la cabeza y los hombros, sin recortes accidentales.

Cambiar solamente la expresión y la orientación necesarias para cada pose. Evitar texto, símbolos flotantes y objetos nuevos. Generar una imagen individual por pose.

Como formato de trabajo, usar imágenes cuadradas de 1024 × 1024 píxeles y fondo liso uniforme, fácil de eliminar después. Priorizar que el rostro se entienda al reducirlo a la pantalla de Botbar, de 172 × 320 píxeles.

### Texto base para Gemini

Adjuntar `nahue_pick.png` y completar la pose al final:

> Usá al personaje de la imagen adjunta como referencia. Conservá exactamente su identidad, rostro, cabello, auriculares, vestimenta y estilo anime semirrealista con pintura digital, sombreado suave con volumen y proporciones naturales. Mantené el mismo encuadre, escala, cámara, iluminación y fondo que en la imagen base aprobada. Generá una sola imagen, sin texto ni elementos nuevos. Cambiá únicamente la expresión y la orientación de la cabeza necesarias para esta pose: **[descripción de la pose]**.

### Lista de poses de Botbar

Los nombres corresponden a las 28 expresiones del avatar actual. Izquierda y derecha se describen desde el punto de vista de quien mira la imagen.

| Nº | Nombre del archivo sugerido | Qué pedir |
| --- | --- | --- |
| 01 | `01-neutral.png` | Neutral, cabeza y torso de frente, mirada a la cámara y expresión tranquila. |
| 02 | `02-upward-side-glance.png` | Mirada lateral hacia arriba, con leve inclinación de cabeza. |
| 03 | `03-downward-gaze.png` | Mirada hacia abajo, cabeza ligeramente baja. |
| 04 | `04-skeptical-right.png` | Escepticismo hacia la derecha, un ojo más entrecerrado que el otro. |
| 05 | `05-small-attentive.png` | Atención serena, ojos moderadamente abiertos. |
| 06 | `06-wide-downward-gaze.png` | Mirada hacia abajo con ojos bien abiertos. |
| 07 | `07-surprised-left.png` | Sorpresa mirando hacia la izquierda. |
| 08 | `08-sleepy-squint.png` | Sueño, párpados muy bajos y expresión relajada. |
| 09 | `09-angry-right.png` | Enojo hacia la derecha, con ceño fruncido. |
| 10 | `10-curious-left.png` | Curiosidad hacia la izquierda, con leve inclinación de cabeza. |
| 11 | `11-asymmetric-down-right.png` | Mirada abajo a la derecha, un ojo más abierto que el otro. |
| 12 | `12-attentive-left.png` | Escucha atenta orientada ligeramente hacia la izquierda. |
| 13 | `13-joyful-wide.png` | Alegría intensa y sonrisa amplia natural. |
| 14 | `14-eyes-closed.png` | Ojos completamente cerrados y rostro relajado. |
| 15 | `15-joyful-down-right.png` | Alegría mirando abajo a la derecha. |
| 16 | `16-skeptical-left.png` | Escepticismo hacia la izquierda, con ojos asimétricos. |
| 17 | `17-far-right-glance.png` | Mirada marcada hacia la derecha, sin llegar al perfil completo. |
| 18 | `18-angry-left.png` | Enojo hacia la izquierda, con ceño fruncido. |
| 19 | `19-playful-right.png` | Expresión juguetona y pícara hacia la derecha. |
| 20 | `20-asymmetric-up-left.png` | Mirada arriba a la izquierda, con apertura desigual de los ojos. |
| 21 | `21-gentle-downward-gaze.png` | Mirada suave hacia abajo, tranquila y amable. |
| 22 | `22-wide-down-left.png` | Mirada abajo a la izquierda con ojos bien abiertos. |
| 23 | `23-surprised-wide-left.png` | Sorpresa intensa hacia la izquierda, más marcada que en la pose 07. |
| 24 | `24-drowsy-closed.png` | Adormilado, ojos cerrados y cabeza ligeramente vencida por el sueño. |
| 25 | `25-suspicious-right.png` | Desconfianza hacia la derecha y ojos entrecerrados. |
| 26 | `26-shy-downward.png` | Timidez, mirada baja y gesto reservado. |
| 27 | `27-angry-brows.png` | Enojo frontal con ceño claramente fruncido. |
| 28 | `28-uneasy-left.png` | Inquietud hacia la izquierda, con tensión sutil en la mirada. |

La lista sirve para generar imágenes. **Su orden no es el orden de un video.** Las miradas neutrales a izquierda y derecha del primer video pueden requerir referencias adicionales: las poses del catálogo que miran a esos lados también incluyen emociones.

## 3. Revisar las imágenes antes de hacer videos

Cuando estén listas, revisarlas con Codex. Comprobar que sigue siendo el mismo personaje y que no cambian el rostro, los auriculares, la ropa, la escala ni el encuadre entre poses.

Corregir las imágenes que tengan diferencias antes de usarlas como referencias de video. Guardar los originales de cada imagen.

## 4. Preparar el primer video de 10 segundos

Después de revisar las imágenes, Codex preparará el prompt específico para el primer video y señalará qué referencias usar.

La secuencia propuesta es:

| Tiempo | Acción |
| --- | --- |
| 0–2 segundos | Neutral, mirando al frente y quieto. |
| 2–4 segundos | Giro suave hacia la izquierda y breve pausa. |
| 4–6 segundos | Regreso suave al centro. |
| 6–8 segundos | Giro suave hacia la derecha y breve pausa. |
| 8–10 segundos | Regreso a la pose neutral inicial. |

Requisitos: cámara fija, movimiento continuo, sin cortes, sin cambios de escena y sin cambios de identidad, fondo o iluminación. El torso debe permanecer estable mientras se mueve la cabeza.

No intentar incluir las primeras diez poses en esos diez segundos. Necesitamos tiempo para ver las transiciones y extraer sus cuadros intermedios.

## 5. Generar los demás videos por grupos

Agrupar movimientos relacionados: sueño y despertar, alegría, enojo, curiosidad y otras reacciones. Definir el contenido y la duración de cada video después de revisar las imágenes.

Procurar que cada video empiece y termine en la misma pose neutral para facilitar la conexión entre movimientos.

Botbar tiene 23 animaciones actuales: dormir, despertar, reposo, escuchar, pensar, buscar, trabajar, entusiasmarse, aburrirse, sospechar, enojarse, adormecerse, alegría, curiosidad, confusión, sorpresa, orgullo, timidez, tristeza, risa, miedo, juego y celebración. Estas combinan las poses; no necesitamos necesariamente un video independiente por cada animación.

## 6. Extraer cuadros y adaptar Botbar

Con los videos aprobados, Codex podrá:

1. Seleccionar los tramos útiles y extraer los cuadros intermedios.
2. Alinear el personaje, preparar el fondo y ajustar el tamaño para la pantalla.
3. Organizar las poses y transiciones para las animaciones de Botbar.
4. Adaptar el dibujado del firmware y verificar el resultado en el dispositivo.

La app de clima sirve como referencia del método de extraer cuadros de video. Botbar conservará sus propias expresiones y animaciones. Su firmware actual dibuja geometría, por lo que usar imágenes requiere una adaptación posterior; generar los recursos no actualiza automáticamente el dispositivo.

## Estado actual

- Referencia elegida: `nahue_pick.png`.
- Estilo elegido: anime semirrealista con pintura digital.
- Diez imágenes generadas y revisadas en `ani`.
- Generación de las poses restantes pausada mientras probamos el video.
- Próximo paso: generar el primer video con el prompt de `PRIMER_VIDEO_PRUEBA.md`.
- La adaptación del código todavía no comenzó.
