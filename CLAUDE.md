# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mourafiq (مرافق)** is an AI-powered assistive device for visually impaired users in Morocco, running on a Raspberry Pi 4. It combines real-time object detection, OCR, GPS navigation, and voice interaction, responding entirely in Moroccan Darija Arabic.

## Running the Application

```bash
source /home/som/projet_ia/bin/activate
cd ~/mourafiq
python3 main.py
```

The app requires physical hardware: PiCamera2, microphone, speaker/headphones, and an optional GPS module on `/dev/ttyS0`. It cannot run on a development machine.

Make permanent in `~/.bashrc`:
```bash
echo 'source /home/som/projet_ia/bin/activate' >> ~/.bashrc
echo 'export GROQ_API_KEY="gsk_..."' >> ~/.bashrc
source ~/.bashrc
```

> `assistant_ia.py` est déprécié — utiliser `main.py`.

## Dependencies

```bash
pip install -r requirements.txt
sudo apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra mpg123 python3-picamera2
git lfs pull   # for yolov8n.pt
```

## API — Groq (backend principal)

**Groq** remplace Google Gemini (quota `limit: 0` sur tous les modèles avec la clé `AQ.Ab8...`).

| Feature | Groq model | Free tier |
|---------|-----------|-----------|
| NLP / Darija | `llama-3.1-8b-instant` | 14 400 req/day, 30 RPM |
| Voice → Text | `whisper-large-v3-turbo` | 7 200 req/day |

Get a free API key at **console.groq.com** → API Keys. Format: `gsk_...`

## Architecture — Structure des fichiers

```
mourafiq/
├── main.py          # Point d'entrée — init matériel + threads
├── config.py        # Constantes (GROQ_API_KEY, ports, seuils, chemins)
├── state.py         # État partagé entre threads (locks, camera, model, groq_client)
├── audio.py         # parler(), suprimer_alsa(), calibrer_micro()
├── vision.py        # mode_vision() — boucle YOLO
├── conversation.py  # mode_conversation() — boucle micro
├── intents.py       # process_command() — routage commandes vocales
├── groq_service.py  # groq_darija() + reconnaitre_voix()
├── ocr_reader.py    # lire_texte() — Tesseract
├── gps.py           # init_gps(), get_gps(), naviguer()
├── translations.py  # dict YOLO COCO class → phrase darija
├── requirements.txt
├── models/          # yolov8n.pt (optionnel — sinon racine)
├── temp/            # audio.mp3, audio.wav (auto-créé par main.py)
└── logs/            # logs (auto-créé par main.py)
```

## Thread Synchronisation

Two daemon threads launched from `main.py`:

| Thread | Function | Description |
|--------|----------|-------------|
| Vision | `mode_vision()` | YOLO loop; announces objects in Darija via `parler()` |
| Conversation | `mode_conversation()` | VAD loop → Groq Whisper STT → `process_command()` |

| Primitive | Type | Purpose |
|-----------|------|---------|
| `camera_lock` | `threading.Lock` | Serialises all `camera.capture_array()` calls |
| `audio_lock` | `threading.Lock` | Serialises all `parler()` calls |
| `conversation_active` | `threading.Event` | **Pauses vision during audio playback only** — set/cleared inside `parler()`. Vision runs freely during mic listening. |

## Key Functions

- **`parler(texte)`** in `audio.py` — sets `conversation_active`, edge-tts (ar-MA-JamalNeural) → fallback gTTS → mpg123; protected by `audio_lock`; clears `conversation_active` after playback
- **`groq_darija(question)`** in `groq_service.py` — `llama-3.1-8b-instant`, 3 retries with exponential backoff
- **`reconnaitre_voix()`** in `groq_service.py` — PyAudio VAD → WAV → `whisper-large-v3-turbo`; **30s timeout** if no voice detected
- **`process_command(commande)`** in `intents.py` — command router; returns `False` to stop the conversation loop
- **`lire_texte()`** in `ocr_reader.py` — camera capture → Pytesseract (`ara+fra`) → `groq_darija()` narration
- **`get_gps()`** in `gps.py` — reads NMEA from persistent serial connection `state.gps_serial`
- **`calibrer_micro()`** in `audio.py` — measures ambient noise at startup, sets `VOL_SEUIL = max(150, ambient×3)`
- **`suprimer_alsa()`** in `audio.py` — context manager that redirects stderr to suppress ALSA/JACK noise

