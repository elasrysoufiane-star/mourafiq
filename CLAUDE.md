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
│   │   ├── groq_client.py          # groq_darija() — llama-3.1-8b-instant
│   │   └── claude_client.py        # claude_darija() + claude_describe_scene() — VLM
│   ├── providers/
│   │   ├── ai.py                   # get_ai_response() — routage groq/claude/openai
│   │   ├── stt.py                  # transcribe() — routage groq/openai
│   │   ├── tts.py                  # synthesize() — routage edge/gtts/elevenlabs
│   │   └── vision_ai.py            # describe_scene() — routage local(YOLO)/claude
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
config.settings ──────────────────────────────┐ (stdlib + dotenv seulement)
src.vision.translations ──────────────────────┤ (rien)
src.core.state ───────────────────────────────┤ (threading seulement)
src.providers.tts    ◄── config               │
src.providers.stt    ◄── config  (state lazy) │
src.providers.ai     ◄── config  (groq_client / claude_client lazy)
src.providers.vision_ai ◄── config, core.state, providers.ai  (claude_client lazy)
src.audio.speaker    ◄── core.state  (providers.tts lazy dans _jouer_tts)
src.ai.groq_client   ◄── core.state           │
src.ai.claude_client ◄── config  (anthropic + PIL lazy)
src.audio.listener   ◄── config, core.state, audio.speaker  (providers.stt lazy dans _transcrire)
src.vision.detector  ◄── config, core.state, audio.speaker, vision.translations
src.ocr.reader       ◄── core.state, audio.speaker, providers.ai
src.gps.location     ◄── config, core.state, audio.speaker, providers.ai
src.conversation.intents ◄── core.state, audio.speaker, providers.ai, providers.vision_ai, ocr.reader, gps.location
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

## API — Claude (Anthropic, optionnel — cerveau vision à la demande)

| Feature | Modèle défaut | Prix /1M (in/out) |
|---------|---------------|-------------------|
| Description de scène (VLM) | `claude-haiku-4-5` | $1 / $5 |
| Qualité max (option) | `claude-opus-4-8` | $5 / $25 |

Clé sur **console.anthropic.com** → API Keys (format `sk-ant-...`). Vide = fallback local/Groq automatique.

**Architecture hybride (économie de tokens) :** YOLO local tourne en continu (gratuit, 0 token). Claude n'est appelé QUE sur intention vocale (`شنو قدامي؟`). Leviers : appel à la demande, image redimensionnée à 768px + JPEG q70, `max_tokens=150`, cooldown anti double-appel, Haiku par défaut. Usage (in/cache_read/out) loggé à chaque appel. Le marqueur de prompt caching est présent mais n'aide que si le prompt système dépasse le minimum cacheable du modèle.

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

- **`parler(texte)`** in `src/audio/speaker.py` — sets `conversation_active`, délègue à `providers.tts.synthesize()`
- **`reconnaitre_voix()`** in `src/audio/listener.py` — PyAudio VAD → WAV → `providers.stt.transcribe()`; **timeout 8s**
- **`get_ai_response(question)`** in `src/providers/ai.py` — routage vers `groq_darija()` / `claude_darija()` / openai
- **`groq_darija(question)`** in `src/ai/groq_client.py` — LLaMA, 3 retries backoff (implémentation)
- **`describe_scene(image, question)`** in `src/providers/vision_ai.py` — routage VLM (claude) ou fallback YOLO local + cooldown
- **`claude_describe_scene(image, q)`** in `src/ai/claude_client.py` — Claude multimodal, image downscalée, usage loggé
- **`process_command(commande)`** in `src/conversation/intents.py` — retourne `False` pour arrêt
- **`mode_conversation()`** in `src/conversation/commands.py` — boucle écoute + mot de réveil « مرافق » + fenêtre de suivi (`WAKE_FOLLOWUP_WINDOW`)
- **`contient_wake(commande)` / `retirer_wake(commande)`** in `src/conversation/intents.py` — détection/retrait du mot de réveil
- **`calibrer_micro()`** in `src/audio/listener.py` — mesure bruit ambiant → `VOL_SEUIL`
- **`suprimer_alsa()`** in `src/audio/listener.py` — contextmanager stderr redirect

