# Aubar · microservicio de WhatsApp

Proyecto Node.js separado del frontend y del backend del portfolio. La primera
etapa se ejecuta en la PC para pruebas con contactos elegidos; después se puede
mover el mismo servicio al servidor propio.

```text
WhatsApp → Baileys / Node.js → POST /api/v1/chat/ en Render → Aubar / MCP / Groq
```

Node no consulta directamente la base del portfolio ni necesita otra clave de
Groq. Usa el contrato existente de Django: `mensaje`, `historial`, `idioma` →
`respuesta`. No modifica ni sustituye la integración Meta existente.

## Arquitectura y responsabilidades

El bot es un **microservicio independiente**, organizado por módulos. Mantiene
su propio proceso y se comunica con Django mediante HTTP y JSON. Puede compartir
repositorio y servidor con el frontend y el backend, conservando su ejecución
separada: reiniciar Django no requiere cerrar la vinculación de WhatsApp.

```text
WhatsApp
   ↕
Baileys / microservicio Node.js
   ↕ HTTP / JSON
Backend Django en Render
   ├── Datos públicos del portfolio mediante MCP
   └── Groq: generación de respuestas

Tarjetas de tecnologías y estadísticas:
Node.js → API pública de tecnologías + Shields + proveedores del README → PNG
```

Node.js recibe y filtra los mensajes, administra el menú y el historial temporal,
consulta la API y entrega texto o imágenes. Django mantiene las reglas de Aubar,
el acceso a los datos publicados y la integración con Groq. El microservicio no
accede directamente a la base de datos del portfolio ni almacena claves de Groq.
Las tarjetas se generan sin pasar por el modelo.

Actualmente el recorrido es **PC → Internet → Django en Render → Groq**. En el
servidor propio se puede cambiar `PORTFOLIO_API_URL` por una dirección interna,
por ejemplo `http://localhost:8000/api/v1/chat/` si ambos procesos comparten el
host. El validador actual permite HTTP solo en loopback; usar un nombre de servicio
Docker por HTTP requeriría adaptar esa validación. La red interna evita el viaje
público entre Node y Django. Mantener Django encendido evita la espera de arranque
por hibernación; las consultas a Groq y a las tarjetas externas siguen usando
Internet. No hace falta fusionar ambos procesos para obtener estas ventajas.

### Tecnologías y librerías

Versiones declaradas en `package.json`; `package-lock.json` fija la instalación.

| Tecnología / librería | Versión | Uso |
| --- | --- | --- |
| Node.js | 24.x | Ejecución del microservicio |
| JavaScript con módulos ES | — | Código del bot, mediante `import` y `export` |
| `@whiskeysockets/baileys` | 7.0.0-rc14 | Conexión no oficial a WhatsApp Web mediante QR, recepción y envío |
| `node:sqlite` | Incluido en Node.js | Persistencia de credenciales y claves de vinculación |
| `sharp` | 0.35.5 | Renderizado y composición de tarjetas SVG en PNG |
| `qrcode-terminal` | 0.12.0 | Visualización del QR en la terminal |
| `pino` | 9.14.0 | Logger de la conexión, configurado en silencio para no exponer identificadores ni claves |
| `fetch` y `AbortController` | Nativos de Node.js | Consultas HTTP, límites de espera y cancelación |
| `node:http` | Incluido en Node.js | Estado `/health` y puente de escritorio autenticado `/control/` |
| `node:test` y `node:assert` | Incluidos en Node.js | Pruebas automatizadas sin enviar mensajes reales |
| Dockerfile | Base Node.js 24 | Preparación para el futuro servidor; despliegue aún pendiente de validar |

No se utiliza Express: el pequeño endpoint de estado usa el servidor HTTP nativo.
La configuración `.env` también se carga con Node, mediante
`--env-file-if-exists=.env`, sin una dependencia adicional de dotenv.

### Organización del código y almacenamiento

| Módulo | Responsabilidad |
| --- | --- |
| `src/index.js` | Inicio, composición de servicios, health y apagado ordenado |
| `src/config.js` | Lectura y validación de configuración |
| `src/whatsapp.js` | Conexión, reconexión, cola y envío de mensajes o imágenes |
| `src/incoming.js` | Filtro de contactos, mensajes privados e identificación del remitente |
| `src/conversation.js` | Activación, contexto, idioma, límites y desactivación |
| `src/menu.js` | Secciones del portfolio y traducción de opciones a consultas |
| `src/portfolio-client.js` | Contrato HTTP con Django y manejo de errores |
| `src/whatsapp-text.js` | Conversión de tablas Markdown a bloques legibles |
| `src/auth-store.js` | Persistencia de la sesión de WhatsApp en SQLite |
| `src/desktop-control.js` | Puente local autenticado, eventos entrantes y recibos de envío explícito |
| `src/technology-cards.js` | Consulta de fuentes, caché y generación de imágenes |
| `src/readme-cards.json` | Estilos de badges y URLs públicas de estadísticas |
| `test/` | Pruebas del contrato, conversación, transporte, persistencia y tarjetas |

