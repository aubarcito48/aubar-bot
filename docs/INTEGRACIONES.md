# Aubar: portfolio y WhatsApp

El código Node del puente se versiona en `integrations/whatsapp-bot` junto al
panel para que el clon del repositorio incluya ambos extremos. La instancia
local previa sigue en `portfolio/whatsapp-bot`, con su configuración y sesión
privadas intactas. No ejecutar dos procesos con el mismo puerto o sesión.
Para una instalación nueva, usar `integrations/whatsapp-bot`, ejecutar `npm ci`
y preparar su `.env` desde `.env.example`. No copiar ni versionar credenciales
de WhatsApp. El emparejador usa el `.env` del puente incluido si existe; en este
workspace conserva el del proyecto hermano mientras no se prepare el nuevo.

El panel actual de Python consulta el portfolio, envía mensajes explícitos y
notifica mensajes nuevos de WhatsApp. La interfaz web y las agendas quedan
para etapas posteriores.

## Portfolio: datos publicados, una sola generación de texto

Aubar consulta directamente los GET públicos existentes de Django:
`perfil/`, `proyectos/`, `experiencias/`, `formacion/`, `tecnologias/` y `enlaces/`.
No llama al chat del portfolio, no abre una segunda generación en Groq y no
accede al Admin, a la base, a borradores ni a los archivos privados del backend.

Un selector local por palabras identifica las secciones necesarias, con un
máximo de tres por pregunta. Reconoce algunas continuaciones cortas del tema
anterior. Es un enrutador inicial, no un intérprete universal: una consulta sin
esas referencias puede no activar fuentes. Los saludos no disparan solicitudes.
Una consulta general sobre el portfolio recupera perfil y proyectos. El perfil
publicado identifica a Nahuel cuando la pregunta no señala otra persona.
Se pide la traducción inglesa cuando el selector identifica términos ingleses;
Groq conserva su capacidad de responder en español e inglés.

Los datos se adjuntan exclusivamente a la generación de contenido. El director
de gestos recibe el diálogo y el texto aprobado; no vuelve a recibir toda la API.
Las referencias no se agregan al historial visible ni se comparten con WhatsApp.
El contenido externo está identificado como datos, con una instrucción superior
para no seguir órdenes contenidas allí y reconocer referencias incompletas o fallidas.

Se excluyen imágenes y campos ajenos al contrato público. No se abren enlaces
de los datos ni se siguen redirecciones o URLs de paginación. Si una lista tiene
más páginas, se marca explícitamente como parcial.

## WhatsApp: estado, envío explícito y notificaciones

El bot Node de `portfolio/whatsapp-bot` ya expone `GET /health`:

- HTTP 200, `status=connected`: la conexión del bot está activa.
- HTTP 503 con un estado reconocido: el servicio respondió, pero WhatsApp aún
  no está conectado; puede estar esperando el QR, conectándose o detenido.
- Sin respuesta o contrato inválido: el estado no se pudo verificar. Eso no
  demuestra por sí solo que el bot esté apagado.

El nuevo puente autenticado admite `POST /control/send`, `GET /control/events`
y `GET /control/inbox`.
Solo funciona desde loopback y exige un token privado compartido; rechaza
solicitudes de navegador con Origin. No habilita un envío público por Internet.
Se mantienen los números de `TEST_CONTACTS`, mensajes privados y texto; no se
agregan grupos, medios, lectura de conversaciones históricas ni agendas.

Para enviar, el dueño debe pedirlo explícitamente con número internacional y
texto: «enviá un WhatsApp a +549XXXXXXXXXX: Hola». El analizador local conserva
las palabras y genera un UUID por pedido. No interpreta nombres como números ni
elige destinatarios. Los formatos incompletos piden el número y el texto; no
se entregan a Groq para inventar una ejecución. El modelo no tiene una herramienta
de envío: sus respuestas, los datos del portfolio y los mensajes recibidos no
pueden disparar un envío. Tampoco se transmite una consulta al chat del portfolio.

