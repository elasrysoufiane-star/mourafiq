# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Assistant IA pour Malvoyants — Maroc** is an AI-powered assistive device for visually impaired users in Morocco, running on a Raspberry Pi 4. It combines real-time object detection, OCR, GPS navigation, and voice interaction, responding entirely in Moroccan Darija Arabic.

## Running the Application

```bash
source /home/som/projet_ia/bin/activate
cd ~/morafiq
python3 assistant_ia.py
```

The app requires physical hardware: PiCamera2, microphone, speaker/headphones, and an optional GPS module on `/dev/ttyS0`. It cannot run on a development machine.

Make permanent in `~/.bashrc`:
```bash
echo 'source /home/som/projet_ia/bin/activate' >> ~/.bashrc
echo 'export GROQ_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

## Dependencies

```bash
pip install ultralytics picamera2 pytesseract pyaudio pyserial pynmea2 gtts edge-tts groq pillow numpy
sudo apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra mpg123
git lfs pull   # for yolov8n.pt
```

> `pygame` removed — replaced by `mpg123` CLI for reliable Bluetooth audio playback.  
> `edge-tts` added as primary TTS — `gTTS` kept as automatic fallback.

## API — Groq (primary, replaces Gemini)

**Groq** is the current AI backend. It replaced Google Gemini due to persistent `limit: 0` quota issues with the new `AQ.Ab8...` Gemini key format.

| Feature | Groq model | Free tier |
|---------|-----------|-----------|
| NLP / Darija | `llama-3.1-8b-instant` | 14,400 req/day, 30 RPM |
| Voice → Text | `whisper-large-v3-turbo` | 7,200 req/day |

Get a free API key at **console.groq.com** → API Keys.

```bash
export GROQ_API_KEY="gsk_..."
```

The Groq key format is `gsk_...` — no upload/delete cycle needed for audio (sent directly as bytes).

## Architecture

Two daemon threads launched from `__main__`:

| Thread | Function | Description |
|--------|----------|-------------|
| Vision | `mode_vision()` | Continuous YOLO loop; announces detected objects in Darija via `parler()` |
| Conversation | `mode_conversation()` | VAD loop → Groq Whisper STT → command router |

### Thread Synchronisation

| Primitive | Type | Purpose |
|-----------|------|---------|
| `camera_lock` | `threading.Lock` | Serialises all `camera.capture_array()` calls |
| `audio_lock` | `threading.Lock` | Serialises all `parler()` calls |
| `conversation_active` | `threading.Event` | Pauses vision **during audio playback only** — set/cleared inside `parler()`. Vision runs freely during mic listening. |

### Key Functions

- **`parler(texte)`** — `edge-tts` (primary, `ar-MA-JamalNeural`) → fallback `gTTS` → MP3 → `mpg123`; protected by `audio_lock`; sets/clears `conversation_active` around playback only
- **`groq_darija(question)`** — `llama-3.1-8b-instant` with system prompt enforcing single-sentence Moroccan Darija
- **`reconnaitre_voix()`** — PyAudio VAD → WAV → `whisper-large-v3-turbo` transcription; timeout 30s si aucune voix détectée
- **`lire_texte()`** — camera capture → Pytesseract (`ara+fra`) → `groq_darija()` narration
- **`get_gps()`** — reads NMEA from persistent serial connection `gps_serial`
- **`naviguer(destination)`** — GPS + `groq_darija()` for turn-by-turn guidance
- **`calibrer_micro()`** — measures ambient noise at startup, sets `VOL_SEUIL = max(150, ambient×3)`
- **`suprimer_alsa()`** — context manager that redirects stderr to suppress ALSA/JACK noise

### Configuration Constants

| Constant | Default | Purpose |
|----------|---------|---------|
| `GROQ_API_KEY` | `os.environ["GROQ_API_KEY"]` | Never hardcode |
| `GPS_PORT` | `/dev/ttyS0` | Serial port for GPS |
| `CONF_SEUIL` | `0.50` | YOLO confidence threshold (was 0.60 — test 0.45 if still missing objects) |
| `VOL_SEUIL` | auto-calibrated | Set at startup from ambient noise measurement |

### Object Dictionary

`traductions` maps YOLO COCO class names → Darija strings. Add entries here for new object classes.

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
pactl list sinks short
```

Note: HUAWEI FreeBuds SE 3 (MAC `70:40:FF:6E:21:7E`) failed to provide an audio sink via PipeWire. oraimo SpaceBuds Air worked immediately.

## Free/Cheap API Alternatives

| Need | Best Free | Cheap paid |
|------|-----------|------------|
| NLP (Darija) | **Groq** `llama-3.1-8b-instant` — 14,400/day | Gemini 1.5 Flash $0.075/1M tokens |
| STT (Arabic) | **Groq** `whisper-large-v3-turbo` — 7,200/day | OpenAI Whisper $0.006/min |
| TTS (Arabic) | **edge-tts** `ar-MA-JamalNeural` free (Microsoft) + fallback gTTS | ElevenLabs $5/mo (voix très naturelle) |
| Object detection | **YOLOv8n** local — free forever | — |
| OCR | **Tesseract** local — free forever | — |

**Gemini status:** New `AQ.Ab8...` key format returns `limit: 0` on `gemini-2.0-flash` and `gemini-2.0-flash-lite`. `gemini-1.5-flash` returns 404. Avoid until quota issue is resolved. If needed, use a personal Gmail account (not Workspace) on aistudio.google.com.

## Fixes Applied (2026-06-13)

| Fix | Description | Statut |
|-----|-------------|--------|
| `conversation_active` | Déplacé dans `parler()` — vision libre pendant l'écoute micro | ✅ Appliqué |
| `edge-tts` | Voix `ar-MA-JamalNeural` avec fallback automatique `gTTS` | ✅ Appliqué |
| `CONF_SEUIL` | `0.60` → `0.50` (tester `0.45` si trop d'objets ratés) | ✅ Appliqué |
| Timeout micro | 30s sans voix → retour automatique, évite blocage infini | ✅ Appliqué |

## Known Non-Issues

ALSA/JACK spam at startup is suppressed by `suprimer_alsa()` context manager around PyAudio init. These are harmless enumeration errors.

The `Picamera2.close()` traceback on `KeyboardInterrupt` is a known PiCamera2 bug — does not affect functionality.
