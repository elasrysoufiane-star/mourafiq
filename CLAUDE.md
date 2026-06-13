# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Assistant IA pour Malvoyants — Maroc** is an AI-powered assistive device for visually impaired users in Morocco, running on a Raspberry Pi 4. It combines real-time object detection, OCR, GPS navigation, and voice interaction, responding entirely in Moroccan Darija Arabic.

## Running the Application

```bash
# Activate the virtualenv first (Pi path)
source /home/som/projet_ia/bin/activate

# Set the API key if not already in ~/.bashrc
export GEMINI_API_KEY="AQ.Ab8RN6..."

# Run
python3 assistant_ia.py
```

The app requires physical hardware: PiCamera2, microphone, speaker, and an optional GPS module on `/dev/ttyS0`. It cannot run on a development machine.

To make the venv and API key permanent on the Pi:
```bash
echo 'source /home/som/projet_ia/bin/activate' >> ~/.bashrc
echo 'export GEMINI_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

## Dependencies

Install inside the virtualenv on the Raspberry Pi:

```bash
pip install ultralytics picamera2 pytesseract pyaudio pyserial pynmea2 gtts pygame google-genai pillow numpy
```

> **Note:** The package is `google-genai` (new SDK), NOT `google-generativeai` (deprecated).

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

### Thread Synchronisation

Three primitives prevent race conditions between the two threads:

| Primitive | Type | Purpose |
|-----------|------|---------|
| `camera_lock` | `threading.Lock` | Serialises all `camera.capture_array()` calls |
| `audio_lock` | `threading.Lock` | Serialises all `parler()` calls (single pygame channel) |
| `conversation_active` | `threading.Event` | Vision thread sleeps while the user is speaking |

### Key Functions

- **`parler(texte)`** — gTTS → MP3 → pygame playback for Arabic TTS; protected by `audio_lock`
- **`gemini_darija(question)`** — calls `gemini-1.5-flash` via `client.models.generate_content()` with a system prompt constraining replies to single-sentence Moroccan Darija
- **`reconnaitre_voix()`** — PyAudio VAD loop; writes captured speech to `/tmp/audio.wav`, uploads via `client.files.upload()`, transcribes with Gemini multimodal, then deletes the remote file
- **`lire_texte()`** — captures frame under `camera_lock`, runs Pytesseract (`ara+fra`), passes result to `gemini_darija()` for Darija narration
- **`get_gps()`** — reads NMEA sentences from the serial GPS module, returns `(lat, lon)`
- **`naviguer(destination)`** — combines GPS coordinates with `gemini_darija()` to give turn-by-turn guidance

### Configuration Constants (top of `assistant_ia.py`)

| Constant | Default | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` | `os.environ["GEMINI_API_KEY"]` | Read from environment — never hardcode |
| `GPS_PORT` | `/dev/ttyS0` | Serial port for GPS module |
| `GPS_BAUD` | `9600` | GPS baud rate |
| `CONF_SEUIL` | `0.60` | YOLO confidence threshold for announcements |
| `VOL_SEUIL` | `200` | Microphone volume threshold for VAD (calibrated for Pi USB mic) |

### Object Dictionary

`traductions` maps YOLO COCO class names → Darija announcement strings. Add entries here to support additional object classes.

## Gemini API Notes

- **SDK:** Uses `google.genai` (new) via `from google import genai`. The old `google.generativeai` package is fully deprecated and incompatible with the new `AQ.Ab8...` key format.
- **Client:** `gemini = genai.Client(api_key=GEMINI_API_KEY)` — one global client, no `.configure()` call needed.
- **Model:** `gemini-1.5-flash` — chosen over `gemini-2.0-flash` to avoid free-tier quota exhaustion during testing.
- **Quota:** Free tier quotas are per-project and per-day. If you hit `429 RESOURCE_EXHAUSTED`, create a new API key in a new Google Cloud project on aistudio.google.com/apikey.
- **API key format:** New Gemini keys start with `AQ.Ab8RN6...` (not `AIzaSy...`). Both formats are valid depending on the project.
- **File cleanup:** Audio files uploaded via `client.files.upload()` are deleted immediately after transcription with `client.files.delete()`.

## Known Non-Issues (safe to ignore)

The following messages appear at every startup and are harmless — PyAudio enumerating non-existent audio devices:

```
ALSA lib pcm.c:2722 Unknown PCM cards.pcm.*
Cannot connect to server socket ... jack server is not running
JackShmReadWritePtr::~JackShmReadWritePtr - Init not done for -1
```

To suppress them, redirect stderr when launching:
```bash
python3 assistant_ia.py 2>/dev/null
```

## Suggested Improvements

- **Retry on quota error:** Wrap `gemini_darija()` and `reconnaitre_voix()` with exponential backoff for `429` errors instead of silently returning empty string.
- **Startup audio check:** Call `arecord -l` at startup and warn if no input device is found, instead of failing silently later.
- **GPS serial port:** Open the serial port once at startup (not per-call in `get_gps()`) to avoid repeated open/close overhead.
- **ALSA noise suppression:** Add `2>/dev/null` or configure `/etc/asound.conf` to suppress PyAudio enumeration spam.
- **VAD calibration:** Print live volume in first 2 seconds at startup to auto-detect ambient noise and set `VOL_SEUIL` dynamically.