SQLite guarda **credenciales y claves de WhatsApp**, no conversaciones. El
historial queda en memoria, con caducidad y tamaño limitado, y se pierde al
reiniciar el proceso. La caché de tarjetas también es temporal. `.env`, las
credenciales, las copias de sesión y las vistas previas están excluidas de Git.

El control opcional del escritorio usa además `desktop-sends.sqlite`: guarda
UUID, hash y estado para no duplicar un envío, sin guardar teléfono ni texto.
Los eventos de notificación son temporales en RAM; no se guardan conversaciones.

## Límites de esta etapa

- Baileys conecta por WhatsApp Web sin Chromium. Es una biblioteca no oficial,
  sin garantía de continuidad ni de que WhatsApp no restrinja la cuenta. Usar
  un número de prueba; esto no resuelve el alta en la API oficial de Meta.
- Solo responde a números incluidos en `TEST_CONTACTS`. No hay modo público.
- Solo acepta texto en conversaciones privadas nuevas; ignora grupos, estados,
  canales, mensajes propios, medios y sincronización histórica.
- Primero requiere `/aubar`, `/aubar en` o la frase completa del enlace del
  portfolio. Otros mensajes de contactos inactivos se ignoran.
- `SALIR`, `STOP`, `HUMANO`, `HUMAN` desactivan la sesión y descartan respuestas
  pendientes. No garantizan una respuesta personal de Nahuel; el aviso del
  escritorio depende de que el puente y el panel estén conectados.
- Conversaciones en memoria por 30 minutos de inactividad, hasta 100 sesiones,
  historial máximo de 8 mensajes / 6000 caracteres. No se guarda texto en SQLite.
- Procesa hasta 5 mensajes por contacto y 8 consultas a Render por minuto; una
  consulta a la vez, cola de hasta 20 mensajes, deduplicación acotada y descarte
  de mensajes de más de 5 minutos. Los límites de la API web siguen compartidos.
- La PC y el proceso deben permanecer encendidos. Al cerrar el proceso deja de
  responder, pero no cierra la sesión vinculada en WhatsApp.
- No cobra una suscripción por la biblioteca. Render, Groq, conexión a Internet
  y el futuro servidor conservan sus límites y posibles costos propios.

## Inicio en Windows

Requiere **Node.js 24**. Desde `portfolio/whatsapp-bot`:

```powershell
npm ci
Copy-Item .env.example .env
```

Si `.env` ya existe, conservá el archivo. Editá `TEST_CONTACTS` con los números
que van a escribirle al bot durante las pruebas, en formato internacional,
solo dígitos, separados por comas. No pongas `+`, espacios ni guiones.
El contacto de prueba debe ser otro número diferente del número vinculado.
Si la lista está vacía, el programa no conecta WhatsApp.

Primero se puede comprobar todo sin vincular ningún teléfono:

```powershell
npm test
npm run demo
```

En la demo, escribí `/aubar`, una pregunta, `SALIR` y luego `/fin` para terminar.
Es una simulación sin red ni WhatsApp. Para verificar el backend real:

```powershell
npm run check:api
npm run demo:api
```

Estos dos últimos comandos envían preguntas a la API de Render/Groq. Render
puede estar dormido: el timeout es de 90 segundos, configurable hasta 120.
No se reintenta una consulta automáticamente ni se repite un envío fallido.

## Vincular WhatsApp cuando se decida probar

Con `.env` y `TEST_CONTACTS` configurados:

```powershell
npm start
```

1. En el teléfono del bot: **WhatsApp → Dispositivos vinculados → Vincular un dispositivo**.
2. Escanear el QR de la terminal privada. No compartir el QR ni publicarlo en logs.
3. Desde otro número incluido en `TEST_CONTACTS`, mandar `/aubar` o:

   `Hola Nahuel, vi tu portfolio y me gustaría contactarte.`

4. Preguntar por un proyecto publicado. El bot consulta la API existente en Render.
5. Mandar `SALIR` y otra pregunta: debe confirmar la salida y quedar en silencio.
6. Probar un número fuera de la lista: no debe responder.
7. Parar con **Ctrl+C** y reiniciar. La vinculación se recupera de SQLite;
   la conversación debe activarse de nuevo.

No se inició una conexión real ni se vinculó un teléfono durante la preparación.
La prueba real de QR/envío/recepción queda pendiente hasta elegir los contactos.

Verificación local del 14/11/2026: 10 pruebas automatizadas aprobadas, demo de
activación/pregunta/salida sin red y una consulta real al endpoint público de
Render. Aubar respondió correctamente con el contrato `respuesta`. No se
modificó la base del portfolio ni se enviaron mensajes por WhatsApp.

