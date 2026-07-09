# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mourafiq (مرافق)** is an AI-powered assistive device for visually impaired users in Morocco, running on a Raspberry Pi 4. It combines real-time object detection, OCR, and voice interaction, responding entirely in Moroccan Darija Arabic. (Le GPS a été retiré du projet le 2026-07-09 — ne pas le réintroduire.)

## Running the Application

```bash
source /home/som/projet_ia/bin/activate
cd ~/mourafiq
python3 main.py
```

The app requires physical hardware: PiCamera2, microphone, and speaker/headphones. It cannot run on a development machine without mocking.

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
│   ├── test_intents.py             # inclut mot de réveil (contient_wake/retirer_wake)
│   ├── test_providers.py           # routage AI/STT/TTS/vision + clés
│   └── smoke_claude_vision.py      # test isolé Claude vision (Pi ou image fixe)
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
src.conversation.intents ◄── core.state, audio.speaker, providers.ai, providers.vision_ai, ocr.reader
src.conversation.commands ◄── core.state, audio.listener, conversation.intents
src.core.app         ◄── config, core.state, audio.speaker, audio.listener,
                          vision.detector, conversation.commands
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

**Architecture hybride (économie de tokens) :** YOLO local tourne en continu (gratuit, 0 token). Claude n'est appelé que sur intention vocale (`شنو قدامي؟`) — **ou** périodiquement en mode sans micro si `VISION_AI_PROVIDER=claude` (voir `AUTO_DESCRIBE_INTERVAL`, coût continu). Leviers : appel à la demande, image redimensionnée à 768px + JPEG q70, `max_tokens=150`, cooldown anti double-appel, Haiku par défaut. Usage (in/cache_read/out) loggé à chaque appel. Le marqueur de prompt caching est présent mais n'aide que si le prompt système dépasse le minimum cacheable du modèle.

## Thread Synchronisation

| Thread | Fonction | Fichier |
|--------|----------|---------|
| Vision | `mode_vision()` | `src/vision/detector.py` |
| Conversation | `mode_conversation()` | `src/conversation/commands.py` |
| AutoScene (sans micro) | `mode_auto_scene()` | `src/vision/detector.py` |

Le thread **Conversation n'est lancé que si un micro est détecté** (`state.mic_ok`).
Sans micro → **mode vision seul** : `app.init()` met `mic_ok=False`, saute la calibration,
et `main()` ne démarre pas l'écoute (évite la boucle « En attente de voix → Timeout 8s »).
À la place, si `AUTO_DESCRIBE_INTERVAL > 0`, le thread **AutoScene** décrit la scène
toutes les N secondes (`describe_scene()` → `parler()`) — remplace la commande vocale
absente. Provider selon `VISION_AI_PROVIDER` (claude payant / local gratuit).

| Primitive | Type | Rôle |
|-----------|------|------|
| `camera_lock` | `Lock` | Sérialise `camera.capture_array()` |
| `audio_lock` | `Lock` | Sérialise `parler()` |
| `conversation_active` | `Event` | **Pause vision pendant audio seulement** — géré dans `speaker.parler()` uniquement |
| `mic_ok` | `bool` | Micro détecté au démarrage. `False` → thread conversation non lancé (vision seule) |

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
3. YOLO et Tesseract OCR restent toujours locaux — jamais de provider cloud pour ces composants.
4. `src/providers/` = routage uniquement. Implémentations dans leurs modules d'origine.
5. Imports providers en lazy (dans `_jouer_tts` / `_transcrire`) — rester testable sur Windows sans matériel.

## Configuration (config/settings.py)

| Constante | Défaut | Rôle |
|-----------|--------|------|
| `GROQ_API_KEY` | `os.environ.get(...)` | Vide si absent (erreur levée dans app.init()) |
| `DEMO_MODE` | `free` | `free` (logique normale) ou `demo` (documentation uniquement) |
| `CONF_SEUIL` | `0.50` | Seuil confiance YOLO (tester 0.45 si détection insuffisante) |
| `EDGE_VOICE` | `ar-MA-JamalNeural` | Voix edge-tts |
| `TIMEOUT_ECOUTE` | `≈125 chunks (8s)` | Timeout micro |
| `MODEL_PATH` | `models/yolov8n.pt` | Chemin modèle YOLO |
| `AI_PROVIDER` | `groq` | Provider NLP (groq / claude / openai) |
| `STT_PROVIDER` | `groq` | Provider STT (groq / openai) |
| `STT_MODEL` | `whisper-large-v3-turbo` | Modèle Whisper Groq (`whisper-large-v3` pour +précision) |
| `TTS_PROVIDER` | `edge` | Provider TTS (edge / gtts / elevenlabs) |
| `VISION_AI_PROVIDER` | `local` | Provider scène VLM (local YOLO / claude) |
| `ELEVENLABS_API_KEY` | `""` | Clé ElevenLabs (vide = fallback edge) |
| `ELEVENLABS_VOICE_ID` | `""` | Voice ID ElevenLabs (vide = voix par défaut Adam) |
| `OPENAI_API_KEY` | `""` | Clé OpenAI (non utilisé par défaut) |
| `ANTHROPIC_API_KEY` | `""` | Clé Claude (vide = fallback groq/local) |
| `CLAUDE_TEXT_MODEL` | `claude-haiku-4-5` | Modèle conversation darija (`claude_darija`) |
| `CLAUDE_VISION_MODEL` | `claude-haiku-4-5` | Modèle VLM (opus-4-8 pour qualité max) |
| `CLAUDE_MAX_TOKENS` | `150` | Plafond réponse (parlée → courte) |
| `CLAUDE_IMG_MAX_PX` | `768` | Taille max image avant envoi (tokens) |
| `CLAUDE_IMG_QUALITY` | `70` | Qualité JPEG image avant envoi (tokens) |
| `VISION_COOLDOWN` | `3` | Anti double-appel scène (secondes) |
| `AUTO_DESCRIBE_INTERVAL` | `5` | Description auto en mode sans micro (s ; 0 = désactivé). Claude si `VISION_AI_PROVIDER=claude` |
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

