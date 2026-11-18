# Aubar Director: piloto local propio

El director trabaja con el catálogo de **Aubar**, sus 28 identificadores de
expresión y 23 animaciones. No usa imágenes, voces ni pesos de Isa. Conserva
**Kokoro / am_onyx**, las funciones del panel y los manejadores locales de USB,
micrófono y YouTube. Se reutiliza el método de evaluación de Isa, no su personaje.

## Qué está implementado

- Entrada de actuación independiente del texto aprobado. Las palabras no se
  reescriben, aunque se pida decir una frase positiva con una actuación enojada.
- Selección explícita de los 51 identificadores mediante el parser existente.
- Clasificador propio de 15 estilos de actuación solicitados y una clase neutral.
  No diagnostica cómo se siente el usuario ni interpreta toda conversación.
- Extracción semántica local ES/EN con [multilingual MiniLM](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2),
  Apache-2.0. Este extractor preentrenado es de Sentence Transformers; las
  etiquetas, entrenamiento del clasificador, umbrales y catálogo son de Aubar.
- Comparativa local de Random Forest y regresión logística. Para este piloto
  se seleccionó la segunda por sus resultados de validación, no por preferencia
  por un algoritmo. La inferencia del clasificador usa NumPy, sin pickle ni sklearn.
- Controles iniciales de ritmo, energía y pausa dentro de los límites de Onyx.
  Son perfiles conservadores, todavía no controles acústicos aprendidos.
- Una sola petición de contenido a Groq en modo local. No llama al director
  remoto, tampoco ante una duda del clasificador; conserva texto y pose neutral.
- Cancelación, presupuesto temporal, repetición y control manual conservados.
  Elegir una animación nunca abre YouTube, cambia el modo ni despacha funciones.

Los 51 IDs son los que reconoce el firmware; algunos tienen equivalencias
visuales heredadas. No equivalen a 51 videos independientes ni a 51 clases
aprendidas. Los estados de escuchar, pensar, buscar o trabajar siguen en sus
manejadores locales; los 15 estilos aprendidos cubren actuaciones conversacionales.

## Preparación explícita

Desde la raíz de Botbar, usando su entorno local:

```powershell
.venv/Scripts/python.exe -m pip install -r pc/requirements-director.txt
.venv/Scripts/python.exe tools/install_director_model.py
```

Descarga inicial de unos 128 MB, con revisión y SHA-256 fijados. Se guarda en
`models/aubar-director-minilm`, fuera de Git. No descarga durante una respuesta.
Los pesos pequeños de nuestro clasificador están en
`pc/aubar_control/director_weights/`. Si falta un archivo o cambia su hash o el
catálogo, el modo local conserva la respuesta con una selección neutral.

Para entrenar nuevamente, sólo con ejemplos sintéticos del repositorio:

```powershell
.venv/Scripts/python.exe -m pip install -r experiments/aubar_director/requirements.txt
.venv/Scripts/python.exe tools/train_aubar_director.py
```

No usa conversaciones personales, API de Groq, micrófono ni USB para entrenar.
El entrenamiento no forma parte del arranque del panel. Semilla, versiones y
hashes de corpus, catálogo y pesos quedan registrados en los artefactos.

## Prueba antes de activar

```powershell
.venv/Scripts/python.exe tools/preview_aubar_director.py --audio
```

Genera `tmp/aubar-director-v1/index.html`, WAVs de Onyx y `review.json` con
selección, controles y tiempos. No reproduce sonido automáticamente ni conecta
la placa. La prueba muestra gestos originales y voz: **no simula sincronización
fonética ni la composición de boca del ESP32**. Las rutas visuales de esta
revisión corresponden a los rangos existentes de `portrait_routes.h`.

Para probar el director desde el panel, configurar en `.env`:

```dotenv
AUBAR_DIRECTOR=local
```

Recargar configuración o reiniciar el panel. `AUBAR_DIRECTOR=groq` conserva el
director anterior y sigue siendo el valor predeterminado durante la revisión.
No se cambió el `.env` del usuario ni se cargó firmware nuevo en el ESP32.

## Resultados y límites de la primera tanda

`experiments/aubar_director/corpus.py` separa plantillas completas de entrenamiento
(1210 casos), validación (364) y prueba (244). No comparte solicitudes completas
entre particiones, pero **sí vocabulario de estilos**: es una evaluación sintética
de distintas formulaciones, no una medición de conversación real o de imágenes.
El umbral se elige exclusivamente con validación y queda congelado para prueba.

En los 244 casos de prueba:

- Acierto global con abstenciones neutrales: **80,7 %**.
- Exactitud balanceada entre clases: **63,3 %**.
- En los 120 pedidos de actuación: 73 estilos correctos, 5 incorrectos y 42
  abstenciones neutrales; acierto sobre todos los pedidos de actuación: **60,8 %**.
- Entre las 78 decisiones expresivas: **93,6 %** correspondieron a la etiqueta.
- En las 124 menciones, negaciones o consultas neutrales: cero actuaciones
  indebidas en esta prueba. No es una garantía para frases futuras.

La validación fue más difícil: 50,8 % global y 30,1 % balanceado con la misma
política conservadora. Ambos resultados se conservan en el informe; no se
presenta el mejor porcentaje como calidad general del bot. Los errores de estilo
y las abstenciones están disponibles en `experiments/aubar_director/report.json`.

Por estas limitaciones sigue como **piloto optativo**. Antes de reemplazar el
director habitual faltan ejemplos naturales, negaciones más variadas, pedidos
con varios estilos, contexto entre turnos y revisión visual humana. Una vez
congelada una nueva tanda, conviene usar un conjunto de prueba nuevo y separado.

## Etapas siguientes de la clasificación propia

1. Etiquetar ejemplos reales de actuación permitida, neutralidad y ambigüedad,
   preservando el catálogo y los manejadores de funciones de Aubar.
2. Medir y clasificar **Onyx/Kokoro**: fonemas, ritmo, silencios entre palabras y
   oraciones, tiempos de apertura y cierre; validar ES y EN por separado.
3. Clasificar el banco propio de imágenes: boca/labios/mandíbula, pose compatible,
   ojos y continuidad. Validar detecciones sobre este avatar antes de usarlas
   como referencia de entrenamiento.
4. Probar el selector temporal completo y la conexión USB sin saltos, incluyendo
   cancelaciones y cambios de expresión. La continuidad y la precisión de boca
   se evalúan aparte del acierto del director de gestos.

Botbar no tenía Rhubarb integrado; su boca actual recorre un clip mientras se
reproduce la voz. Ese mecanismo no se sustituyó en esta etapa. El porcentaje
anterior **no mide fonemas, labios, frames, voz emocional ni sincronización**.
