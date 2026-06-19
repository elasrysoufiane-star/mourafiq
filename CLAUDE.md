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
│   │   └── reader.py               # lire_texte() — capture + délègue providers.ocr
│   ├── gps/
│   │   └── location.py             # init_gps(), get_gps(), naviguer()
│   ├── ai/
│   │   ├── groq_client.py          # groq_darija() — llama-3.1-8b-instant
│   │   └── claude_client.py        # claude_darija()/describe_scene()/read_text() — VLM
│   ├── providers/
│   │   ├── ai.py                   # get_ai_response() — routage groq/claude/openai
│   │   ├── stt.py                  # transcribe() — routage groq/openai
│   │   ├── tts.py                  # synthesize() — routage edge/gtts/elevenlabs
│   │   ├── vision_ai.py            # describe_scene() — routage local(YOLO)/claude
│   │   └── ocr.py                  # read_text() — routage local(Tesseract)/claude
│   └── conversation/
│       ├── intents.py              # KEYWORDS_* + process_command()
│       └── commands.py             # mode_conversation() — thread écoute
├── models/
│   └── yolov8n.pt                  # Git LFS
├── tests/
│   ├── test_config.py
│   ├── test_translations.py
│   ├── test_intents.py             # inclut mot de réveil (contient_wake/retirer_wake)
│   ├── test_providers.py           # routage AI/STT/TTS/vision/ocr + clés
│   └── smoke_claude_vision.py      # test isolé Claude vision (Pi ou image fixe)
├── temp/                           # audio.mp3, audio.wav (auto-créé)
└── logs/                           # Logs runtime (auto-créé)
```

## Import Chain (aucun import circulaire)

```
config.settings ──────────────────────────────┐ (stdlib + dotenv seulement)
src.vision.translations ──────────────────────┤ (rien)
src.core.state ───────────────────────────────┤ (threading seulement)
src.core.memory ──────────────────────────────┤ (config + threading — historique conversation)
src.audio.text_clean ─────────────────────────┤ (re seulement — nettoyage Markdown TTS)
src.providers.tts    ◄── config               │
src.providers.stt    ◄── config  (state lazy) │
src.providers.ai     ◄── config  (groq_client / claude_client lazy)
src.providers.vision_ai ◄── config, core.state, providers.ai  (claude_client lazy)
src.providers.ocr    ◄── config  (claude_client / providers.ai / pytesseract lazy)
src.audio.speaker    ◄── core.state, audio.text_clean  (providers.tts lazy dans _jouer_tts)
src.ai.groq_client   ◄── core.state           │
src.ai.claude_client ◄── config, core.memory  (anthropic + PIL lazy)
src.audio.listener   ◄── config, core.state, audio.speaker  (providers.stt lazy dans _transcrire)
src.vision.detector  ◄── config, core.state, audio.speaker, vision.translations  (providers.vision_ai lazy dans mode_auto_scene)
src.ocr.reader       ◄── core.state, audio.speaker  (providers.ocr lazy dans lire_texte)
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

**Architecture hybride (économie de tokens) :** YOLO local tourne en continu (gratuit, 0 token). Claude n'est appelé que sur intention vocale (`شنو قدامي؟`) — **ou** périodiquement en mode sans micro si `VISION_AI_PROVIDER=claude` (voir `AUTO_DESCRIBE_INTERVAL`, coût continu). Leviers : appel à la demande, image redimensionnée à 768px + JPEG q70, `max_tokens=150`, cooldown anti double-appel, Haiku par défaut. Usage (in/cache_read/out) loggé à chaque appel. Le marqueur de prompt caching est présent mais n'aide que si le prompt système dépasse le minimum cacheable du modèle.

## Mode « Full Claude » (branche `feat/full-claude-assistant`)

