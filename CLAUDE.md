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

The app requires physical hardware: PiCamera2, microphone, speaker/headphones, and an optional GPS module on `/dev/ttyS0`. It cannot run on a development machine without mocking.

```bash
echo 'export GROQ_API_KEY="gsk_..."' >> ~/.bashrc && source ~/.bashrc
```

## Dependencies

```bash
pip install -r requirements.txt
sudo apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra mpg123 python3-picamera2
git lfs pull   # models/yolov8n.pt
```

## Architecture — Structure des fichiers

```
mourafiq/
├── main.py                         # Point d'entrée minimal → src.core.app.main()
├── config/
│   ├── __init__.py
│   └── settings.py                 # Toutes les constantes de configuration
├── src/
│   ├── core/
│   │   ├── state.py                # Locks, events, objets matériels partagés
│   │   └── app.py                  # init() + main() — hardware lazy-loaded
│   ├── audio/
│   │   ├── speaker.py              # parler(), suprimer_alsa(), calibrer_micro()
│   │   └── listener.py             # reconnaitre_voix(), _transcrire()
│   ├── vision/
│   │   ├── detector.py             # mode_vision() — boucle YOLO
│   │   └── translations.py         # Dict YOLO COCO → phrases darija
│   ├── ocr/
│   │   └── reader.py               # lire_texte() — Tesseract ara+fra
│   ├── gps/
│   │   └── location.py             # init_gps(), get_gps(), naviguer()
│   ├── ai/
│   │   └── groq_client.py          # groq_darija() — llama-3.1-8b-instant
│   └── conversation/
│       ├── intents.py              # KEYWORDS_* + process_command()
│       └── commands.py             # mode_conversation() — thread écoute
├── models/
│   └── yolov8n.pt                  # Git LFS
├── tests/
│   ├── test_config.py
│   ├── test_translations.py
│   └── test_intents.py
├── temp/                           # audio.mp3, audio.wav (auto-créé)
└── logs/                           # Logs runtime (auto-créé)
```

## Import Chain (aucun import circulaire)

```
config.settings ──────────────────────────────┐ (stdlib seulement)
src.vision.translations ──────────────────────┤ (rien)
src.core.state ───────────────────────────────┤ (threading seulement)
src.audio.speaker    ◄── config, core.state   │
src.ai.groq_client   ◄── core.state           │
src.audio.listener   ◄── config, core.state, audio.speaker
src.vision.detector  ◄── config, core.state, audio.speaker, vision.translations
src.ocr.reader       ◄── core.state, audio.speaker, ai.groq_client
src.gps.location     ◄── config, core.state, audio.speaker, ai.groq_client
src.conversation.intents ◄── core.state, audio.speaker, ai.groq_client, ocr.reader, gps.location
src.conversation.commands ◄── core.state, audio.listener, conversation.intents
src.core.app         ◄── config, core.state, audio.speaker, audio.listener,
                          vision.detector, conversation.commands, gps.location
main.py              ◄── core.app
```

## API — Groq (backend principal)

| Feature | Modèle | Quota gratuit |
|---------|--------|---------------|
| NLP / Darija | `llama-3.1-8b-instant` | 14 400 req/jour |
| STT Arabe | `whisper-large-v3-turbo` | 7 200 req/jour |

Clé sur **console.groq.com** → API Keys (format `gsk_...`)

## Thread Synchronisation

| Thread | Fonction | Fichier |
|--------|----------|---------|
| Vision | `mode_vision()` | `src/vision/detector.py` |
| Conversation | `mode_conversation()` | `src/conversation/commands.py` |

| Primitive | Type | Rôle |
|-----------|------|------|
| `camera_lock` | `Lock` | Sérialise `camera.capture_array()` |
| `audio_lock` | `Lock` | Sérialise `parler()` |
| `conversation_active` | `Event` | **Pause vision pendant audio seulement** — géré dans `speaker.parler()` uniquement |

## Key Functions