## Configuration Constants (config.py)

| Constant | Default | Purpose |
|----------|---------|---------|
| `GROQ_API_KEY` | `os.environ["GROQ_API_KEY"]` | Never hardcode |
| `GPS_PORT` | `/dev/ttyS0` | Serial port for GPS |
| `CONF_SEUIL` | `0.50` | YOLO confidence threshold (was 0.60 — test 0.45 if missing objects) |
| `EDGE_VOICE` | `ar-MA-JamalNeural` | Microsoft edge-tts voice |
| `TIMEOUT_ECOUTE` | `≈468 chunks (30s)` | Mic listening timeout |
| `MODEL_PATH` | auto | Checks `models/yolov8n.pt` then `yolov8n.pt` at root |
| `VOL_SEUIL` | auto-calibrated | Set at startup in `state.py` |

## Object Dictionary

`translations.py` maps YOLO COCO class names → Darija strings. Add entries here for new object classes.

## Audio / Bluetooth Setup (Raspberry Pi)

The Pi uses **PipeWire** as its audio system (Raspberry Pi OS Trixie).

**Bluetooth headphones (oraimo SpaceBuds Air — MAC `28:52:E0:23:61:6F`):**
```bash
bluetoothctl connect 28:52:E0:23:61:6F
pactl set-default-sink $(pactl list sinks short | grep bluez | awk '{print $2}')
```

**If Bluetooth sink doesn't appear** after reboot:
```bash
systemctl --user start wireplumber pipewire pipewire-pulse
bluetoothctl connect 28:52:E0:23:61:6F
```

Note: HUAWEI FreeBuds SE 3 (MAC `70:40:FF:6E:21:7E`) failed to provide an audio sink via PipeWire. oraimo SpaceBuds Air worked immediately.

## Free/Cheap API Alternatives

| Need | Best Free | Cheap paid |
|------|-----------|------------|
| NLP (Darija) | **Groq** `llama-3.1-8b-instant` — 14 400/day | Gemini 1.5 Flash $0.075/1M tokens |
| STT (Arabic) | **Groq** `whisper-large-v3-turbo` — 7 200/day | OpenAI Whisper $0.006/min |
| TTS (Arabic) | **edge-tts** `ar-MA-JamalNeural` free + fallback gTTS | ElevenLabs $5/mo (very natural) |
| Object detection | **YOLOv8n** local — free forever | — |
| OCR | **Tesseract** local — free forever | — |

**Gemini status:** New `AQ.Ab8...` key format returns `limit: 0` on all models. Avoid.

## Fixes Applied (2026-06-13)

| Fix | Description | File |
|-----|-------------|------|
| `conversation_active` | Moved into `parler()` only — vision free during mic listening | `audio.py` |
| `edge-tts` | `ar-MA-JamalNeural` with automatic `gTTS` fallback | `audio.py` |
| `CONF_SEUIL` | `0.60` → `0.50` (test `0.45` if still missing objects) | `config.py` |
| Mic timeout | 30s without voice → automatic return, no infinite block | `groq_service.py` |
| Refactoring | `assistant_ia.py` split into 11 modules | all files |

## Known Non-Issues

ALSA/JACK spam at startup is suppressed by `suprimer_alsa()` in `audio.py` around PyAudio init.

The `Picamera2.close()` traceback on `KeyboardInterrupt` is a known PiCamera2 bug — does not affect functionality.

## Import Chain (no circular dependencies)

```
config → (stdlib only)
translations → (nothing)
state → threading
audio → config, state
groq_service → config, state, audio
vision → config, translations, state, audio
ocr_reader → state, audio, groq_service
gps → config, state, audio, groq_service
intents → state, audio, groq_service, ocr_reader, gps
conversation → state, groq_service, intents
main → config, state, audio, vision, conversation, gps
```
