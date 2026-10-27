# Configuración de Groq

La configuración se prepara localmente. Esta etapa no realiza solicitudes a
Groq ni comprueba que una clave sea válida ante el servicio.

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

## Validación

`tests/pc/test_config.py` cubre precedencia del entorno, ausencia de clave,
valores inválidos, errores de lectura, ausencia de interpolación, mensajes sin
secretos y recarga del panel sin afectar los controles locales. Los tests usan
valores sintéticos y no necesitan credenciales ni acceso a Groq.

Validación del 27 de octubre de 2026: **129 pruebas aprobadas**, dependencias
comprobadas con `pip check` y reglas de Git verificadas. El usuario confirmó
la carga y recarga desde `.env` en la pestaña **IA**, sin mostrar la clave.
Esta confirmación corresponde a la configuración local, no a una llamada a la API.

Referencias: [configurar la clave en Groq](https://console.groq.com/docs/quickstart),
[modelos disponibles](https://console.groq.com/docs/models) y
[python-dotenv](https://github.com/theskumar/python-dotenv).
