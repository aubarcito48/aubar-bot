# Configuración de Groq

La configuración se prepara localmente. Abrir el panel o recargar `.env` no
realiza solicitudes. **Probar conexión** permite comprobar la clave y el modelo
mediante una consulta real a Groq.

## Preparación

1. Abrir el panel mediante `.\tools\start_control.ps1`, que instala las
   dependencias en `.venv`.
2. Si no existe `.env`, copiar `.env.example` a `.env` en la raíz del proyecto.
   No reemplazar un archivo local que ya tenga configuración.
3. Completar `GROQ_API_KEY` dentro de `.env` con la clave propia, sin compartirla.
4. Guardar y pulsar **Recargar configuración** en la pestaña **IA** del panel.

Ejemplo de estructura, sin una clave real:

```dotenv
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS=20
```

- `GROQ_API_KEY`: obligatoria para preparar la integración. Sin ella, el panel
  informa qué falta y permite seguir usando el avatar, el micrófono y Dora.
- `GROQ_MODEL`: identificador configurable. El valor predeterminado es
  `openai/gpt-oss-20b`, listado por Groq entre sus modelos de producción al
  preparar esta configuración. El acceso efectivo se comprueba al consultar
  la API, no al cargar el archivo.
- `GROQ_TIMEOUT_SECONDS`: tiempo máximo de espera que usará el cliente, entre
  1 y 120 segundos; el valor predeterminado es 20. No admite valores infinitos.

Las variables del entorno del proceso tienen prioridad sobre `.env`, incluso
si están vacías. El archivo se busca en la raíz del proyecto, no en el
directorio desde el que se haya abierto el panel. Se lee como UTF-8, con o
sin BOM. No se modifica el archivo ni se agregan sus valores a `os.environ`.
No se expanden referencias `${OTRA_VARIABLE}` ni se ejecuta contenido del archivo.

## Credenciales y Git

`.env` y sus variantes locales están ignorados por `.gitignore`.
`.env.example` se versiona y mantiene `GROQ_API_KEY` vacía.
La clave no se muestra en la interfaz, en la representación de la configuración
ni en los errores de validación. No se imprimen valores al recargar.

Para comprobar las reglas sin mostrar contenido:

```powershell
git check-ignore -v .env
git status --short
```

Para preparar otra PC, copiar la plantilla y colocar su clave localmente.
La validación local informa formato y presencia; no equivale a una conexión
exitosa, autorización del modelo o disponibilidad del servicio.

## Probar la conexión

En la pestaña **IA**, pulsar **Probar conexión** con la configuración lista.
La prueba envía «Respondé en una frase breve: ¿estás lista para conversar?»
al modelo configurado, usando internet. La respuesta aparece como texto y
se informa si Groq respondió correctamente. Funciona sin conectar el ESP32.
Los comandos de voz, Dora y el control USB siguen disponibles. Esta prueba es
independiente de la conversación: no agrega sus mensajes al historial.

## Personalidad y conversación por texto

En **IA**, escribir un mensaje y pulsar **Enviar** o Enter. Aubar responde
como una asistente cercana, curiosa y respetuosa, en español con voseo y con
preferencia por frases breves adecuadas para escucharse. Las instrucciones
también le indican reconocer cuando falta información y no inventar recuerdos,
acciones realizadas ni acceso a sensores. Son instrucciones al modelo; no
constituyen una garantía de exactitud de cada respuesta.

La conversación aparece como **Vos / Aubar** y admite preguntas de seguimiento.
Por ejemplo, escribir «Mi color preferido es violeta» y después «¿Cuál es mi
color preferido?». El campo admite hasta 1000 caracteres; una respuesta tiene
como máximo 2000. La entrada se conserva si la consulta falla para poder
corregirla o reintentar manualmente.

Se conservan hasta **seis intercambios completos** y **12 000 caracteres de
historial**, sumando preguntas y respuestas. Al superar cualquiera de esos
límites se retiran los pares más antiguos. Cada consulta envía a Groq las
instrucciones de personalidad, ese contexto limitado y el mensaje actual.
El texto de conversación no se escribe en archivos, en Git ni en registros
de actividad del panel.