El puente guarda UUID, hash de destinatario/texto y estado en
`.data/desktop-sends.sqlite`; no guarda el mensaje ni el teléfono en esa tabla.
El mismo UUID y contenido no se envían dos veces, incluso tras reiniciar Node;
si cambia el contenido se rechaza. Un intento pendiente o ambiguo no se reenvía.
No hay reintentos automáticos. Cancelar la espera, cerrar el panel o iniciar una
conversación nueva **no retira un mensaje ya transmitido**. Una respuesta aceptada
no acredita entrega ni lectura. Ante un resultado incierto, revisar WhatsApp
antes de iniciar otro pedido (que tendrá otro UUID). La tabla admite hasta
10.000 intentos; si se llena, falla antes de transmitir. Un envío activo a la vez
y hasta cinco nuevos por minuto limitan el control manual.

La pestaña **WhatsApp** muestra mensajes nuevos de los contactos habilitados,
incluidos los que aún no activaron el chat del portfolio con `/aubar`. Puede
leerlos con Onyx: «Te llegó un mensaje de [nombre]: [texto]». Sin nombre se usa
la terminación del número. Las notificaciones no pasan por Groq ni por el
historial de conversación. La lectura respeta la voz desactivada y espera a que
no haya otra respuesta, captura o reproducción en curso; se puede desactivar con
su casilla. Silenciar o detener la voz descarta avisos de audio pendientes.

«Mostrá mis mensajes de WhatsApp» o «leé mis mensajes de WhatsApp» consulta
localmente los mensajes que aún conserva el puente. Resume la presentación a
los últimos tres, conservando el texto (con marca si se recorta). Tampoco llama
a Groq ni evalúa el contenido como órdenes. No consulta mensajes antiguos del teléfono.
Los pedidos locales y sus resultados quedan en la pestaña WhatsApp, fuera del
historial que se envía a Groq en preguntas posteriores; consultar la bandeja
no filtra esos mensajes al continuar una conversación general.

El puente retiene hasta 100 eventos nuevos durante cinco minutos en RAM y
deduplica IDs. El panel consulta cada tres segundos (diez tras una falla),
recibe hasta 20 eventos por consulta y conserva hasta 100 mensajes visibles
en RAM. La cola de voz retiene como máximo 10 avisos durante 60 segundos.
Una sesión nueva comienza desde el momento de conexión: no reproduce el
historial anterior. Si vence la ventana o se reinicia el puente, el panel avisa
que puede faltar información. No garantiza avisos de todos los mensajes si
el panel o el bot estuvieron apagados. Los historiales de ambos canales siguen
separados. La sesión, QR y credenciales de Baileys no se entregan al panel.

## Configuración y uso

En el `.env` privado de Botbar:

```dotenv
AUBAR_PORTFOLIO_API_URL=https://portfolio-backend-6ecn.onrender.com/api/v1/
AUBAR_SOURCES_TIMEOUT_SECONDS=60
AUBAR_WHATSAPP_HEALTH_URL=http://127.0.0.1:3000/health
AUBAR_WHATSAPP_CONTROL_URL=http://127.0.0.1:3000/control/
AUBAR_CONTROL_TOKEN=<token privado compartido con whatsapp-bot>
```

Estas direcciones no son secretos. Se agregaron a la configuración local sin
cambiar las claves existentes. Un valor vacío desactiva esa fuente.
La API exige HTTPS salvo loopback; el endpoint de WhatsApp solo admite loopback.
No se envían claves de Groq a estas fuentes. Solo las rutas `/control/` reciben
el token de control en Authorization; el portfolio y `/health` no reciben claves.

La configuración local ya quedó vinculada con un token aleatorio, sin mostrarlo
ni cambiar claves de API o de sesión. Para repetir el emparejamiento en este
workspace, con ambos `.env` existentes:

```powershell
.\.venv\Scripts\python.exe tools/configure_whatsapp_bridge.py
```

El script conserva un token válido existente y no sobrescribe dos tokens
contradictorios. No versionar `.env`, sesiones ni las bases SQLite.

Reiniciar el panel para cargar el código nuevo. En cambios posteriores de URL,
«Recargar configuración» también vacía las cachés. Ejemplos de consultas:

