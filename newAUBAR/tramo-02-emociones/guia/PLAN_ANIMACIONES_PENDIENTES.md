# Próximas imágenes y videos de Aubar

Revisión: 13 de noviembre de 2026. Referencias: `portrait_routes.h`, catálogo del panel y hoja `../../tramo-01-base-miradas/frames-preparados/firmware/lcd-172x320.jpg`.

## Qué tenemos

Hay 23 acciones en el catálogo. Todas tienen una ruta visual, pero eso no significa que tengan un gesto exclusivo. Una pose fija con un fundido ya permite representar una acción; no se cuenta como material ausente solo por no tener un video propio.

| Grupo | Acciones | Situación |
| --- | --- | --- |
| Material básico adecuado (9) | Dormir, despertar, reposo, escuchar, pensar, buscar, trabajar, adormecerse, curiosear | Disponibles. Dormir/adormecerse comparten ojos cerrados; despertar vuelve al frente. Pensar tiene su imagen de mano en el mentón. Se pueden mejorar sus transiciones más adelante. |
| Movimiento de alegría compartido (4) | Entusiasmarse, alegría, jugar, celebrar | Disponibles usando el mismo tramo de sonrisa. Falta diferenciarlas si queremos gestos propios. |
| Representación provisional por revisar o completar (10) | Aburrirse, sospechar, enojarse, confundirse, sorprenderse, orgullo, timidez, tristeza, reír, asustarse | Detalle abajo. No son diez imágenes necesariamente: algunas pueden compartir material y otras ya tienen una base aprovechable. |

## Primera tanda: seis imágenes nuevas

Usar el retrato frontal original CON fondo como referencia de identidad y composición. Mantener exactamente estilo 3D, rostro, cabello, lentes, ropa, encuadre, tamaño, fondo, luz, escritorio y computadora. Mantener las manos en su posición original: estas seis imágenes cambian principalmente ojos, cejas y boca.

| Archivo sugerido | Expresión que debe verse | Qué reemplaza hoy |
| --- | --- | --- |
| `01-enojado.webp` | Cejas fruncidas, mirada firme, labios apretados. Enojo moderado, sin gritar. | La imagen de pensar. |
| `02-sospechoso.webp` | Una ceja ligeramente levantada, ojos algo entrecerrados y mirada lateral leve, boca cerrada. | La imagen de pensar. |
| `03-confundido.webp` | Cejas asimétricas levantadas, mirada de duda y boca apenas entreabierta. | La imagen de pensar; necesitamos distinguir confusión de reflexión. |
| `04-triste.webp` | Extremos interiores de las cejas elevados, mirada baja y comisuras levemente hacia abajo. Sin lágrimas. | La imagen dormido. |
| `05-asustado.webp` | Ojos abiertos, cejas elevadas y boca entreabierta con tensión. | La imagen de boca abierta, que no distingue miedo de sorpresa. |
| `06-timido.webp` | Mirada baja/lateral, sonrisa pequeña y discreta, leve inclinación de cabeza. | Un movimiento genérico de mirar abajo. |

Generar cada imagen como una modificación de la misma referencia frontal, conservando todo lo demás. No usar la imagen anterior generada como nueva referencia: evitar acumular cambios de identidad y anatomía.

## Video de prueba de 10 segundos

Las seis imágenes son referencias de expresión, no seis diapositivas para encadenar. Pedir un único plano con movimiento continuo, cámara fija y cuadros nítidos. El frontal existente sirve también de referencia inicial/final; no requiere generar una séptima imagen nueva.

Orden propuesto para probar: neutral → sospecha → confusión → enojo → tristeza → miedo → timidez → neutral.

- 0–0,5 s: frontal neutral.
- 0,5–9,5 s: seis intervalos de 1,5 s, uno por expresión. En cada intervalo, transición suave durante unos 0,75 s y sostener el gesto durante unos 0,75 s.
- 9,5–10 s: volver al frontal neutral.

Es una prueba exigente: seis gestos caben como objetivo, pero debemos revisar si el generador respeta los seis y mantiene el rostro estable. Si mezcla u omite expresiones, dividir en dos videos con tres gestos cada uno. No dar por completada una acción hasta revisar los cuadros resultantes.

Para recortar cada gesto independiente necesitaremos elegir sus cuadros y preparar el regreso al reposo. El orden de este video no será el orden obligatorio de las acciones en la app.

## Después de esta tanda

| Acción | Material actual | Pendiente |
| --- | --- | --- |
| Aburrirse | Dormido | Ojos pesados pero abiertos y gesto desganado, para distinguir aburrimiento de sueño. |
| Sorprenderse | Imagen de boca abierta | La base ya existe. Revisar si basta y animar ojos/cejas/boca; no pedir otra imagen por defecto. |
| Orgullo | Sonrisa extraída del video | Se puede conservar. Si queremos diferenciarla: sonrisa satisfecha y mentón apenas elevado. |
| Reír | Imagen de boca semiabierta | Las imágenes de boca ya existen. Falta una secuencia de risa reconocible. |
| Entusiasmarse / alegría / jugar / celebrar | Un mismo tramo de sonrisa | Diferenciación opcional posterior con gestos propios. |

La boca sincronizada con la voz es un trabajo separado; una secuencia de risa no proporciona sincronización labial.

## Revisión antes de dar por terminado un recurso

Comprobar identidad, manos, lentes, computadora, posición y escala constantes. Mantener los originales con fondo para el video. Quitar fondo y optimizar las copias destinadas a la app después; conservar siempre las fuentes originales.

Esta tanda cubre los estados emocionales básicos. Las 28 expresiones antiguas también incluyen variantes de dirección y asimetría: estos seis gestos frontales no reemplazan todas esas variantes.