El historial solo incorpora un par pregunta/respuesta después de una respuesta
válida y exitosa. Los errores y resultados descartados no agregan turnos.
**Nueva conversación** borra el contexto y la vista, e invalida cualquier
respuesta pendiente. Si una solicitud ya estaba en curso, su operación de red
puede terminar en el trabajador; su resultado no reaparece ni se incorpora al
nuevo historial. Se podrá enviar otro mensaje cuando finalice esa operación.

Recargar la configuración y cerrar el panel también reinician el contexto.
No se recuperan conversaciones de una sesión anterior. **Probar conexión**
mantiene su función de diagnóstico y no cambia lo que recuerda Aubar.

## Conversación con micrófono y Dora

Las consultas reconocidas por el micrófono se envían a Groq usando el mismo
contexto que el campo de texto. Con el botón manual, esperar **Escuchando**,
decir «contame algo interesante» y soltar. En escucha automática, conectar
la placa, esperar la calibración y decir **«Aubar, contame algo interesante»**.
La [guía del panel](herramienta-pc.md#identificar-consultas-abiertas) detalla
la activación, los filtros y los ejemplos.

El panel informa que está preparando la respuesta y pausa la escucha durante
esa consulta. Muestra el resultado completo en **IA** y, con **Activar voz**
marcado, lo reproduce una sola vez con Dora. El volumen se toma al iniciar
la reproducción. No acepta audio como nuevas frases mientras prepara o lee
la respuesta. Después del audio conserva la protección de 350 ms y solo
retoma la escucha automática si sigue activada. La captura manual requiere
otra pulsación para continuar; también funciona sin conectar el ESP32.

Los comandos exactos del avatar mantienen prioridad y se ejecutan localmente,
sin consultar a Groq. Una consulta conversacional todavía no selecciona
expresiones o animaciones; esa integración se implementa por separado.
Los mensajes escritos y **Probar conexión** siguen mostrando texto sin lectura
automática. El historial sí se comparte entre preguntas escritas y habladas.

Desactivar la voz o pulsar **Detener** cancela la lectura actual o pendiente.
Si Groq todavía está respondiendo, el texto exitoso puede mostrarse e ingresar
al contexto, pero no se leerá después de volver a activar la voz. Un fallo de
audio tampoco elimina una respuesta válida ni repite la consulta a Groq.
Si falla la consulta, informa el error, no agrega un turno y vuelve a permitir
la escucha.

Solo se conserva una lectura de IA pendiente, con vencimiento de 15 segundos.
Comparte el motor de voz con las confirmaciones del catálogo: espera a que
termine una reproducción en curso, sin superponer voces. **Nueva conversación**,
recargar la configuración o cambiar la conexión USB descartan lecturas
anteriores. Una pregunta capturada antes de un reinicio o cambio de conexión
no se envía después. Desconectar durante una consulta por voz descarta su
resultado tardío, sin reejecutarlo al reconectar. Apagar el micrófono durante
la respuesta lo mantiene apagado al terminar.

El cliente usa HTTPS con validación de certificado y el endpoint oficial
`https://api.groq.com/openai/v1/chat/completions`. La clave se envía únicamente
en el encabezado de autorización, no en el texto de la consulta. No sigue
redirecciones y no imprime cuerpos de error, encabezados ni excepciones del
transporte. Si la respuesta incluyera la clave configurada, la oculta antes
de mostrarla.

Solo se admite una consulta en curso, sin acumular pedidos ni reintentar
automáticamente. La solicitud se ejecuta en un trabajador separado del USB,
el reconocimiento y la salida de voz. Usa el tiempo de espera configurado,
comprueba el plazo durante la lectura y limita el cuerpo de respuesta a
256 KiB y el texto final a 2000 caracteres. Una respuesta vacía o truncada
no se informa como éxito. Se cierra la conexión al terminar o fallar.

Los errores de autenticación, permisos, modelo no disponible, límites,
servicio remoto, conexión y tiempo de espera muestran mensajes que permiten
corregir la configuración o iniciar otra prueba. No desconectan el avatar.
Cambiar la configuración mientras hay una prueba pendiente descarta su
resultado; se podrá iniciar una nueva al terminar la anterior. Cerrar el
panel descarta el resultado y no bloquea Tk esperando la red; una operación
ya iniciada termina en el trabajador con su tiempo de espera y libera la conexión.

## Validación

`tests/pc/test_config.py` cubre precedencia del entorno, ausencia de clave,
valores inválidos, errores de lectura, ausencia de interpolación, mensajes sin
secretos y recarga del panel sin afectar los controles locales. Los tests usan
valores sintéticos y no necesitan credenciales ni acceso a Groq.

Validación del 27 de octubre de 2026: **129 pruebas aprobadas**, dependencias
comprobadas con `pip check` y reglas de Git verificadas. El usuario confirmó
la carga y recarga desde `.env` en la pestaña **IA**, sin mostrar la clave.
Esta confirmación corresponde a la configuración local, no a una llamada a la API.

La integración del cliente añade `tests/pc/test_groq_client.py`: verifica
solicitudes y errores HTTP con transporte simulado, límite de respuesta y
tiempo, ausencia de reintentos, ocultamiento de claves, continuidad de Tk/USB,
recarga de configuración y cierre. No usa la clave real en pruebas automáticas.

La identificación de consultas añade `tests/pc/test_queries.py` y amplía las
pruebas del detector: prioridad de comandos, activación obligatoria, consulta
manual y automática, filtrado por confianza y ausencia de solicitudes a Groq.
También cubre una activación más suave que el comando y la omisión del nombre
en la transcripción, que solo se admite si el audio previo lo verifica.

Tras estos cambios se aprobaron **151 pruebas**. Se verificaron consultas y
comandos con Vosk real, entrada sintética y COM3, sin llamadas a Groq. Además
se simuló la omisión del nombre en la transcripción conservando el audio real
de prueba: el verificador fonético recuperó la activación y siguió rechazando
las frases cuyo audio no contiene el nombre.
El usuario confirmó con su micrófono que «Aubar, contento» vuelve a ejecutar
el comando y responder con Dora, y que «Aubar, cómo estás» se identifica como
consulta después de la corrección del inicio de captura.

En captura manual, mantener pulsado el botón también activa las consultas:
se puede decir «contame algo interesante» sin el nombre. La escucha automática
mantiene la verificación de «Aubar». Una palabra mal transcrita como «ahogar»
no se agrega como alias ni se elimina de una consulta sin verificarla.
Este ajuste pasó **152 pruebas** y se comprobó con Vosk real y una captura
manual sintética desde el panel, sin consultas a Groq.
El usuario confirmó que «contame algo interesante» se identifica como consulta
al mantener pulsado el botón, sin decir el nombre.

Validación del cliente del 27 de octubre de 2026: **139 pruebas aprobadas**,
`pip check` correcto y una consulta real desde el panel usando la configuración
local. Se comprobó el funcionamiento de Tk y COM3 y que los controles de IA
entran en la ventana mínima de 760 × 650. El usuario confirmó la respuesta de
Groq y la continuidad del panel durante la consulta.

`tests/pc/test_conversation.py` cubre la construcción del contexto, los límites
por pares y caracteres, el reinicio durante una consulta, respuestas tardías
o duplicadas, errores y reintentos sin turnos fallidos, y la separación de la
prueba de conexión. También comprueba que las credenciales configuradas se
oculten en todo el cuerpo enviado a Groq.

La conversación pasó **161 pruebas** y una comprobación real con Groq:
retuvo un dato sintético en una pregunta de seguimiento y dejó de conocerlo
después de reiniciar. Los controles se comprobaron en una ventana de 760 × 650.
El usuario confirmó la conversación por texto, el recuerdo de un dato en una
pregunta de seguimiento, el borrado mediante **Nueva conversación** y la
visualización completa de los controles.

La integración de micrófono, IA y voz se validó con **172 pruebas aprobadas**
y `pip check` correcto. `tests/pc/test_voice_conversation.py` cubre una consulta
y una respuesta, contexto compartido, descarte del audio propio, recuperación
de escucha, silencio y detención durante la espera, errores, reinicios,
reconexión y reproducción compartida con el catálogo sin superposición.
Se probó con entrada sintética, Vosk/Groq/Dora reales y comandos en COM3.
El usuario confirmó con su micrófono tanto la conversación manual y sus
seguimientos como el recorrido automático, la prioridad de los comandos y
el apagado del micrófono durante la respuesta.

Referencias: [configurar la clave en Groq](https://console.groq.com/docs/quickstart),
[modelos disponibles](https://console.groq.com/docs/models) y
[python-dotenv](https://github.com/theskumar/python-dotenv).
Referencia del cliente: [Chat completions](https://console.groq.com/docs/api-reference)
y [errores de Groq](https://console.groq.com/docs/errors).
