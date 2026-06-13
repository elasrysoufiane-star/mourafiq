# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Assistant IA pour Malvoyants — Maroc** is an AI-powered assistive device for visually impaired users in Morocco, running on a Raspberry Pi 4. It combines real-time object detection, OCR, GPS navigation, and voice interaction, responding entirely in Moroccan Darija Arabic.

## Running the Application

```bash
# On Raspberry Pi 4 only (requires physical hardware)
python assistant_ia.py
```

The app requires physical hardware: PiCamera2, microphone, speaker, and an optional GPS module on `/dev/ttyS0`. It cannot run on a development machine.

## Dependencies

Install on the Raspberry Pi:

```bash
pip install ultralytics picamera2 pytesseract pyaudio pyserial pynmea2 gtts pygame google-generativeai pillow numpy wave
```

Tesseract must also be installed system-wide with Arabic and French language packs:

```bash
sudo apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra
```

The YOLO model `yolov8n.pt` is stored via Git LFS — run `git lfs pull` after cloning.

## Architecture

The application runs two daemon threads launched from `__main__`:

| Thread | Function | Description |
|--------|----------|-------------|
| Vision | `mode_vision()` | Continuous YOLO object detection loop; announces newly-detected objects in Darija via `parler()` |
| Conversation | `mode_conversation()` | Listens for voice commands via `reconnaitre_voix()`, routes to appropriate handler |

### Key Functions

- **`parler(texte)`** — gTTS → MP3 → pygame playback for Arabic TTS output
- **`gemini_darija(question)`** — calls `gemini-2.0-flash` with a system prompt that constrains replies to single-sentence Moroccan Darija
- **`reconnaitre_voix()`** — PyAudio VAD loop writing to `/tmp/audio.wav`, then transcribes via Gemini's multimodal API
- **`lire_texte()`** — captures frame, runs Pytesseract (`ara+fra`), passes result to `gemini_darija()` for Darija narration
- **`get_gps()`** — reads NMEA sentences from the serial GPS module, returns `(lat, lon)`
- **`naviguer(destination)`** — combines GPS coordinates with `gemini_darija()` to give turn-by-turn guidance

### Configuration Constants (top of `assistant_ia.py`)

| Constant | Default | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` | hardcoded | Google Gemini API key — move to env var before sharing |
| `GPS_PORT` | `/dev/ttyS0` | Serial port for GPS module |
| `GPS_BAUD` | `9600` | GPS baud rate |
| `CONF_SEUIL` | `0.60` | YOLO confidence threshold for announcements |
| `VOL_SEUIL` | `500` | Microphone volume threshold for VAD |

### Object Dictionary

`traductions` maps YOLO COCO class names → Darija announcement strings. Add entries here to support additional object classes.

## Important Notes

- **GEMINI_API_KEY is hardcoded** in the source — do not commit a real key to a public repo; use an environment variable instead.
- The Vision thread sets a 3-second cooldown (`time.sleep(3)`) and tracks `dernier` to avoid repeating the same object announcement.
- Voice recognition uses Gemini's `upload_file` API for audio transcription — requires network access.
- GPS fix may require outdoor conditions; `get_gps()` polls up to 30 NMEA lines before giving up.
