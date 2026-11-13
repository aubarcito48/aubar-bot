# Recursos del avatar por tramos

Todo el material de creación del avatar se organiza dentro de `newAUBAR`.

| Tramo | Contenido | Estado |
| --- | --- | --- |
| [01 — Base y miradas](tramo-01-base-miradas/guia/GUIA_AVATAR.md) | Seis poses iniciales, dos videos, miradas, parpadeos, sonrisa y cuadros del avatar actual. | Integrado en el ESP32. |
| [02 — Emociones](tramo-02-emociones/guia/PLAN_ANIMACIONES_PENDIENTES.md) | Enojado, sospechoso, confundido, triste, asustado y tímido. | Carpetas listas para recibir imágenes y video. |

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

Los scripts de preparación y empaquetado siguen apuntando al tramo 01 aprobado. El tramo 02 se integrará después de revisar sus nuevos recursos; crear sus carpetas no cambia lo que muestra la placa.

Al iniciar otra tanda, crear `tramo-03-nombre` con la misma estructura.
