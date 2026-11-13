# Interpretación contextual de Aubar

Groq ahora dirige conjuntamente la respuesta, los gestos y la prosodia disponible.
No hay un clasificador de emociones por palabras ni una tabla que asigne frases a emociones.
El modelo recibe el contexto de la conversación y el catálogo real del avatar.

## Decisión del modelo

Cada respuesta contiene `text` y de uno a cuatro `segments`. Un fragmento incluye:

```json
{
  "text": "Nahuel, vas a lograrlo.",
  "gesture": "animation:angry",
  "delivery": "en tono furioso",
  "speed": 1.0,
  "energy": 1.2,
  "pause_ms": 0
}
```

`gesture` usa un identificador exacto con prefijo para evitar confundir una
expresión con una animación. El modelo elige libremente dentro del catálogo.
`delivery` describe la intención y aparece en el panel; no se pronuncia.

La aplicación valida los identificadores, los límites de voz y que el texto
hablado coincida con el escrito. Rechaza fragmentos incongruentes o comandos
desconocidos. Las respuestas antiguas sin plan mantienen compatibilidad.

Las instrucciones distinguen actuar una emoción de describirla: una frase de
ánimo puede interpretarse enojado si se pide. Una petición literal conserva la
frase, sin agregar consejos. Se usa un solo fragmento para frases cortas y solo
se divide cuando conviene cambiar la intención o introducir una pausa.

## Contenido antes de actuación

La conversación se resuelve primero como texto, sin el catálogo de animaciones
ni la obligación de construir un plan JSON. Una segunda llamada a Groq recibe
el diálogo y ese texto fijado para preparar la actuación. El director no puede
cambiar las palabras: la aplicación compara ambos textos antes de aceptarlo.

Si la segunda etapa falla, excede la cuota o intenta sustituir el contenido, se
conserva la primera respuesta con una interpretación neutral y el panel lo
informa. No hay reintentos automáticos. Ambas etapas comparten el tiempo máximo
configurado y la misma cancelación. La prueba de conexión sigue usando una sola
llamada; una respuesta de conversación ahora usa dos llamadas y más cuota.

En GPT-OSS las instrucciones de aplicación se envían como `developer`. La etapa
de contenido usa razonamiento medio y la de actuación usa razonamiento bajo.
Ver [formato Harmony](https://github.com/openai/openai-cookbook/blob/main/articles/openai-harmony.md)
y [controles de razonamiento de Groq](https://console.groq.com/docs/reasoning).

Esto impide que la preparación de voz reescriba una respuesta, pero no garantiza
que el primer texto sea correcto: el modelo todavía puede interpretar mal una
petición informal. En la regresión del saludo sin comillas omitió la última
oración. Con `decime enojado: "bien nahuel! estoy bien!"` conservó ambas oraciones
y eligió enojo. Para repetición exacta de varias frases conviene delimitarlas.

## Voz y tiempos

Se conserva `am_onyx`, en español e inglés. Groq controla:

| Control | Rango | Efecto real |
| --- | --- | --- |
| `speed` | 0.8–1.2 | Multiplica el ritmo actual de síntesis. |
| `energy` | 0.65–1.2 | Modifica la amplitud antes del volumen del usuario, con límite de picos. |
| `pause_ms` | 0–600 | Agrega silencio después del fragmento. |

El mismo proceso de Kokoro sintetiza los fragmentos y crea una pista continua.
El inicio y fin reales de cada fragmento se publican al comenzar la reproducción,
después de sintetizar. El panel sigue esa línea de tiempo y cambia el gesto.
Durante una pausa dirigida se cierra la boca conservando el gesto. No se
interrumpe la animación por cada sílaba ni por fluctuaciones de volumen.

Cancelar, desconectar o iniciar otra conversación descarta la interpretación
pendiente. La repetición manual de una respuesta conserva su plan original.
Las decisiones del modelo respetan el control manual posterior del usuario.

## Rostro durante el habla

Antes el video de habla reemplazaba toda la cara. El firmware nuevo conserva
el rostro y el cuerpo de la emoción y mezcla una región de boca del video de
habla, con bordes suaves y anclajes del retrato aprobado. Los anclajes son
geometría del personaje, no reglas para interpretar conversaciones.

Se admite esta composición para las emociones del tramo 02 y los gestos del
tramo 03. En poses sin una boca frontal compatible se conserva la pose o su
animación original mientras suena la voz. No se fuerza una boca frontal sobre
un rostro girado o una pose con la mano cerca de la cara.

`PORTRAIT` agrega `face`: identifica el cuadro facial conservado; 65535 indica
habla frontal sin composición. `frame` y `checksum` siguen identificando el
cuadro fuente decodificado, antes de mezclar los píxeles de la boca.

## Límites de esta versión

Onyx no recibe una instrucción emocional nativa. `delivery="furioso"` no se
convierte en actuación acústica por sí sola: se ejecutan los controles reales
de ritmo, energía y pausas que eligió el modelo. No se promete la expresividad
de un motor de voz entrenado para interpretar instrucciones emocionales.

La composición facial es una primera aproximación: puede necesitar ajustes de
posición o tono alrededor de los labios. La cara emocional se conserva como
pose durante el habla; no se generan videos nuevos ni fonemas exactos.

No se agregó otro modelo, entrenamiento, descargas ni dependencia de pandas.
Para evaluar conversaciones se pueden preparar casos de prueba y analizarlos
en una tabla; esa evaluación no debe convertirse en reglas de producción.

Referencias: [interfaz de Kokoro](https://github.com/thewh1teagle/kokoro-onnx/blob/main/examples/with_voice.py)
y [voz de Groq](https://console.groq.com/docs/text-to-speech). La documentación de
voz de Groq consultada ofrece inglés y árabe; no se cambió automáticamente a
otro motor porque Aubar debe conservar español e inglés y la voz elegida.

## Validación

- 238 pruebas locales aprobadas, incluidas validación del plan, temporización,
  silencios, cambios de gesto, repetición y cancelación.
- Texto inmutable ante un director que intenta cambiarlo, fallo de la segunda
  etapa, cancelación entre etapas y tiempo máximo compartido comprobados.
- Prueba real con Groq y el panel: petición literal de enojo, texto preservado,
  `animation:angry`, intención «en tono furioso», energía 1.2.
- Audio real de Onyx y ESP32: rostro de enojo 778 conservado y 17 cuadros de
  boca observados durante la misma frase, sin errores de decodificación.
- Verificación USB de 12 rostros durante el movimiento de boca, conservación
  de la pose de pensar, habla neutral y detención. Comando de prueba:

```powershell
.venv/Scripts/python.exe tools/test_expressive_usb.py --port COM3
```
