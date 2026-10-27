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
Los comandos de voz, Dora y el control USB siguen disponibles; esta prueba
todavía no incorpora conversación por micrófono, historial ni voz de la IA.

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

Validación del cliente del 27 de octubre de 2026: **139 pruebas aprobadas**,
`pip check` correcto y una consulta real desde el panel usando la configuración
local. Se comprobó el funcionamiento de Tk y COM3 y que los controles de IA
entran en la ventana mínima de 760 × 650. El usuario confirmó la respuesta de
Groq y la continuidad del panel durante la consulta.

Referencias: [configurar la clave en Groq](https://console.groq.com/docs/quickstart),
[modelos disponibles](https://console.groq.com/docs/models) y
[python-dotenv](https://github.com/theskumar/python-dotenv).
Referencia del cliente: [Chat completions](https://console.groq.com/docs/api-reference)
y [errores de Groq](https://console.groq.com/docs/errors).