## Persistencia y traslado al servidor propio

`AUTH_DIR` contiene `auth.sqlite`: credenciales y claves de la sesión de WhatsApp.
No son conversaciones, pero permiten usar la cuenta vinculada. La carpeta debe
ser privada y persistente, y no debe subirse a Git ni compartirse. Está ignorada
en `.gitignore` y excluida del contexto Docker. Un único proceso utiliza cada
archivo; SQLite toma un bloqueo exclusivo para impedir dos instancias.

Node 24 puede mostrar una advertencia de que `node:sqlite` es experimental.
Se usa el SQLite incluido en Node, sin compilar extensiones externas.

El `Dockerfile` está preparado para el futuro servidor: Node 24, usuario sin
privilegios y puerto de health. Requiere un volumen privado en `/app/.data`,
`TEST_CONTACTS` como variable y `SHOW_QR=false` después de vincular. Para enlazar
en el servidor, hacerlo desde una terminal privada con QR habilitado, no desde
logs públicos. No habilitar varias réplicas.

La sesión de SQLite se puede mover con el proceso detenido, conservando la
misma versión de Node/Baileys y permisos. Apagar la PC antes de arrancar la copia
en el servidor: no ejecutar ambas con la misma sesión. Si WhatsApp exige volver
a vincular, hacerlo manualmente; el programa nunca borra las credenciales para
forzar un nuevo QR ni llama a `logout` al detenerse.

`GET /health` devuelve únicamente el estado, sin números, QR ni secretos.
Devuelve 200 cuando está conectado y 503 mientras inicia o está desconectado.
Es local por defecto (`127.0.0.1:3000`); Docker usa `0.0.0.0`. Ajustar el tiempo de gracia de health durante la
vinculación inicial antes de configurar reinicios automáticos en un servidor.

## Puente con el panel Aubar de escritorio

Con `AUBAR_CONTROL_TOKEN` vacío, el control permanece desactivado. Un token
aleatorio de 64 caracteres hexadecimales, compartido solo con el `.env` de
Botbar, habilita estas rutas privadas:

- `GET /control/events?after=<cursor>`: hasta 20 eventos de texto nuevos por
  consulta. Primera conexión sin cursor comienza en el presente, sin historial.
- `GET /control/inbox`: hasta 20 mensajes que aún conserva la ventana temporal,
  para una consulta explícita del dueño, sin acceder al historial del teléfono.
- `POST /control/send`: JSON con `request_id` UUID v4, `recipient` internacional
  (solo dígitos) y `text` de hasta 2.000 caracteres. Se limita a `TEST_CONTACTS`.

Ambas exigen Authorization Bearer, origen de conexión loopback y ausencia de
Origin de navegador. No se admite control desde Internet aunque health esté
publicado por Docker. Los mensajes entrantes se notifican al dueño, pero nunca
se evalúan como órdenes del escritorio. No se exponen QR, sesión ni contactos.

Hasta 100 eventos se conservan cinco minutos en RAM; el panel puede mostrarlos
y leerlos con Onyx sin enviarlos a Groq. Reiniciar Node pierde esa ventana. El
cursor informa reinicios o eventos fuera de ventana; esto no es una bandeja
persistente ni reemplaza WhatsApp para consultar el historial completo.

El envío explícito conserva el texto y no usa Groq. Una sola operación simultánea,
hasta cinco intentos nuevos por minuto y un recibo persistente por UUID evitan
repeticiones del mismo pedido. Si se pierde la confirmación, queda `unknown`:
no se reintenta automáticamente. `accepted` no prueba entrega ni lectura.
Cancelar la espera del cliente no retira un mensaje transmitido. Un nuevo UUID
es un pedido nuevo; revisar WhatsApp antes de repetir un resultado ambiguo.
La tabla de recibos tiene un límite de 10.000 registros y falla antes de enviar
si se alcanza. No borrar recibos pendientes para forzar reintentos.

Reiniciar `npm start` después de configurar el token. No se inicia ni vincula
WhatsApp automáticamente desde Botbar. `npm test` verifica el puente con
transportes simulados y SQLite temporal, sin enviar mensajes reales.

## Conversación y presentación

### Tarjetas actualizadas de tecnologías y GitHub

La opción `5`, `Tecnologías` o `Technologies` envía dos PNG: tecnologías con
badges agrupados y estadísticas de GitHub (lenguajes, estadísticas generales y
racha). La lista se consulta en `/api/v1/tecnologias/`, recorriendo la paginación;
no se guarda una lista fija de habilidades ni se pide al modelo inventar cifras.
Los estilos de badges y las tres URLs de estadísticas se tomaron del README
local de `readme/aubarcito48`, en `src/readme-cards.json`. Hay estilos adicionales
para C++, Arduino y ESP32. Una tecnología nueva aparece automáticamente; si no
tiene un logo configurado o falla Shields, se muestra su nombre en un badge.