## Fixes & Features (2026-06-17) — branche `feat/claude-vision-assistant`

État courant après la session « Claude vision + fiabilité écoute ».

| Changement | Description | Fichiers |
|-----------|-------------|----------|
| Claude VLM | Description de scène à la demande (`describe_scene`), hybride YOLO local + Claude | `src/ai/claude_client.py`, `src/providers/vision_ai.py`, `src/conversation/intents.py` |
| Prompts séparés | `_VISION_SYSTEM_PROMPT` (scène) vs `_CHAT_SYSTEM_PROMPT` (conversation darija) | `src/ai/claude_client.py` |
| Mot de réveil | « مرافق » + fenêtre de suivi `WAKE_FOLLOWUP_WINDOW` ; `WAKE_WORD_ENABLED=0` = continu | `src/conversation/commands.py`, `intents.py`, `config/settings.py` |
| Anti-écho STT | Purge ~0.4s micro + attente fin parole + filtre captures trop courtes | `src/audio/listener.py` |
| Prompt Whisper | Liste de mots-clés retirée (Whisper la recrachait) → indice de langue court | `src/providers/stt.py` |
| `STT_MODEL` | Modèle Whisper configurable (`whisper-large-v3` pour +précision) | `config/settings.py`, `src/providers/stt.py` |
| Stop keyword | `سلام` (salut) → `سلامة` (adieu) : le salut n'arrête plus l'app | `src/conversation/intents.py` |
| Bienvenue | Phrase d'accueil « مرافق » annonçant les commandes clés | `src/core/app.py` |
| Log TTS | Affiche le moteur réel (edge/gtts/elevenlabs) | `src/providers/tts.py` |
| Mode vision seul | Sans micro : `init()` met `state.mic_ok=False`, saute la calibration, `main()` ne lance pas le thread conversation → plus de boucle « En attente de voix → Timeout 8s » | `src/core/app.py`, `src/core/state.py` |
| Description auto (sans micro) | Thread `mode_auto_scene()` : sans micro, décrit la scène toutes les `AUTO_DESCRIBE_INTERVAL`s (`describe_scene()`→`parler()`). Claude si `VISION_AI_PROVIDER=claude`, sinon YOLO+Groq gratuit. Respecte `conversation_active` + cooldown | `src/vision/detector.py`, `src/core/app.py`, `config/settings.py` |

**Limite connue (matérielle) :** micro+voix sur le même canal **Bluetooth HFP 8 kHz** (FreeBuds SE 3) → audio dégradé des deux côtés, écho résiduel et erreurs Whisper darija possibles. Correctif définitif = **micro USB séparé** (FreeBuds en sortie A2DP). Le mot de réveil compense côté fiabilité.

**Config « qualité max » (coût accepté), via `.env` uniquement :** `AI_PROVIDER=claude`, `VISION_AI_PROVIDER=claude`, `CLAUDE_VISION_MODEL=claude-opus-4-8` (ou `claude-sonnet-4-6`), `CLAUDE_IMG_MAX_PX=1568`, `STT_MODEL=whisper-large-v3`. TTS : rester en edge-tts (ElevenLabs gratuit ≈ 10 min/mois, insuffisant). Coût vision : ~0.001 $/scène (Haiku 768px) → ~0.02-0.03 $/scène (Opus 1568px), à la demande seulement.

## Changements (2026-07-09) — retrait du GPS

Le GPS a été **entièrement retiré** (décision projet : pas de navigation GPS).
Supprimé : `src/gps/` (module complet), `state.gps_serial`, constantes `GPS_*` et
`GEOCODE_*`, intentions vocales localisation/navigation (`KEYWORDS_GPS`,
`KEYWORDS_NAVIGATE`, branches صيدلية/سبيطار/جامع/محطة), dépendances `pyserial` et
`pynmea2`, tests GPS/navigation associés. Le README a reçu la photo du projet
`assets/mourafiq-medina.png` (appareil MOURAFIQ IA porté dans la médina) en en-tête.

## Maintenance de ce fichier (économie de tokens)

Ce CLAUDE.md est chargé dans **chaque** session. Le tenir à jour après chaque changement significatif évite aux prochaines sessions de ré-explorer le code (gros poste de tokens). Règle : après un edit notable (nouveau module, nouvelle constante config, fix de comportement), mettre à jour la table concernée ici **dans le même commit**. Rester concis — ne pas dupliquer ce que le code/les commits disent déjà.

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
