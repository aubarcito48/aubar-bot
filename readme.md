# Aubar Bot

Asistente de escritorio con ESP32-S3, retrato animado, reconocimiento local con
Whisper small y voz Kokoro/Onyx. Integra conversaciones con Groq, consultas al
portfolio, YouTube y el puente de WhatsApp.

## Iniciar

Desde la ra?z del proyecto, con Python 3.11 o superior:

```powershell
.\tools\start_control.ps1
```

El lanzador prepara el entorno y los modelos cuando faltan. Las credenciales se
configuran en `.env` a partir de `.env.example` y permanecen fuera de Git.

El puente de WhatsApp requiere Node.js 24 y su propia configuraci?n local:

```powershell
cd integrations\whatsapp-bot
npm ci
npm start
```

## Organizaci?n

- `pc/aubar_control/ui/`: panel de escritorio.
- `pc/aubar_control/config/`: configuraci?n; `paths.py` fija la ra?z del proyecto.
- `pc/aubar_control/models/avatar/`: cat?logo y respuestas del avatar.
- `pc/aubar_control/services/`: audio, reconocimiento, voz y asistente/director.
- `pc/aubar_control/device/`: protocolo y conexi?n USB.
- `pc/aubar_control/integrations/`: portfolio, WhatsApp y YouTube.
- `firmware/KirbyPantalla/src/`: avatar, animaciones, retrato y USB. El sketch,
  el controlador de pantalla y el banco binario conservan su ubicaci?n de compilaci?n.
- `integrations/whatsapp-bot/src/`: configuraci?n, servicios y almacenamiento del puente.
- `assets/`: fuentes del retrato, cat?logo original y fotograf?as del dispositivo.
- `tools/`: instalaci?n, generaci?n de recursos y configuraci?n de integraciones.
- `models/`: modelos locales, excluidos de Git.

El firmware se abre con `firmware/KirbyPantalla/KirbyPantalla.ino`. Al mover el
checkout se actualiza la ruta del banco de im?genes, sin regenerarlo:

```powershell
.\.venv\Scripts\python.exe tools\avatar\generate_portrait_firmware.py --paths-only
```

Los recursos y modelos conservan las licencias incluidas en sus archivos y descargas.