Al solicitar las tarjetas se consultan las fuentes públicas, con caché en memoria
de 15 minutos. Después de vencer, la siguiente solicitud vuelve a consultar;
no hay un cron ni cambios en imágenes enviadas anteriormente. Se indica la hora
de consulta en Argentina. Los proveedores de estadísticas tienen su propia
caché, por lo que esa hora no garantiza datos de GitHub en tiempo real. Si una
fuente falla no se reenvía una captura vencida: se informa la indisponibilidad.
Los porcentajes de lenguajes reflejan uso en repositorios, no nivel profesional.

La primera generación puede demorar por Render o los proveedores. Si falla el
envío de una imagen, se intenta enviar texto de respaldo. SALIR durante la carga
invalida las imágenes pendientes. Las consultas y las imágenes no contienen el
número de teléfono del visitante. Las tarjetas no pasan por Groq.

Sharp convierte los SVG a PNG y muestra el estado final de sus animaciones para
que las cifras no queden invisibles. Sus dependencias opcionales de plataforma
son necesarias también en Docker: instalar con `npm ci --omit=dev`.

Vista previa con datos reales, sin conectar WhatsApp ni enviar mensajes:

```powershell
node --env-file-if-exists=.env scripts/preview-cards.js
```

Las imágenes quedan en `tmp/cards-preview`. Se verificó la descarga real y se
inspeccionaron ambos PNG; la recepción en el teléfono se prueba reiniciando el
bot y seleccionando `5`. Esta función no requiere desplegar cambios en Render.

La bienvenida incluye un menú de seis secciones: Sobre Nahuel, Proyectos,
Experiencia, Educación, Tecnologías y Contacto. Se elige escribiendo un número
del 1 al 6 o el nombre de la sección; también se aceptan preguntas libres.
No son botones tocables: se usa texto compatible con el transporte actual.
Las opciones se traducen a consultas concretas contra la misma API pública.
Proyectos pide un bloque por proyecto, con descripción y URLs de demo y GitHub
solo cuando estén publicadas para ese proyecto. Tecnologías pide bloques por
categoría. Si el modelo devuelve una tabla Markdown, el cliente la transforma en
bloques con etiquetas y líneas en blanco antes de enviarla y guardarla en el
historial. No se agregan ni se adivinan enlaces ausentes en la respuesta.
El menú aparece automáticamente una sola vez por sesión; `MENÚ`, `MENU` o
`/menu` lo vuelven a mostrar a pedido, conservando el contexto reciente.
Después de SALIR hace falta activar nuevamente el bot antes de usar el menú.

El saludo se muestra en párrafos cortos y queda guardado como un turno real del
historial enviado a la API. Así Groq puede ver que Aubar ya se presentó antes de
responder la primera pregunta. Volver a enviar `/aubar` cambia el idioma y confirma
que la conversación sigue activa, sin repetir la bienvenida ni el menú, conservando
el contexto reciente dentro del límite de historial.

El prompt del backend pide responder directamente, usar voseo en español, resolver
referencias a preguntas anteriores y evitar repetir la presentación o los datos de
contacto en cada respuesta. Esta parte requiere desplegar el backend actualizado;
reiniciar solamente este servicio no actualiza el prompt de Render. El historial
es temporal, tiene límites y se pierde al detener el proceso o vencer la sesión.

Referencia revisada: [whatsapp-formatting de Microsoft](https://github.com/microsoft/amplifier-app-nanoclaw/blob/main/container/skills/whatsapp-formatting/SKILL.md).
Sus adaptadores y conversión automática pertenecen a ese proyecto; aquí no se
asume que Baileys convierte Markdown. Las respuestas siguen siendo texto simple,
con saltos de línea y listas breves cuando ayudan a leerlas en el teléfono.

Verificación de esta mejora: 11 pruebas del servicio Node y 5 pruebas del proveedor
del backend aprobadas. Comprueban el historial y el contrato, no garantizan cada
respuesta del modelo. Falta la prueba conversacional con el backend desplegado.

## Fuentes

- [Baileys](https://github.com/WhiskeySockets/Baileys), versión fijada en package-lock.json.
- [Guía de conexión y aviso de biblioteca no oficial](https://baileys.wiki/).
- [Contrato de Aubar](../portfolio_backend/docs/AUBAR.md).
- [Integración oficial ya existente](../portfolio_backend/docs/WHATSAPP.md).

El despliegue Docker y la vinculación real no se dan por verificados hasta
probarlos en ese entorno. Ninguno de los tests envía mensajes ni usa una base
de datos de producción.