- **`parler(texte)`** in `src/audio/speaker.py` — sets `conversation_active`, edge-tts (`ar-MA-JamalNeural`) → fallback gTTS → mpg123
- **`reconnaitre_voix()`** in `src/audio/listener.py` — PyAudio VAD → WAV → Whisper; **timeout 30s**
- **`groq_darija(question)`** in `src/ai/groq_client.py` — LLaMA, 3 retries backoff
- **`process_command(commande)`** in `src/conversation/intents.py` — retourne `False` pour arrêt
- **`calibrer_micro()`** in `src/audio/speaker.py` — mesure bruit ambiant → `VOL_SEUIL`
- **`suprimer_alsa()`** in `src/audio/speaker.py` — contextmanager stderr redirect

## Configuration (config/settings.py)

| Constante | Défaut | Rôle |
|-----------|--------|------|
| `GROQ_API_KEY` | `os.environ.get(...)` | Vide si absent (erreur levée dans app.init()) |
| `CONF_SEUIL` | `0.50` | Seuil confiance YOLO (tester 0.45 si détection insuffisante) |
| `EDGE_VOICE` | `ar-MA-JamalNeural` | Voix edge-tts |
| `TIMEOUT_ECOUTE` | `≈468 chunks (30s)` | Timeout micro |
| `MODEL_PATH` | `models/yolov8n.pt` | Chemin modèle YOLO |
| `GPS_PORT` | `/dev/ttyS0` | Port série GPS |

## Imports matériels — lazy loading

`Picamera2`, `YOLO`, `Groq` sont importés à l'intérieur de `app.init()`, pas au niveau module.
Cela permet d'importer `config`, `src.vision.translations`, `src.conversation.intents` etc.
sur Windows pour les tests, sans lever d'erreur d'import matériel.

## Audio / Bluetooth (Raspberry Pi)

PipeWire (Raspberry Pi OS Trixie). Écouteurs : **oraimo SpaceBuds Air** MAC `28:52:E0:23:61:6F`

```bash
bluetoothctl connect 28:52:E0:23:61:6F
pactl set-default-sink $(pactl list sinks short | grep bluez | awk '{print $2}')
```

HUAWEI FreeBuds SE 3 (`70:40:FF:6E:21:7E`) : échec PipeWire — ne pas utiliser.

## Tests

```bash
# Depuis la racine du projet, fonctionne sur Windows sans Pi
python3 tests/test_config.py
python3 tests/test_translations.py
python3 tests/test_intents.py
# ou
pytest tests/ -v
```

## Fixes Appliqués (2026-06-13)

| Fix | Description | Fichier |
|-----|-------------|---------|
| `conversation_active` | Uniquement dans `parler()` — vision libre pendant écoute | `src/audio/speaker.py` |
| edge-tts | `ar-MA-JamalNeural` + fallback gTTS automatique | `src/audio/speaker.py` |
| `CONF_SEUIL` | `0.60` → `0.50` | `config/settings.py` |
| Timeout micro | 30s sans voix → retour automatique | `src/audio/listener.py` |
| Lazy imports | Picamera2/YOLO/Groq importés dans `init()` seulement | `src/core/app.py` |
| Refactoring src/ | 10 modules plats → structure `src/` + `config/` | tous |
| models/ | `yolov8n.pt` déplacé via `git mv` | `models/yolov8n.pt` |

## Known Non-Issues

- ALSA/JACK spam supprimé par `suprimer_alsa()` dans `src/audio/speaker.py`
- Traceback `Picamera2.close()` sur Ctrl+C : bug connu PiCamera2, pas fonctionnel

## Free/Cheap API Alternatives

| Besoin | Gratuit | Payant |
|--------|---------|--------|
| NLP Darija | **Groq** `llama-3.1-8b-instant` | Gemini 1.5 Flash $0.075/1M |
| STT Arabe | **Groq** `whisper-large-v3-turbo` | OpenAI Whisper $0.006/min |
| TTS Arabe | **edge-tts** + fallback gTTS | ElevenLabs $5/mo |
| Détection | **YOLOv8n** local | — |
| OCR | **Tesseract** local | — |
