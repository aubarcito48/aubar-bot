# Eficiencia de Groq en Aubar

Se adaptan las prácticas evaluadas en StitchWeather: medición, reutilización
acotada y control de solicitudes. ECC no se instala ni se agrega como dependencia.
El modelo, los prompts, el razonamiento y los límites de salida se conservan.
El director predeterminado sigue siendo Groq; `AUBAR_DIRECTOR=local` sigue siendo
un piloto opcional independiente de esta mejora.

## Cambios del panel de PC

- Caché RAM de hasta 64 resultados de etapas válidas, con vigencia de 300 segundos.
  La clave incluye todo el payload efectivo: historial, mensaje, instrucciones,
  modelo, temperatura, razonamiento y esquema. Está separada por credencial
  mediante HMAC con un secreto aleatorio de sesión. No se guarda la clave API
  dentro de las claves de caché ni se escriben conversaciones en disco.
- Se reutilizan contenido y dirección por separado. Si la dirección falla,
  el texto aprobado se conserva y un reintento idéntico puede reutilizarlo.
  Una dirección inválida o que reescribe palabras no se almacena. El director
  local, cuando se elige, vuelve a ejecutarse localmente sobre el texto.
- Nueva conversación, recarga y cierre vacían la caché. Una generación impide
  que un resultado pendiente vuelva a llenarla después del reinicio.
- Ante HTTP 429 se respeta `Retry-After` numérico, o 30 segundos si falta o no
  es válido; se acota entre 1 segundo y 24 horas. La espera es por credencial,
  incluso cambiando de modelo. Reiniciar conversación no la elude. Las respuestas
  que ya están en caché pueden usarse durante esa espera sin solicitar a Groq.
- No se agregan reintentos automáticos. Sigue existiendo un solo trabajador y
  no se encolan conversaciones. «Probar conexión» siempre hace una consulta real,
  salvo una espera de límite activa: no obtiene una falsa confirmación de caché.
- La pestaña IA muestra intentos de proveedor, tokens informados, cantidad de
  respuestas con información de uso y reutilizaciones locales. Solo se acumulan
  números en RAM: no prompts, claves ni cuerpos de errores. Se contabiliza
  `usage` incluso si luego falla la validación del contenido. Sin `usage` válido,
  el consumo es desconocido y no se estima como cero. Los totales son parciales
  si hay respuestas sin uso; no equivalen a dólares ni a un límite de gasto.
- También se registran tokens de entrada cacheados por Groq cuando vienen en
  `usage.prompt_tokens_details.cached_tokens`; se distinguen de la caché local.

Las funciones locales, el reconocimiento, Kokoro/Onyx y el protocolo ESP32
no cambian. No hay que volver a cargar firmware ni configurar Render.
No se copian límites por visitante de una web pública: Aubar funciona en el PC.

## Alcance del ahorro y verificación

Pruebas de transporte simulado verifican que dos solicitudes idénticas completas
usan **2 llamadas en total** con director Groq: ambas etapas de la primera y cero
de la repetición. Sin reutilización serían 4. Con director local opcional son
**1 y 0**, y la dirección local se vuelve a calcular en ambas.

Esto demuestra llamadas evitadas en ese escenario, no un porcentaje de ahorro
en conversaciones reales. Después de una respuesta completada cambia el historial:
repetir la pregunta allí requiere otra respuesta y no reutiliza la anterior.
No se efectuaron llamadas de pago para esta verificación. Se preservaron los
prompts para no atribuir ahorros a un cambio no evaluado de calidad.

Las pruebas cubren vencimiento, capacidad, separación de contexto/modelo/clave,
reinicio durante solicitudes pendientes, cancelación, uso ausente, errores,
espera por límite y presentación de métricas. Ejecutar desde la raíz:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests/pc -q
```

Referencias de las prácticas y compatibilidad del proveedor:

- [ECC: patrones cost-aware](https://github.com/affaan-m/ECC/blob/main/skills/cost-aware-llm-pipeline/SKILL.md).
- [Groq: caché nativa de prefijos](https://console.groq.com/docs/prompt-caching).
- [Groq: límites y Retry-After](https://console.groq.com/docs/rate-limits).

No se copian las APIs de caché de otros proveedores: la caché nativa de Groq
es automática en los modelos compatibles y su presencia no se garantiza.