## Providers (src/providers/)

Couche de routage — configurer via `.env` (défaut = tout gratuit).

| Variable | Défaut | Options | Fichier |
|----------|--------|---------|---------|
| `AI_PROVIDER` | `groq` | `groq`, `claude`, `openai`* | `src/providers/ai.py` |
| `STT_PROVIDER` | `groq` | `groq`, `openai`* | `src/providers/stt.py` |
| `TTS_PROVIDER` | `edge` | `edge`, `gtts`, `elevenlabs` | `src/providers/tts.py` |
| `VISION_AI_PROVIDER` | `local` | `local`, `claude` | `src/providers/vision_ai.py` |

*options futures — structure prête, fallback automatique vers groq si clé absente.
`claude` (AI + vision) : payant, fallback automatique vers groq/local si `ANTHROPIC_API_KEY` absente.

**Règles :**
1. Mode par défaut = gratuit (`groq` + `edge`). Ne jamais changer les défauts dans le code.
2. Si clé payante absente → message clair + fallback gratuit automatique, jamais d'exception non gérée.
3. YOLO, Tesseract OCR et GPS restent toujours locaux — jamais de provider cloud pour ces composants.
4. `src/providers/` = routage uniquement. Implémentations dans leurs modules d'origine.
5. Imports providers en lazy (dans `_jouer_tts` / `_transcrire`) — rester testable sur Windows sans matériel.

## Configuration (config/settings.py)

| Constante | Défaut | Rôle |
|-----------|--------|------|
| `GROQ_API_KEY` | `os.environ.get(...)` | Vide si absent (erreur levée dans app.init()) |
| `CONF_SEUIL` | `0.50` | Seuil confiance YOLO (tester 0.45 si détection insuffisante) |
| `EDGE_VOICE` | `ar-MA-JamalNeural` | Voix edge-tts |
| `TIMEOUT_ECOUTE` | `≈125 chunks (8s)` | Timeout micro |
| `MODEL_PATH` | `models/yolov8n.pt` | Chemin modèle YOLO |
| `GPS_PORT` | `/dev/ttyS0` | Port série GPS |
| `AI_PROVIDER` | `groq` | Provider NLP (groq / claude / openai) |
| `STT_PROVIDER` | `groq` | Provider STT (groq / openai) |
| `TTS_PROVIDER` | `edge` | Provider TTS (edge / gtts / elevenlabs) |
| `VISION_AI_PROVIDER` | `local` | Provider scène VLM (local YOLO / claude) |
| `ELEVENLABS_API_KEY` | `""` | Clé ElevenLabs (vide = fallback edge) |
| `OPENAI_API_KEY` | `""` | Clé OpenAI (non utilisé par défaut) |
| `ANTHROPIC_API_KEY` | `""` | Clé Claude (vide = fallback groq/local) |
| `CLAUDE_VISION_MODEL` | `claude-haiku-4-5` | Modèle VLM (opus-4-8 pour qualité max) |
| `CLAUDE_MAX_TOKENS` | `150` | Plafond réponse (parlée → courte) |
| `CLAUDE_IMG_MAX_PX` | `768` | Taille max image avant envoi (tokens) |
| `VISION_COOLDOWN` | `3` | Anti double-appel scène (secondes) |
| `WAKE_WORD_ENABLED` | `1` | Mot de réveil « مرافق » requis (0 = écoute continue) |
| `WAKE_FOLLOWUP_WINDOW` | `15` | Fenêtre de suivi après réveil/commande (secondes) |

## Imports matériels — lazy loading

`Picamera2`, `YOLO`, `Groq` sont importés à l'intérieur de `app.init()`, pas au niveau module.
`anthropic` et `PIL` sont importés en lazy dans `src/ai/claude_client.py` (jamais au niveau module).
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
python3 tests/test_providers.py
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
| Providers | `src/providers/` — AI/STT/TTS configurables via `.env` | `src/providers/` |
| python-dotenv | Chargement automatique de `.env` au démarrage | `config/settings.py` |

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