- «¿Qué proyectos tiene mi portfolio?»
- «¿Qué tecnologías tengo publicadas?»
- «Contame mi experiencia y formación.»
- «¿Cuál es el estado de mi bot de WhatsApp?»

Para comprobar WhatsApp, su proceso debe estar iniciado por su procedimiento
habitual (`npm start` desde `portfolio/whatsapp-bot`, con su `.env` y contactos
de prueba configurados). Aubar no lo inicia automáticamente, ya que ese proceso
puede contestar mensajes entrantes de los contactos habilitados.

## Límites y pruebas

Las lecturas se ejecutan en el trabajador de IA, fuera del hilo Tk. Comparten
un presupuesto independiente de 60 segundos para permitir el inicio del backend
gratuito, configurable con `AUBAR_SOURCES_TIMEOUT_SECONDS` entre 1 y 90.
La conexión inicial del portfolio tiene hasta diez segundos; la espera de
respuesta usa el presupuesto restante. El health local usa hasta tres segundos
por operación. DNS y la conexión inicial dependen también del sistema operativo.
La cancelación interrumpe sockets conectados y se comprueba entre operaciones.
Después de leer las fuentes comienza el timeout de generación de Groq, sin
consumirlo esperando Render. El tiempo total puede sumar ambos presupuestos.
El panel muestra el estado de las fuentes mientras trabaja.

Máximo 128 KiB por respuesta y 14.000 caracteres de contexto. Datos públicos
válidos se cachean 60 segundos; las fallas esperan 10 segundos antes de volver a
consultar esa URL. WhatsApp se consulta de nuevo en cada solicitud exitosa.
Nueva conversación, recarga y cierre descartan estas cachés. No hay reintentos
automáticos ni archivos con datos recuperados. Una fuente no disponible se
identifica como tal, sin entregar respuestas anteriores como si fueran actuales.

Render puede estar dormido: la primera pregunta puede demorar hasta ese
presupuesto. Si todas las fuentes necesarias fallan, una respuesta local informa
el problema de conexión sin llamar a Groq ni afirmar que no existe información
sobre Nahuel. Una falla se conserva diez segundos para evitar solicitudes
repetidas; volver a consultar luego es una acción del usuario.

Verificación real del 17/11/2026, sin llamar a Groq: perfil disponible,
4 proyectos, 27 tecnologías, 3 experiencias, 2 formaciones y 4 enlaces.
WhatsApp no respondió en el endpoint local configurado y sigue pendiente de
verificar con el proceso real del bot iniciado. No se enviaron mensajes reales.
Sí pasó una prueba Python → HTTP → Node con transporte simulado: notificación,
token, conservación literal del texto e idempotencia, sin WhatsApp ni Groq.

Corrección del acceso al portfolio: se reprodujeron las preguntas «conta sobre
nahuel» y «contame sobre el portfolio de nahuel argandoña». El límite anterior
de cuatro segundos interrumpía la primera lectura y cacheaba la falla; además,
esa falla podía convertirse en una respuesta de desconocimiento del modelo.
Una prueba real tras la corrección recuperó perfil y proyectos y obtuvo de Groq
una descripción con PintaEbook, DGES, StitchWeather y Aubar Bot, incluso después
de una respuesta previa que preguntaba a qué Nahuel se refería el usuario.

Pruebas simuladas cubren selección de fuentes, contrato GET sin autenticación,
contexto de generación, exclusión del director y del historial, URLs permitidas,
estados HTTP 503 válidos, datos parciales, fechas, ausencia de seguimiento de
enlaces, tamaño, vencimiento, cancelación y presupuesto. Se ejecutan con:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests/pc -p test_connected_sources.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests/pc -p test_whatsapp_control.py -v
.\.venv\Scripts\python.exe tools/check_whatsapp_integration.py
```

El último script usa el puente incluido en `integrations/whatsapp-bot` y Node
24. Arranca y cierra únicamente un fixture local en un puerto efímero; nunca
importa Baileys ni abre la sesión real. Las pruebas de Node se ejecutan con
`npm test` desde el directorio del puente y también usan transportes simulados.
