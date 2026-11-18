# Reconocimiento local con Whisper

La captura y enumeración del micrófono siguen usando `sounddevice`. La detección
de inicio y fin de frase sigue usando el segmentador propio. Whisper
cambia solo el reconocimiento que convierte PCM en texto, no Groq, Kokoro,
las animaciones ni el firmware ESP32.

## Arranque

Whisper es el único reconocedor del panel, tras la prueba del usuario con su voz.
Vosk y su instalador se retiraron del proyecto. El paquete y los modelos locales
quedaron pendientes de limpieza: la revisión automática bloqueó su borrado. No existe selector
`AUBAR_STT_ENGINE` ni retorno automático al motor anterior.

Cerrar el panel y abrirlo con `tools/start_control.ps1`. El lanzador prepara
las dependencias y verifica los archivos locales. La pestaña Micrófono muestra
el motor activo. Recargar Groq no reinicia el reconocedor.

## Whisper local

- `faster-whisper==1.2.1`, CTranslate2 4.9.0 y PyAV 19.0.2.
- Whisper **small multilingüe**, forzado a español, transcripción y CPU int8.
- Cuatro hilos, un trabajador y modelo conservado en memoria durante la sesión.
- Aproximadamente 486 MB de archivos, fijados por revisión y SHA-256. Solo el
  instalador descarga; el reconocedor exige archivos locales completos y válidos.
- No se instala CUDA ni se usa la Radeon. Las mediciones se hicieron en el
  Ryzen 7 5700X del equipo, con 16 GB de RAM total.
- VAD de la biblioteca para filtrar silencios, temperaturas sin muestreo y sin
  contexto de una frase anterior. Sin prompt que fuerce palabras ni corrección
  de nombres por parecido: un nombre dudoso no se reemplaza automáticamente.
- PyAV remuestrea entradas distintas de 16 kHz, con filtrado de audio.
- Se preserva el contrato existente `RecognitionResult`: texto, gesto, YouTube
  o consulta. Ni el benchmark ni el reconocedor ejecutan las acciones.

Hay filtros por probabilidad, ausencia de voz, repetición y longitud. Las órdenes
requieren evidencia mayor que las consultas; esto puede rechazar una orden cuyo
texto parezca correcto. Los umbrales son iniciales y las probabilidades no son
comparables directamente con las de Vosk. No es una autenticación de hablante
ni una garantía de que nunca se transcriba audio incorrectamente.

## Resultado histórico de la comparación del 18/11/2026

Se procesaron cinco WAVs locales de pruebas anteriores, de 2,1 a 3 segundos,
en procesos separados para liberar cada modelo antes de cargar el siguiente.
No se grabó el micrófono ni se envió audio a servicios externos.

| Muestra | Vosk | Whisper |
| --- | --- | --- |
| pregunta-como | «ver cómo estás» | «¡Aubar, cómo estás!» |
| pregunta-contame | «aubert contame algo interesante» | «¡Aubar, contame algo interesante!» |
| pregunta-negada | «no te pongas contento» | «¡Aubar, no te pongas contento!» |
| combinado-enojado | «ayudar enojado derecha» | «audar enojado derecha» |
| youtube-search-direct | «busca en youtube videos de gatos» | «Busca en YouTube videos de gatos.» |

En la última muestra Whisper rechazó ejecutar la orden por el filtro de
confianza, aunque el texto coincide con la frase esperable. En la cuarta ambos
siguen teniendo problemas con el nombre. Se conserva la negación de la tercera:
no se transforma en la orden positiva «contento».

Vosk cargó en 26,226 s y transcribió en 0,471–1,199 s. Whisper cargó en 1,714 s
y transcribió en 1,593–1,886 s. Son observaciones de esta tanda, no garantías de
latencia. Whisper procesa cada frase más lentamente en esta comparación.

No hay referencias humanas auditadas ni un conjunto nuevo de voz del usuario;
por eso no se presenta un porcentaje de precisión o mejora general. La prueba
pendiente es comparar el texto mostrado en Micrófono con lo que realmente
pronuncia el dueño en frases nuevas, incluyendo nombres, números, negaciones
y ruido ambiente. La ventana máxima de captura sigue siendo diez segundos.

Informe histórico ignorado por Git: `tmp/asr-comparison/report.json`. Para probar Whisper con
WAVs explícitos mono PCM16 de hasta doce segundos:

```powershell
.\.venv\Scripts\python.exe tools/probe_recognition.py ruta/a.wav ruta/b.wav
```

El comando no transmite audio ni ejecuta comandos reconocidos. Los textos del
informe quedan localmente; no versionar grabaciones o transcripciones privadas.

Referencias:
- [faster-whisper y opciones CPU](https://github.com/SYSTRAN/faster-whisper).
- [Modelo y revisión fijada](https://huggingface.co/Systran/faster-whisper-small/tree/536b0662742c02347bc0e980a01041f333bce120).