Cerveau **100% Claude** (langage + vision + lecture), oreilles/voix inchangées (Claude ne fait pas d'audio). Activé **uniquement via `.env`** — les défauts du code restent gratuits.

| Composant | Provider full-Claude | Modèle |
|-----------|----------------------|--------|
| Conversation darija | `AI_PROVIDER=claude` | `CLAUDE_TEXT_MODEL` (sonnet conseillé) |
| Description scène (à la demande) | `VISION_AI_PROVIDER=claude` | `CLAUDE_VISION_MODEL_HQ` (sonnet) |
| Description scène (auto, sans micro) | `VISION_AI_PROVIDER=claude` | `CLAUDE_VISION_MODEL` (haiku, éco) |
| Lecture texte / OCR | `OCR_PROVIDER=claude` | `CLAUDE_VISION_MODEL_HQ` + fallback Tesseract |
| STT (micro) | **reste** `groq` | Whisper |
| TTS (voix) | **reste** `edge` | ar-MA-JamalNeural |

**Stratégie MIXTE (coût/qualité) :** continu = Haiku (`CLAUDE_VISION_MODEL`), à la demande = Sonnet (`CLAUDE_VISION_MODEL_HQ`, déclenché par `hq=True` dans `describe_scene`).

**Prompts accessibilité (`src/ai/claude_client.py`) :** trois prompts système dédiés —
`_VISION_SYSTEM_PROMPT` (sécurité d'abord et avec insistance « عندك! », position+distance, action à faire, court), `_CHAT_SYSTEM_PROMPT` (compagnon darija patient), `_OCR_SYSTEM_PROMPT` (lit + donne le sens : courrier, médicaments, panneaux). Couvre rue + intérieur + lecture.

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
- **`describe_scene(image, question, hq=False)`** in `src/providers/vision_ai.py` — routage VLM (claude) ou fallback YOLO local. `hq=True` (question vocale) → modèle qualité (`CLAUDE_VISION_MODEL_HQ`) + ignore le cooldown ; `hq=False` (boucle auto) → modèle éco + cooldown
- **`read_text(image)`** in `src/providers/ocr.py` — routage OCR claude / Tesseract local ; retourne toujours une phrase darija prête à parler
- **`claude_describe_scene(image, q, model=None)` / `claude_read_text(image, model=None)`** in `src/ai/claude_client.py` — Claude multimodal (scène / OCR), image downscalée, usage loggé, modèle paramétrable
- **`lire_texte()`** in `src/ocr/reader.py` — capture caméra → `providers.ocr.read_text()` → `parler()`
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
| `OCR_PROVIDER` | `local` | `local`, `claude` | `src/providers/ocr.py` |

*options futures — structure prête, fallback automatique vers groq si clé absente.
`claude` (AI + vision + OCR) : payant, fallback automatique vers groq/local si `ANTHROPIC_API_KEY` absente.
**Claude ne fait PAS d'audio** : STT reste Whisper/Groq, TTS reste edge-tts/ElevenLabs — un mode « 100% Claude » se limite au cerveau (langage + vision).

**Règles :**
1. Mode par défaut = gratuit (`groq` + `edge` + `local`). Ne jamais changer les défauts dans le code.
2. Si clé payante absente → message clair + fallback gratuit automatique, jamais d'exception non gérée.
3. YOLO et GPS restent toujours locaux. Tesseract reste le fallback OCR (et le défaut) — Claude OCR est opt-in.
4. `src/providers/` = routage uniquement. Implémentations dans leurs modules d'origine.
5. Imports providers en lazy (dans `_jouer_tts` / `_transcrire` / `read_text` / `lire_texte`) — rester testable sur Windows sans matériel.

## Configuration (config/settings.py)

| Constante | Défaut | Rôle |
|-----------|--------|------|
| `GROQ_API_KEY` | `os.environ.get(...)` | Vide si absent (erreur levée dans app.init()) |
| `DEMO_MODE` | `free` | `free` (logique normale) ou `demo` (documentation uniquement) |
| `CONF_SEUIL` | `0.50` | Seuil confiance YOLO (tester 0.45 si détection insuffisante) |
| `EDGE_VOICE` | `ar-MA-JamalNeural` | Voix edge-tts |
| `TIMEOUT_ECOUTE` | `≈125 chunks (8s)` | Timeout micro |
| `MODEL_PATH` | `models/yolov8n.pt` | Chemin modèle YOLO |
| `GPS_PORT` | `/dev/ttyS0` | Port série GPS (env-overridable) |
| `GPS_BAUD` | `9600` | Baud GPS (env-overridable) |
| `GPS_READ_TIMEOUT` | `3` | Durée max lecture NMEA (s) avant abandon |
| `GEOCODE_ENABLED` | `1` | Reverse geocoding lat/lon → adresse (Nominatim) ; 0 = coords brutes |
| `GEOCODE_TIMEOUT` | `5` | Timeout requête Nominatim (s) |
| `AI_PROVIDER` | `groq` | Provider NLP (groq / claude / openai) |
| `STT_PROVIDER` | `groq` | Provider STT (groq / openai) |
| `STT_MODEL` | `whisper-large-v3-turbo` | Modèle Whisper Groq (`whisper-large-v3` pour +précision) |
| `TTS_PROVIDER` | `edge` | Provider TTS (edge / gtts / elevenlabs) |
| `VISION_AI_PROVIDER` | `local` | Provider scène VLM (local YOLO / claude) |
| `OCR_PROVIDER` | `local` | Provider lecture texte (local Tesseract / claude, fallback Tesseract) |
| `ELEVENLABS_API_KEY` | `""` | Clé ElevenLabs (vide = fallback edge) |
| `ELEVENLABS_VOICE_ID` | `""` | Voice ID ElevenLabs (vide = voix par défaut Adam) |
| `OPENAI_API_KEY` | `""` | Clé OpenAI (non utilisé par défaut) |
| `ANTHROPIC_API_KEY` | `""` | Clé Claude (vide = fallback groq/local) |
| `CLAUDE_TEXT_MODEL` | `claude-haiku-4-5` | Modèle conversation darija (`claude_darija`) |
| `CLAUDE_VISION_MODEL` | `claude-haiku-4-5` | Modèle VLM **continu** (boucle auto) — éco |
| `CLAUDE_VISION_MODEL_HQ` | `=VISION_MODEL` | Modèle VLM **à la demande** (« شنو قدامي » + OCR) — qualité (sonnet) |
| `CLAUDE_MAX_TOKENS` | `150` | Plafond réponse scène/chat (parlée → courte) |
| `CLAUDE_OCR_MAX_TOKENS` | `400` | Plafond réponse OCR (lettre/notice → plus longue) |
| `CLAUDE_IMG_MAX_PX` | `768` | Taille max image avant envoi (tokens) |
| `CLAUDE_IMG_QUALITY` | `70` | Qualité JPEG image avant envoi (tokens) |
| `VISION_COOLDOWN` | `3` | Anti double-appel scène (secondes) |
| `AUTO_DESCRIBE_INTERVAL` | `5` | Description auto en mode sans micro (s ; 0 = désactivé). Claude si `VISION_AI_PROVIDER=claude` |
| `WAKE_WORD_ENABLED` | `1` | Mot de réveil « مرافق » requis (0 = écoute continue) |
| `WAKE_FOLLOWUP_WINDOW` | `15` | Fenêtre de suivi après réveil/commande (secondes) |
| `CONV_MEMORY_TURNS` | `6` | Tours (user+assistant) gardés en contexte Claude → questions de suivi. 0 = sans mémoire |

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
python3 tests/test_memory.py        # mémoire conversation + nettoyage TTS
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
| GPS robustesse | `get_gps()` : accepte GGA toutes constellations (GNGGA/GPGGA…), vérifie `gps_qual` (fix réel), lecture bornée `GPS_READ_TIMEOUT`, trame corrompue ignorée ; `GPS_PORT/BAUD` env-overridable | `src/gps/location.py`, `config/settings.py` |
| GPS reverse geocoding | `reverse_geocode()` (Nominatim OSM, stdlib `urllib`, cache ~11 m) → « vous êtes Boulevard X، quartier Y، ville ». `position_actuelle()` centralise « وين أنا » (adresse réelle, fallback coords). Fallback propre si pas d'Internet | `src/gps/location.py`, `src/conversation/intents.py` |
| Mode vision seul | Sans micro : `init()` met `state.mic_ok=False`, saute la calibration, `main()` ne lance pas le thread conversation → plus de boucle « En attente de voix → Timeout 8s » | `src/core/app.py`, `src/core/state.py` |
| Description auto (sans micro) | Thread `mode_auto_scene()` : sans micro, décrit la scène toutes les `AUTO_DESCRIBE_INTERVAL`s (`describe_scene()`→`parler()`). Claude si `VISION_AI_PROVIDER=claude`, sinon YOLO+Groq gratuit. Respecte `conversation_active` + cooldown | `src/vision/detector.py`, `src/core/app.py`, `config/settings.py` |

**GPS — reste à faire (prioritaire) :** `naviguer()` envoie la position de départ (adresse réelle) + destination au LLM, mais sans API de routage le LLM **ne peut pas** calculer un vrai itinéraire (directions encore approximatives). Prochaines étapes : routage réel (OSRM/Directions) + haversine pour la distance ; cap (RMC en mouvement ou magnétomètre) pour « tourne à gauche/droite ». Idéalement thread GPS de fond qui cache le dernier fix (comme YOLO).

**Limite connue (matérielle) :** micro+voix sur le même canal **Bluetooth HFP 8 kHz** (FreeBuds SE 3) → audio dégradé des deux côtés, écho résiduel et erreurs Whisper darija possibles. Correctif définitif = **micro USB séparé** (FreeBuds en sortie A2DP). Le mot de réveil compense côté fiabilité.

## Branche `feat/full-claude-assistant` (cerveau 100% Claude)

| Changement | Description | Fichiers |
|-----------|-------------|----------|
| Prompts accessibilité | `_VISION_SYSTEM_PROMPT` réécrit (sécurité d'abord + insistance « عندك! », position/distance, action, court) + nouveau `_OCR_SYSTEM_PROMPT` ; couvre rue/intérieur/lecture | `src/ai/claude_client.py` |
| Modèle mixte | `describe_scene(..., hq=)` : Haiku en continu (`CLAUDE_VISION_MODEL`), Sonnet à la demande (`CLAUDE_VISION_MODEL_HQ`) ; `claude_describe_scene`/`claude_read_text` acceptent `model=` | `src/providers/vision_ai.py`, `src/ai/claude_client.py`, `src/conversation/intents.py`, `config/settings.py` |
| OCR Claude | Nouveau provider `read_text()` (claude + fallback Tesseract) ; `reader.lire_texte()` simplifié (capture + parle) ; `claude_read_text()` + `CLAUDE_OCR_MAX_TOKENS` | `src/providers/ocr.py`, `src/ocr/reader.py`, `src/ai/claude_client.py`, `config/settings.py` |
| `OCR_PROVIDER` | Routage OCR `local`/`claude` (défaut local) + tests | `config/settings.py`, `tests/test_providers.py` |
| Mémoire conversation | `src/core/memory.py` : historique roulant TEXTE (`CONV_MEMORY_TURNS` tours) PARTAGÉ chat+vision+OCR → questions de suivi (« وزيد على اليسار؟ », « عاود », « زيدني تفاصيل »). Préfixé à chaque appel Claude ; images jamais stockées ; boucle auto sans micro (`hq=False`) ne mémorise pas (`remember=hq`). Pairage strict user→assistant | `src/core/memory.py`, `src/ai/claude_client.py`, `src/providers/vision_ai.py`, `config/settings.py`, `tests/test_memory.py` |
| Nettoyage TTS | `src/audio/text_clean.py` `clean_for_speech()` retire le Markdown (gras/listes/titres) avant synthèse — sinon edge-tts lit `*`/`-` littéralement. Appelé dans `parler()`. Consigne anti-Markdown ajoutée aux 3 prompts système (`_NO_MARKDOWN`) | `src/audio/text_clean.py`, `src/audio/speaker.py`, `src/ai/claude_client.py`, `tests/test_memory.py` |

**Activation (`.env`) :** `AI_PROVIDER=claude`, `VISION_AI_PROVIDER=claude`, `OCR_PROVIDER=claude`, `ANTHROPIC_API_KEY=sk-ant-...`, `CLAUDE_VISION_MODEL_HQ=claude-sonnet-4-6`. `GROQ_API_KEY` reste obligatoire (STT + démarrage). Coût piloté par `AUTO_DESCRIBE_INTERVAL` (vision continue) et le choix Haiku/Sonnet/Opus.

**Config « qualité max » (coût accepté), via `.env` uniquement :** `AI_PROVIDER=claude`, `VISION_AI_PROVIDER=claude`, `CLAUDE_VISION_MODEL=claude-opus-4-8` (ou `claude-sonnet-4-6`), `CLAUDE_IMG_MAX_PX=1568`, `STT_MODEL=whisper-large-v3`. TTS : rester en edge-tts (ElevenLabs gratuit ≈ 10 min/mois, insuffisant). Coût vision : ~0.001 $/scène (Haiku 768px) → ~0.02-0.03 $/scène (Opus 1568px), à la demande seulement.

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
