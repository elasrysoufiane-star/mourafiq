# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mourafiq (مرافق)** is an AI-powered assistive device for visually impaired users in Morocco, running on a Raspberry Pi 4. It combines Claude-powered scene description, OCR, and voice interaction, responding entirely in Moroccan Darija Arabic. (Le GPS a été retiré du projet le 2026-07-09 — ne pas le réintroduire.)

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
│   │   ├── logging_setup.py        # setup_logging() — tee stdout/stderr → logs/*.log daté
│   │   └── app.py                  # init() + main() — hardware lazy-loaded
│   ├── audio/
│   │   ├── speaker.py              # parler(), suprimer_alsa(), calibrer_micro()
│   │   └── listener.py             # reconnaitre_voix(), _transcrire()
│   ├── vision/
│   │   ├── camera.py               # capturer(hq=) — flux 640×480 ou still pleine résolution
│   │   └── detector.py             # mode_auto_scene() — description auto (Claude, 100%)
│   ├── ocr/
│   │   └── reader.py               # lire_texte() — capture + délègue providers.ocr
│   ├── ai/
│   │   ├── groq_client.py          # groq_darija() — llama-3.1-8b-instant
│   │   └── claude_client.py        # claude_darija()/describe_scene()/read_text() — VLM
│   ├── providers/
│   │   ├── ai.py                   # get_ai_response() — routage groq/claude/openai
│   │   ├── stt.py                  # transcribe() — routage groq/openai
│   │   ├── tts.py                  # synthesize() — routage azure/edge/gtts/elevenlabs
│   │   ├── vision_ai.py            # describe_scene() — 100% Claude, message clair si échec
│   │   └── ocr.py                  # read_text() — routage local(Tesseract)/claude
│   └── conversation/
│       ├── intents.py              # KEYWORDS_* + process_command()
│       └── commands.py             # mode_conversation() — thread écoute
├── tests/
│   ├── test_config.py
│   ├── test_intents.py             # inclut mot de réveil (contient_wake/retirer_wake)
│   ├── test_providers.py           # routage AI/STT/TTS/ocr + clés
│   ├── test_fallbacks.py           # bascule (Groq/Tesseract/edge-tts) ou message clair si Claude/Azure en panne
│   ├── test_listener.py            # VAD webrtcvad/seuil + index micro (sans matériel)
│   ├── test_logging.py             # tee stdout→fichier daté, horodatage, thread-safe, purge
│   └── smoke_claude_vision.py      # test isolé Claude vision (Pi ou image fixe)
├── temp/                           # audio.mp3, audio.wav (auto-créé)
└── logs/                           # Logs runtime (auto-créé)
```

## Import Chain (aucun import circulaire)

```
config.settings ──────────────────────────────┐ (stdlib + dotenv seulement)
src.core.state ───────────────────────────────┤ (threading seulement)
src.core.logging_setup ───────────────────────┤ (stdlib seulement — tee stdout/stderr → fichier)
src.vision.camera ◄── core.state              │ (capture 640×480 / still HQ)
src.core.memory ──────────────────────────────┤ (config + threading — historique conversation)
src.audio.text_clean ─────────────────────────┤ (re seulement — nettoyage Markdown TTS)
src.providers.tts    ◄── config               │
src.providers.stt    ◄── config  (state lazy) │
src.providers.ai     ◄── config  (groq_client / claude_client lazy)
src.providers.vision_ai ◄── config  (claude_client lazy)
src.providers.ocr    ◄── config  (claude_client / providers.ai / pytesseract lazy)
src.audio.speaker    ◄── core.state, audio.text_clean  (providers.tts lazy dans _jouer_tts)
src.ai.groq_client   ◄── core.state           │
src.ai.claude_client ◄── config, core.memory  (anthropic + PIL lazy)
src.audio.listener   ◄── config, core.state, audio.speaker  (providers.stt lazy dans _transcrire)
src.vision.detector  ◄── config, core.state, audio.speaker, vision.camera  (providers.vision_ai, providers.ocr lazy dans mode_auto_scene)
src.ocr.reader       ◄── audio.speaker, vision.camera  (providers.ocr lazy dans lire_texte)
src.conversation.intents ◄── audio.speaker, providers.ai, providers.vision_ai, vision.camera, ocr.reader
src.conversation.commands ◄── core.state, audio.listener, conversation.intents
src.core.app         ◄── config, core.state, core.logging_setup, audio.speaker, audio.listener,
                          vision.detector, conversation.commands
main.py              ◄── core.app
```

## API — Groq (backend principal)

| Feature | Modèle | Quota gratuit |
|---------|--------|---------------|
| NLP / Darija | `llama-3.1-8b-instant` | 14 400 req/jour |
| STT Arabe | `whisper-large-v3` (défaut, +précision darija) ou `-turbo` (rapide) | 7 200 req/jour |

Clé sur **console.groq.com** → API Keys (format `gsk_...`)

## API — Azure Speech (TTS officiel, optionnel)

Même voix marocaine `ar-MA-JamalNeural` qu'edge-tts (catalogue identique), mais
API officielle stable. Tier **F0 gratuit : 500K caractères/mois** — largement
assez. Clé sur **portal.azure.com** → ressource « Speech service » (région
`westeurope` par défaut, sinon surcharger `AZURE_SPEECH_REGION`). Sans clé ou
en cas d'échec : fallback automatique edge-tts.

## API — Claude (Anthropic, optionnel — cerveau vision à la demande)

| Feature | Modèle défaut | Prix /1M (in/out) |
|---------|---------------|-------------------|
| Description de scène (VLM) | `claude-haiku-4-5` | $1 / $5 |
| Qualité recommandée (à la demande) | `claude-sonnet-5` | $2 / $10 (intro jusqu'au 31/08/2026, puis $3/$15) |
| Qualité max (option) | `claude-opus-4-8` | $5 / $25 |

Clé sur **console.anthropic.com** → API Keys (format `sk-ant-...`). **Obligatoire pour la vision** (YOLO a été retiré, il n'y a plus de fallback local) — sans clé ou en cas d'échec, message vocal clair d'indisponibilité au lieu d'une description.

**Vision 100% Claude (YOLO retiré, 2026-07-07) :** Claude est appelé sur intention vocale (`شنو قدامي؟`) **et** en permanence par la boucle AutoScene (voir `AUTO_DESCRIBE_INTERVAL`, coût continu, tourne avec ou sans micro). Leviers : image redimensionnée (640px boucle continue / 1568px still HQ) + JPEG q70, `max_tokens=150`, cooldown anti double-appel, Haiku par défaut en continu (Sonnet à la demande). Usage (in/cache_read/out) loggé à chaque appel. Le marqueur de prompt caching est présent mais n'aide que si le prompt système dépasse le minimum cacheable du modèle.

## Mode « Full Claude » (DÉFAUT du code depuis 2026-07-08)

Cerveau **100% Claude** (langage + vision + lecture), oreilles/voix hors Claude (il ne fait pas d'audio). C'est le mode PAR DÉFAUT : le `.env` ne contient que les clés API, toute la config vit dans `config/settings.py`. Sans clé, chaque brique retombe automatiquement sur le gratuit (claude→groq, azure→edge, OCR claude→Tesseract).

| Composant | Provider (défaut) | Modèle |
|-----------|-------------------|--------|
| Conversation darija | `AI_PROVIDER=claude` (fallback groq) | `CLAUDE_TEXT_MODEL` (sonnet-5) |
| Description scène (à la demande) | toujours Claude | `CLAUDE_VISION_MODEL_HQ` (sonnet-5) |
| Description scène (auto, toujours active) | toujours Claude | `CLAUDE_VISION_MODEL` (haiku, éco) |
| Lecture texte / OCR | `OCR_PROVIDER=claude` (fallback Tesseract) | `CLAUDE_VISION_MODEL_HQ` (sonnet-5) |
| STT (micro) | **reste** `groq` (gratuit) | `whisper-large-v3` |
| TTS (voix) | `azure` — Azure Speech officiel (fallback edge) | ar-MA-JamalNeural |

**Stratégie MIXTE (coût/qualité) :** continu = Haiku (`CLAUDE_VISION_MODEL`), à la demande = Sonnet (`CLAUDE_VISION_MODEL_HQ`, déclenché par `hq=True` dans `describe_scene`).

**Prompts accessibilité (`src/ai/claude_client.py`) :** trois prompts système dédiés —
`_VISION_SYSTEM_PROMPT` (sécurité d'abord et avec insistance « عندك! », position+distance, action à faire, court), `_CHAT_SYSTEM_PROMPT` (compagnon darija patient), `_OCR_SYSTEM_PROMPT` (lit + donne le sens : courrier, médicaments, panneaux). Couvre rue + intérieur + lecture.

## Thread Synchronisation

| Thread | Fonction | Fichier |
|--------|----------|---------|
| AutoScene (toujours actif) | `mode_auto_scene()` | `src/vision/detector.py` |
| Conversation (si micro) | `mode_conversation()` | `src/conversation/commands.py` |

Le thread `Vision` (`mode_vision()`, boucle YOLO continue) a été **retiré le
2026-07-07** — voir `.claude/memory/decisions.md`. Seul `AutoScene` fait de la
vision maintenant, 100% Claude.

**AutoScene tourne TOUJOURS** (`AUTO_DESCRIBE_INTERVAL > 0`), que l'utilisateur
parle ou non, avec ou sans micro : toutes les N secondes (6s par défaut),
`capture → describe_scene() + read_text() → parler()` décrit la caméra en détail
ET lit tout texte visible, par la voix. `state.mic_ok` ne pilote que le
thread **Conversation** (écoute + réponse), lancé EN PLUS d'AutoScene si un
micro est détecté (`app.init()` sonde le micro et saute la calibration si absent —
évite la boucle « En attente de voix → Timeout 8s »). Résultat : la scène est
toujours décrite (et tout texte lu) ; si l'utilisateur parle, l'assistant répond
aussi, sans jamais couper la narration automatique. La scène passe TOUJOURS par
Claude (pas de fallback local, YOLO retiré) ; l'OCR est piloté par `OCR_PROVIDER`
(Claude payant / Tesseract local gratuit). Les réponses OCR creuses (aucun texte
trouvé) sont tues côté `mode_auto_scene()` pour ne pas les répéter à chaque cycle.

| Primitive | Type | Rôle |
|-----------|------|------|
| `camera_lock` | `Lock` | Sérialise `camera.capture_array()` (partagé AutoScene/Conversation) |
| `audio_lock` | `Lock` | Sérialise `parler()` (partagé entre les threads) |
| `conversation_active` | `Event` | **Pause AutoScene pendant la sortie audio uniquement** — géré dans `speaker.parler()` uniquement |
| `user_speaking` | `Event` | **La voix de l'utilisateur est PRIORITAIRE sur la narration** : levé par `reconnaitre_voix()` à la 1ʳᵉ détection de voix, reste levé pendant transcription + traitement, relâché par `mode_conversation()` (try/finally). AutoScene attend (`_attendre_parole_finie`, borne 20s) avant de capturer/parler |
| `mic_ok` | `bool` | Micro détecté au démarrage. `False` → thread Conversation non lancé (AutoScene reste actif) |

## Key Functions

- **`setup_logging(base_dir, to_file, keep_files)`** in `src/core/logging_setup.py` — installe un tee sur `sys.stdout`/`stderr` (appelé au tout début de `main()`) : chaque `print()` de tous les threads part à l'écran ET dans `logs/mourafiq_AAAAMMJJ_HHMMSS.log`, horodaté + nom du thread, thread-safe (verrou), flush par ligne. `LOG_TO_FILE=0` désactive. Purge les vieux logs (`LOG_KEEP_FILES`)
- **`parler(texte)`** in `src/audio/speaker.py` — sets `conversation_active`, délègue à `providers.tts.synthesize()`
- **`reconnaitre_voix()`** in `src/audio/listener.py` — PyAudio VAD → WAV → `providers.stt.transcribe()`; **timeout 8s**
- **`get_ai_response(question)`** in `src/providers/ai.py` — routage vers `groq_darija()` / `claude_darija()` / openai
- **`groq_darija(question)`** in `src/ai/groq_client.py` — LLaMA, 3 retries backoff (implémentation)
- **`describe_scene(image, question, hq=False)`** in `src/providers/vision_ai.py` — 100% Claude (pas de fallback local, YOLO retiré) ; message vocal clair si `ANTHROPIC_API_KEY` absente ou échec. `hq=True` (question vocale) → modèle qualité (`CLAUDE_VISION_MODEL_HQ`) + ignore le cooldown ; `hq=False` (boucle auto) → modèle éco + cooldown
- **`read_text(image, remember=True)`** in `src/providers/ocr.py` — routage OCR claude / Tesseract local ; retourne toujours une phrase darija prête à parler ; `remember=False` dans la boucle AutoScene (pas un tour de dialogue)
- **`claude_describe_scene(image, q, model=None)` / `claude_read_text(image, model=None, remember=True)`** in `src/ai/claude_client.py` — Claude multimodal (scène / OCR), image downscalée, usage loggé, modèle paramétrable
- **`lire_texte()`** in `src/ocr/reader.py` — capture caméra → `providers.ocr.read_text()` → `parler()`
- **`process_command(commande)`** in `src/conversation/intents.py` — retourne `False` pour arrêt
- **`mode_conversation()`** in `src/conversation/commands.py` — boucle écoute + mot de réveil « مرافق » + fenêtre de suivi (`WAKE_FOLLOWUP_WINDOW`)
- **`contient_wake(commande)` / `retirer_wake(commande)`** in `src/conversation/intents.py` — détection/retrait du mot de réveil
- **`calibrer_micro()`** in `src/audio/listener.py` — mesure bruit ambiant → `VOL_SEUIL`
- **`suprimer_alsa()`** in `src/audio/listener.py` — contextmanager stderr redirect
- **`_create(tag, **kwargs)`** in `src/ai/claude_client.py` — `messages.create` centralisé : retries backoff (429/overloaded) sur une clé + **bascule automatique** `ANTHROPIC_API_KEY` → `ANTHROPIC_API_KEY_FALLBACK` si la principale échoue ; `ClaudeError` si toutes les clés échouent. Utilisé par `claude_darija` et `_vision_call`

## Providers (src/providers/)

Couche de routage — défauts = MEILLEURE QUALITÉ (2026-07-08), surchargeables via `.env` ; sans clé, bascule automatique vers le gratuit.

| Variable | Défaut | Options | Fichier |
|----------|--------|---------|---------|
| `AI_PROVIDER` | `claude` (fallback groq) | `claude`, `groq`, `openai`* | `src/providers/ai.py` |
| `STT_PROVIDER` | `groq` | `groq`, `openai`* | `src/providers/stt.py` |
| `TTS_PROVIDER` | `azure` (fallback edge) | `azure`, `edge`, `gtts`, `elevenlabs` | `src/providers/tts.py` |
| `OCR_PROVIDER` | `claude` (fallback local) | `claude`, `local` | `src/providers/ocr.py` |

*options futures — structure prête, fallback automatique vers groq si clé absente.
`claude` (AI + OCR) : payant, fallback automatique vers groq/local si `ANTHROPIC_API_KEY` absente.
**La scène (`src/providers/vision_ai.py`) n'a PAS de variable provider** — elle passe
TOUJOURS par Claude (YOLO retiré, plus de fallback local). Sans clé ou en cas
d'échec : message vocal clair, jamais de silence, jamais d'exception.
**Claude ne fait PAS d'audio** : STT reste Whisper/Groq, TTS reste Azure/edge-tts — un mode « 100% Claude » se limite au cerveau (langage + vision).

**Règles :**
1. Défauts du code = MEILLEURE QUALITÉ (`claude` + `azure` + `claude`, décision 2026-07-08 — voir `.claude/memory/decisions.md`) ; le `.env` ne contient QUE les clés API. Le gratuit n'est plus le défaut mais le FALLBACK automatique : sans clé ou en panne → groq / edge-tts / Tesseract, jamais de crash, jamais de silence (sauf la scène : message vocal clair, pas de fallback local).
2. Si clé payante absente **OU appel Claude en échec après retries** → message clair, jamais d'exception non gérée. `claude_client` lève `ClaudeError` (jamais de phrase d'erreur avalée) ; la couche providers attrape et bascule : chat→Groq, OCR→Tesseract, scène→message vocal clair d'indisponibilité (pas de bascule locale, YOLO retiré) (`tests/test_fallbacks.py`).
3. Tesseract reste le fallback OCR — Claude OCR est le défaut depuis 2026-07-08.
4. `src/providers/` = routage uniquement. Implémentations dans leurs modules d'origine.
5. Imports providers en lazy (dans `_jouer_tts` / `_transcrire` / `read_text` / `lire_texte`) — rester testable sur Windows sans matériel.

## Configuration (config/settings.py)

| Constante | Défaut | Rôle |
|-----------|--------|------|
| `GROQ_API_KEY` | `os.environ.get(...)` | Vide si absent (erreur levée dans app.init()) |
| `DEMO_MODE` | `free` | `free` (logique normale) ou `demo` (documentation uniquement) |
| `EDGE_VOICE` | `ar-MA-JamalNeural` | Voix marocaine — utilisée par Azure Speech ET edge-tts (même catalogue) |
| `TIMEOUT_ECOUTE` | `≈125 chunks (8s)` | Timeout micro |
| `AI_PROVIDER` | `claude` | Provider NLP (claude / groq / openai) — fallback groq sans clé |
| `STT_PROVIDER` | `groq` | Provider STT (groq / openai) |
| `STT_MODEL` | `whisper-large-v3` | Modèle Whisper Groq (`whisper-large-v3-turbo` si la vitesse prime) |
| `TTS_PROVIDER` | `azure` | Provider TTS (azure / edge / gtts / elevenlabs) — fallback edge sans clé |
| `OCR_PROVIDER` | `claude` | Provider lecture texte (claude / local) — fallback Tesseract sans clé |
| `AZURE_SPEECH_KEY` | `""` | Clé Azure Speech (TTS officiel, tier F0 gratuit 500K car./mois) ; vide = fallback edge-tts |
| `AZURE_SPEECH_REGION` | `westeurope` | Région de la ressource Azure Speech |
| `ELEVENLABS_API_KEY` | `""` | Clé ElevenLabs (vide = fallback edge) |
| `ELEVENLABS_VOICE_ID` | `""` | Voice ID ElevenLabs (vide = voix par défaut Adam) |
| `OPENAI_API_KEY` | `""` | Clé OpenAI (non utilisé par défaut) |
| `ANTHROPIC_API_KEY` | `""` | Clé Claude PRINCIPALE — **requise pour la scène** (pas de fallback local, YOLO retiré) ; vide = fallback groq pour le chat/OCR uniquement |
| `ANTHROPIC_API_KEY_FALLBACK` | `""` | Clé Claude de SECOURS — bascule auto si la principale échoue (quota/invalide/panne), gérée dans `claude_client._create`. Vide = pas de secours |
| `CLAUDE_TEXT_MODEL` | `claude-opus-4-8` | Modèle conversation darija (`claude_darija`) — Opus (qualité max, multimodal) |
| `CLAUDE_VISION_MODEL` | `claude-haiku-4-5` | Modèle VLM **continu** (boucle auto + OCR de fond) — Haiku pour la VITESSE (~1.5s : moins de décalage caméra→parole), pas le coût |
| `CLAUDE_VISION_MODEL_HQ` | `claude-opus-4-8` | Modèle VLM scène **à la demande** (« شنو قدامي ») — Opus |
| `CLAUDE_OCR_MODEL` | `claude-opus-4-8` | Modèle OCR **à la demande** (« قرا ليا ») — Opus, précision max (posologie/manuscrit) ; OCR de fond reste `CLAUDE_VISION_MODEL` |
| `CLAUDE_INTENT_MODEL` | `claude-haiku-4-5` | Classification d'INTENTION des transcriptions déformées (`claude_intention`) — filet de sécurité STT, réponse d'un mot (~1s) |
| `CLAUDE_MAX_TOKENS` | `300` | Plafond réponse **à la demande** (scène HQ + chat) — riche |
| `CLAUDE_SCENE_AUTO_MAX_TOKENS` | `60` | Plafond scène **boucle de fond** — court (~6-7s parlé, rotation rapide) |
| `CLAUDE_OCR_MAX_TOKENS` | `400` | Plafond réponse OCR (lettre/notice → plus longue) |
| `CLAUDE_IMG_MAX_PX` | `1568` | Taille max image avant envoi (tokens). 1568 = profite du still HQ ; sans effet sur la boucle continue (source 640px) |
| `CLAUDE_IMG_QUALITY` | `90` | Qualité JPEG image avant envoi (90 = petits caractères plus nets pour l'OCR) |
| `HQ_CAPTURE_ENABLED` | `1` | Still pleine résolution capteur pour OCR + scène à la demande (`capturer(hq=True)`, switch_mode ~0.5-1s). 0 = tout en 640×480 |
| `VISION_COOLDOWN` | `3` | Anti double-appel scène (secondes) |
| `AUTO_DESCRIBE_INTERVAL` | `1` (narration continue) | Description continue N s après la fin de la parole précédente — scène + OCR en PARALLÈLE (ThreadPoolExecutor), silence effectif ≈2.5-3.5s. Mot de réveil audible dans les respirations. 0 = à la demande |
| `VOICE_PRIORITY` | `0` (narration reine) | 0 = la narration n'attend JAMAIS le micro (STT non fiable + bruit ambiant classé « voix » suspendait la narration). 1 = la voix de l'utilisateur redevient prioritaire (`user_speaking`) — à réactiver avec un vrai micro |
| `MIC_DEVICE_INDEX` | `-1` | `-1` = micro par défaut système (micro USB). Ouverture robuste : index configuré → défaut, 16 kHz → taux natif (`_ouvrir_micro`) |
| `WAKE_WORD_ENABLED` | `1` | Mot de réveil « مرافق » requis (0 = écoute continue) |
| `WAKE_FOLLOWUP_WINDOW` | `15` | Fenêtre de suivi après réveil/commande (secondes) |
| `CONV_MEMORY_TURNS` | `15` | Tours (user+assistant) gardés en contexte Claude → questions de suivi. 0 = sans mémoire. + dernière image gardée pour suivi visuel (`memory.set_last_image`) |
| `LOG_TO_FILE` | `1` | Capture toute la sortie console dans `logs/mourafiq_*.log` (horodaté + thread). 0 = console seule |
| `LOG_KEEP_FILES` | `20` | Nombre de fichiers log gardés (les plus anciens supprimés au démarrage → carte SD du Pi) |

## Imports matériels — lazy loading

`Picamera2` et `Groq` sont importés à l'intérieur de `app.init()`, pas au niveau module.
`anthropic` et `PIL` sont importés en lazy dans `src/ai/claude_client.py` (jamais au niveau module).
Cela permet d'importer `config`, `src.conversation.intents` etc.
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
python3 tests/test_intents.py
python3 tests/test_providers.py
python3 tests/test_memory.py        # mémoire conversation + nettoyage TTS
python3 tests/test_fallbacks.py     # bascule/message clair si Claude en panne
python3 tests/test_listener.py      # VAD + index micro (sans matériel)
python3 tests/test_logging.py       # tee stdout→fichier daté, thread-safe, purge
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

## Branche `feat/full-claude-assistant` (cerveau 100% Claude)

| Changement | Description | Fichiers |
|-----------|-------------|----------|
| Prompts accessibilité | `_VISION_SYSTEM_PROMPT` réécrit (sécurité d'abord + insistance « عندك! », position/distance, action, court) + nouveau `_OCR_SYSTEM_PROMPT` ; couvre rue/intérieur/lecture | `src/ai/claude_client.py` |
| Modèle mixte | `describe_scene(..., hq=)` : Haiku en continu (`CLAUDE_VISION_MODEL`), Sonnet à la demande (`CLAUDE_VISION_MODEL_HQ`) ; `claude_describe_scene`/`claude_read_text` acceptent `model=` | `src/providers/vision_ai.py`, `src/ai/claude_client.py`, `src/conversation/intents.py`, `config/settings.py` |
| OCR Claude | Nouveau provider `read_text()` (claude + fallback Tesseract) ; `reader.lire_texte()` simplifié (capture + parle) ; `claude_read_text()` + `CLAUDE_OCR_MAX_TOKENS` | `src/providers/ocr.py`, `src/ocr/reader.py`, `src/ai/claude_client.py`, `config/settings.py` |
| `OCR_PROVIDER` | Routage OCR `local`/`claude` (défaut local) + tests | `config/settings.py`, `tests/test_providers.py` |
| Mémoire conversation | `src/core/memory.py` : historique roulant TEXTE (`CONV_MEMORY_TURNS` tours) PARTAGÉ chat+vision+OCR → questions de suivi (« وزيد على اليسار؟ », « عاود », « زيدني تفاصيل »). Préfixé à chaque appel Claude ; images jamais stockées ; boucle auto sans micro (`hq=False`) ne mémorise pas (`remember=hq`). Pairage strict user→assistant | `src/core/memory.py`, `src/ai/claude_client.py`, `src/providers/vision_ai.py`, `config/settings.py`, `tests/test_memory.py` |
| Nettoyage TTS | `src/audio/text_clean.py` `clean_for_speech()` retire le Markdown (gras/listes/titres) avant synthèse — sinon edge-tts lit `*`/`-` littéralement. Appelé dans `parler()`. Consigne anti-Markdown ajoutée aux 3 prompts système (`_NO_MARKDOWN`) | `src/audio/text_clean.py`, `src/audio/speaker.py`, `src/ai/claude_client.py`, `tests/test_memory.py` |
| Thinking off (2026-07-06) | `thinking={'type':'disabled'}` (`_THINKING_OFF`) explicite sur tous les `messages.create` — sur `claude-sonnet-5` le thinking adaptatif est ACTIF par défaut si omis → mangerait `max_tokens=150` + latence vocale. Nécessite un SDK anthropic récent sur le Pi (`pip install -U anthropic`) | `src/ai/claude_client.py` |
| Capture HQ (2026-07-06) | `src/vision/camera.py` `capturer(hq=)` centralise les captures (camera_lock inclus). OCR + scène à la demande → still PLEINE RÉSOLUTION via `switch_mode_and_capture_array` (~0.5-1s) ; boucles YOLO/auto → flux 640×480. Fallback silencieux 640×480 si still indisponible. `HQ_CAPTURE_ENABLED=0` pour désactiver. Mettre `CLAUDE_IMG_MAX_PX=1568` dans .env pour en profiter | `src/vision/camera.py`, `src/core/app.py`, `src/core/state.py`, `src/ocr/reader.py`, `src/conversation/intents.py`, `src/vision/detector.py`, `config/settings.py` |
| Fallbacks réels (2026-07-06) | Avant : `claude_client` avalait tout échec en phrase d'erreur → les fallbacks documentés étaient du code MORT (Claude en panne = assistant muet). Maintenant : `ClaudeError` levée après retries, la couche providers bascule — chat→Groq, scène→YOLO local, OCR→Tesseract. Un échec ne pollue pas la mémoire de conversation. Testé sans réseau ni SDK | `src/ai/claude_client.py`, `src/providers/ai.py`, `src/providers/vision_ai.py`, `tests/test_fallbacks.py` |
| Scène locale hors-ligne (2026-07-06) | `_local_scene` phrase via le dictionnaire darija local (`_phraser_objets` : dédoublonnage + jointure « ، ») au lieu d'un appel Groq — instantané, marche SANS Internet (dernier maillon de secours des yeux), même voix que le thread vision. Groq uniquement pour les objets hors dictionnaire | `src/providers/vision_ai.py`, `tests/test_fallbacks.py` |
| VAD webrtcvad (2026-07-06) | Détection de parole par webrtcvad (mode 2, trames 20 ms, majorité voisée + plancher volume 150) au lieu du seuil d'amplitude seul — filtre le bruit (trafic, chocs) sur micro Bluetooth HFP dégradé → moins de fausses captures/appels Whisper. Fallback automatique seuil de volume si lib absente. `MIC_DEVICE_INDEX` remplace l'index micro `1` codé en dur (`-1` = défaut système, prêt pour un futur micro USB). Sur le Pi : `pip install webrtcvad` | `src/audio/listener.py`, `config/settings.py`, `requirements.txt`, `tests/test_listener.py` |
| AutoScene toujours actif (2026-07-06) | Avant : `mode_auto_scene()` ne démarrait que si **aucun micro** n'était détecté (`elif` exclusif avec `mode_conversation()`) → avec micro, la description de scène ne se déclenchait que sur la commande vocale « شنو قدامي؟ ». Maintenant : AutoScene démarre **toujours** si `AUTO_DESCRIBE_INTERVAL > 0`, et Conversation démarre **en plus** si un micro est détecté — les deux threads tournent en parallèle (mêmes `camera_lock`/`audio_lock`/`conversation_active` qu'avant). Résultat : la caméra est décrite en détail par la voix en continu, que l'utilisateur parle ou non ; s'il parle, l'assistant répond en plus, sans jamais couper la narration. ⚠️ Coût : si `VISION_AI_PROVIDER=claude`, les appels auto continuent même avec micro — voir `.claude/skills/tune-claude/SKILL.md` | `src/core/app.py`, `src/vision/detector.py`, `config/settings.py`, `.env.example` |
| OCR dans AutoScene + intervalle 2s (2026-07-06) | `mode_auto_scene()` appelle maintenant `read_text()` en plus de `describe_scene()` à chaque cycle, sur la même capture (pas de second accès caméra). Les réponses creuses (`_OCR_SANS_RESULTAT` : aucun texte / Tesseract indisponible) sont tues pour ne pas les répéter en boucle. `read_text()`/`claude_read_text()` acceptent `remember=` (défaut `True` à la demande, `False` dans la boucle — pas un tour de dialogue, cohérent avec `describe_scene(..., hq=)`). `AUTO_DESCRIBE_INTERVAL` par défaut `5` → `2`. ⚠️ Coût doublé si `VISION_AI_PROVIDER` ET `OCR_PROVIDER` sont tous deux `claude` (2 appels/cycle) | `src/vision/detector.py`, `src/providers/ocr.py`, `src/ai/claude_client.py`, `config/settings.py`, `.env.example`, `.claude/skills/tune-claude/SKILL.md` |
| YOLO retiré, vision 100% Claude (2026-07-07) | Demande explicite : YOLO jugé trop faible en conditions réelles. Suppression de `mode_vision()` (thread YOLO continu), `_local_scene()`/`_phraser_objets()` (fallback hors-ligne), `src/vision/translations.py`, `CONF_SEUIL`, `MODEL_PATH`, `models/yolov8n.pt`, dépendance `ultralytics`, `VISION_AI_PROVIDER` (supprimée — plus qu'un seul chemin). `describe_scene()` appelle toujours Claude ; si échec/clé absente → message vocal clair (`_INDISPONIBLE`), jamais de silence mais plus de détection locale de secours. Conséquence : la description de scène **n'est plus gratuite**. Voir `.claude/memory/decisions.md` pour le détail | `src/vision/detector.py`, `src/providers/vision_ai.py`, `src/core/app.py`, `src/core/state.py`, `config/settings.py`, `requirements.txt`, `tests/test_fallbacks.py`, `tests/test_providers.py`, `tests/test_config.py` |
| Timeout client anthropic (2026-07-07) | `anthropic.Anthropic(..., timeout=15.0, max_retries=0)` — le SDK timeoutait à ~10 MIN par défaut et retryait en plus en interne (silencieusement), en amont de notre propre boucle de retry loggée. Sur réseau Pi dégradé : silence total (aucune description, aucune erreur) pendant potentiellement plusieurs minutes après le retrait de YOLO (plus de fallback local pour combler ce trou). Maintenant : échec rapide (15s) → notre retry/fallback (loggé, parlé) prend le relais en quelques dizaines de secondes max | `src/ai/claude_client.py` |
| Défauts qualité + TTS Azure (2026-07-08) | Demande explicite (présentation projet, « meilleur résultat », coût accepté) : les défauts du code passent en qualité max, le `.env` ne contient plus QUE les clés API. Nouveau provider `TTS_PROVIDER=azure` (Azure Speech REST officiel via stdlib urllib, même voix `ar-MA-JamalNeural` qu'edge-tts, tier F0 gratuit 500K car./mois, fallback edge sans clé ou en panne). Défauts : `AI_PROVIDER=claude`, `OCR_PROVIDER=claude`, `STT_MODEL=whisper-large-v3`, `CLAUDE_TEXT_MODEL`/`_HQ=claude-sonnet-5`, `CLAUDE_IMG_MAX_PX=1568`, `AUTO_DESCRIBE_INTERVAL=6`. Bascule auto vers le gratuit testée (`test_tts_azure_*`, `test_default_quality_mode`) | `src/providers/tts.py`, `config/settings.py`, `.env.example`, `tests/test_providers.py`, `tests/test_fallbacks.py` |
| Micro USB — ouverture robuste (2026-07-11) | Crash au démarrage `OSError -9997 Invalid sample rate` : `calibrer_micro()` forçait l'index 1 (périmé — les index PyAudio changent avec le matériel BT/USB) et 16 kHz (les adaptateurs jack→USB ne supportent souvent que 44.1/48 kHz). Nouveau `_ouvrir_micro(p)` : essaie (index configuré → micro par défaut) × (16 kHz → taux natif), retourne `(stream, rate)` ; toute la chaîne s'adapte au taux réel (purge/VAD/timeout/WAV — webrtcvad seulement si 8/16/32/48 kHz, sinon seuil ; Whisper accepte tous les taux). Échec total → seuil par défaut / retry 5s, JAMAIS de crash. `MIC_DEVICE_INDEX` défaut 1→`-1`. Setup matériel : micro USB (entrée) + haut-parleur Bluetooth (sortie) — supprime le couplage HFP | `src/audio/listener.py`, `config/settings.py`, `tests/test_listener.py` |
| Narration continue optimisée — décalage réduit (2026-07-11) | « Trop de silence + décalage caméra→parole ». (1) Scène et OCR de la boucle partent en **PARALLÈLE** (ThreadPoolExecutor 2 workers dans `mode_auto_scene`) : temps mort = max au lieu de la somme (~2.5s vs ~5s). (2) Boucle en **Haiku 4.5** (`CLAUDE_VISION_MODEL`) — choix de VITESSE (latence ~1.5s vs ~3-4s Sonnet), la qualité max reste sur les chemins à la demande (Opus). (3) `CLAUDE_SCENE_AUTO_MAX_TOKENS` 80→60 (~6-7s parlé) + `AUTO_DESCRIBE_INTERVAL` 2→1 → rotation ~10s, silence ≈2.5-3.5s, description fraîche (~3s entre capture et parole). Mot de réveil « مرافق » toujours écouté dans les respirations | `config/settings.py`, `src/vision/detector.py`, `tests/test_providers.py` |
| Narration quasi continue, jamais suspendue par le micro (2026-07-11) | Demande explicite « trop de silence, décris en continu sans attendre la voix » (STT inutilisable sur le matériel, tokens no-object — voir mémoire utilisateur). (1) `AUTO_DESCRIBE_INTERVAL` 8→2 : silence effectif ≈5-7s entre narrations. (2) Nouveau `VOICE_PRIORITY` (défaut 0) : `_attendre_parole_finie` n'attend plus `user_speaking` — le bruit ambiant classé « voix » par le VAD suspendait la narration (borne 20s) → longs silences. La narration n'attend QUE sa propre sortie audio (`conversation_active`). Le mécanisme priorité-voix complet est conservé, réactivable `VOICE_PRIORITY=1` quand un vrai micro rendra la STT fiable | `config/settings.py`, `src/vision/detector.py`, `tests/test_providers.py` |
| Intention devinée par Claude — filet STT (2026-07-11) | Le micro jack→USB déforme les mots (« شنو قدامي » → « كثمانين ») → la commande partait en question libre et l'assistant répondait « ما فهمتش ». Maintenant : quand AUCUN mot-clé ne matche, `claude_intention()` (Haiku, réponse d'un seul mot, ~1s, `_INTENT_SYSTEM_PROMPT` : « le STT est bruité, devine par similarité phonétique ») classe en SCENE/LIRE/AIDE/CHAT et `process_command` route (SCENE → still HQ + question par défaut). SÉCURITÉ : l'ARRÊT ne peut jamais être deviné (mot-clé exact uniquement) ; clé absente/échec → CHAT (comportement historique). Intervalle auto 15→8 (narration ~18-20s : vivant, la priorité voix `user_speaking` protège l'écoute). Testé avec classificateur simulé (`test_intention_devinee_*`) | `src/ai/claude_client.py`, `src/conversation/intents.py`, `config/settings.py`, `tests/test_intents.py`, `tests/test_providers.py` |
| Priorité voix utilisateur + intervalle 15s (2026-07-11) | « Il n'écoute pas » : à 4s la narration était quasi continue → dès que l'utilisateur commençait une phrase, AutoScene reprenait la parole et l'anti-écho ANNULAIT la capture (`Capture annulée` en boucle dans le log réel). Fix : (1) nouvel Event `state.user_speaking` — levé à la 1ʳᵉ détection de voix, reste levé pendant transcription + traitement de la commande (relâché par `mode_conversation`, try/finally + garde-fous sur tous les chemins d'erreur) ; AutoScene attend ce signal avant de capturer ET avant chaque `parler()` (`_attendre_parole_finie`, borne de sécurité 20s si signal coincé/bruit continu). (2) `AUTO_DESCRIBE_INTERVAL` 4→15 : vraies fenêtres de silence. Résultat : l'utilisateur peut parler pendant une fenêtre, sa phrase va au bout, la réponse arrive avant la reprise de la narration | `src/core/state.py`, `src/audio/listener.py`, `src/conversation/commands.py`, `src/vision/detector.py`, `config/settings.py` |
| Yeux permanents 4s + cadence AutoScene réparée (2026-07-11) | STT toujours peu fiable sur le matériel du jour de la démo → la démo ne dépend plus de la voix : `AUTO_DESCRIBE_INTERVAL` 0→4 (description continue scène + OCR). Fix cadence : la boucle SAUTAIT tout le cycle si l'assistant parlait au réveil (`continue` → re-sommeil complet → cadence réelle 2×-4× l'intervalle) ; maintenant elle ATTEND la fin de la parole (poll 0.2s) puis capture une image FRAÎCHE → narration ~toutes les (parole + 4s) | `config/settings.py`, `src/vision/detector.py`, `tests/test_providers.py` |
| Annonce vocale panne micro (2026-07-11) | L'utilisateur est NON-VOYANT : un problème micro loggé en console est invisible pour lui — il parlait dans le vide sans comprendre. Maintenant : 3 échecs micro consécutifs (~15s : ouverture ratée ou flux muet) → l'appareil DIT « كاين مشكل فالميكروفون... » (une seule fois par panne, anti-spam) ; à la première écoute complète réussie ensuite → « الميكروفون رجع خدام » ; démarrage sans micro détecté → annonce vocale aussi (`app.main()`). `_signaler_echec_micro()`/`_signaler_micro_ok()`/`_parler_securise()` (import parler lazy, jamais d'exception). Testé (`test_annonce_panne_micro_*`) | `src/audio/listener.py`, `src/core/app.py`, `tests/test_listener.py` |
| Anti-gel micro — flux muet détecté (2026-07-11) | Log réel : thread Conversation figé pour toujours sur `En attente de voix...` (plus aucun timeout 8s). Cause : un flux PyAudio peut s'OUVRIR sans erreur mais ne jamais délivrer une trame (périphérique décroché par une reconfiguration PipeWire — ex. connexion du haut-parleur Bluetooth entre la calibration et l'écoute) → `stream.read()` bloquant = gel silencieux du thread. Fix : `_flux_actif()` vérifie à l'OUVERTURE que des données arrivent (~1.2s, sinon candidat suivant : autre taux/périphérique) ; `_lire_chunk()` remplace tous les `stream.read()` (poll non-bloquant `get_read_available`, >3s muet → ferme + message + réessai au cycle suivant) ; `_fermer()` ne lève jamais. Testé avec faux flux muet (`test_flux_actif_muet`, `test_lire_chunk_muet_retourne_none`) | `src/audio/listener.py`, `tests/test_listener.py` |
| Double clé Anthropic + Opus à la demande (2026-07-08) | Demande explicite : (a) 2ᵉ clé de secours + (b) Opus pour la qualité max (coût no-object). (a) Nouveau `ANTHROPIC_API_KEY_FALLBACK` ; `claude_client._get_client(key)` (cache par clé), `_api_keys()` (principale puis secours), `_create(tag, **kwargs)` centralise retries + **bascule auto** de clé si la principale échoue (quota/invalide/panne). `claude_darija`/`_vision_call` refactorés autour de `_create` (l'image « dernière vue » n'est gardée qu'en cas de succès). (b) `CLAUDE_TEXT_MODEL` + `CLAUDE_VISION_MODEL_HQ` = `claude-opus-4-8` (OCR déjà Opus). ⚠️ Opus = +latence vocale (assumé). Boucle continue reste Sonnet 5 (Opus impraticable en continu + OFF en démo). Test `test_key_failover_principale_ko_secours_ok` | `config/settings.py`, `src/ai/claude_client.py`, `.env`, `.env.example`, `tests/test_fallbacks.py`, `tests/test_providers.py` |
| Qualité dialogue/expérience — coût no-object (2026-07-08) | Demande explicite « meilleure expérience + dialogue, tokens no-object ». Cadrage : le vrai facteur limitant est la LATENCE vocale, pas le coût → qualité là où l'utilisateur attend peu ou où la précision prime. (2) **Budgets tokens séparés** : `CLAUDE_MAX_TOKENS` 100→300 (scène à la demande + chat = riche), nouveau `CLAUDE_SCENE_AUTO_MAX_TOKENS=80` (boucle de fond = court, ne monopolise pas la parole). `claude_describe_scene` accepte `max_tokens=`, choisi dans `vision_ai._claude_scene` selon `hq`. (3) **Boucle continue Haiku→Sonnet 5** (`CLAUDE_VISION_MODEL`). (4) **Mémoire** `CONV_MEMORY_TURNS` 6→15 + **dernière image gardée** (`memory.set_last_image`/`get_last_image`, remplie sur appel vision à la demande `remember=True`) rattachée à la question chat suivante → suivi VISUEL (« شنو كانت الحاجة الزرقاء؟ »). (6) **OCR à la demande en Opus 4-8** (`CLAUDE_OCR_MODEL`, précision posologie/manuscrit ; OCR de fond reste Sonnet via `providers/ocr.py`) + `CLAUDE_IMG_QUALITY` 70→90. Streaming Claude→TTS (chantier séparé) reste le prochain gros levier de latence. Tests : `test_memory` (dernière image), `test_default_quality_mode` | `config/settings.py`, `src/ai/claude_client.py`, `src/providers/vision_ai.py`, `src/providers/ocr.py`, `src/core/memory.py`, `tests/test_memory.py`, `tests/test_providers.py` |
| Anti-écho pendant l'enregistrement + moins de bavardage (2026-07-08) | Log réel du Pi : le micro captait la voix de l'assistant (chaque « Compris » = le « Pi dit » précédent, quasi mot pour mot). Cause : `reconnaitre_voix()` ne testait `conversation_active` qu'AVANT d'ouvrir le micro ; si AutoScene se met à parler pendant l'enregistrement (fréquent), la boucle capte tout le haut-parleur et le transcrit. Fix : test de `conversation_active` À CHAQUE itération de la boucle d'enregistrement → capture jetée (« Capture annulée — l'assistant parle »). En complément (l'assistant parlait ~15-18s toutes les 6s = narration continue, aucun silence pour écouter) : `AUTO_DESCRIBE_INTERVAL` 6→10, `CLAUDE_MAX_TOKENS` 150→100. NB : la STT darija elle-même est excellente (Whisper large-v3) — le problème n'était pas la reconnaissance mais l'écho. Vrai correctif matériel = écouteurs intra (sortie) + micro USB (entrée) pour supprimer le couplage acoustique | `src/audio/listener.py`, `config/settings.py`, `tests/test_providers.py` |
| Système de logs runtime (2026-07-08) | Avant : tout partait en `print()` sur la console et disparaissait à la fermeture (rien dans `logs/`). Maintenant `setup_logging()` (appelé au début de `main()`) installe un tee sur `sys.stdout`/`stderr` : chaque `print()` de TOUS les threads est affiché ET écrit dans `logs/mourafiq_AAAAMMJJ_HHMMSS.log`, horodaté `[HH:MM:SS ThreadName]`, thread-safe (verrou → lignes entières malgré AutoScene+Conversation concurrents), flush par ligne (rien perdu sur Ctrl+C). Purge auto des vieux logs (`LOG_KEEP_FILES`, défaut 20). `LOG_TO_FILE=0` = console seule. Pour copier un log au debug : `logs/` (ignoré par git). stdlib pure, testé (`tests/test_logging.py`) | `src/core/logging_setup.py`, `src/core/app.py`, `config/settings.py`, `tests/test_logging.py`, `tests/test_config.py` |

**Activation : rien à activer** — les défauts du code SONT le mode qualité depuis 2026-07-08. `.env` = clés uniquement : `GROQ_API_KEY` (obligatoire — STT + démarrage), `ANTHROPIC_API_KEY` (obligatoire pour la vision — scène/OCR/conversation), `AZURE_SPEECH_KEY` (optionnel — TTS officiel, vide = edge-tts). Coût piloté par `AUTO_DESCRIBE_INTERVAL` (6s ≈ 600 appels scène/h, ×2 avec OCR claude) et le choix Haiku/Sonnet/Opus. Profils eco/mixte/max : `.claude/skills/tune-claude/SKILL.md`.

**Monter encore la qualité (via `.env`) :** `CLAUDE_VISION_MODEL=claude-sonnet-5` (boucle continue en Sonnet — coût ×2 sur ~600 appels/h) ou `CLAUDE_VISION_MODEL_HQ=claude-opus-4-8`. ⚠️ Opus = +latence vocale — tester avant d'adopter pour la conversation. Note : `CLAUDE_IMG_MAX_PX` > 640 n'agit que sur le still HQ (OCR + scène à la demande) ; la boucle continue reste en 640×480 (jamais agrandie → aucun surcoût).

## Changements (2026-07-09) — retrait du GPS

Le GPS a été **entièrement retiré** (décision projet : pas de navigation GPS).
Supprimé : `src/gps/` (module complet), `state.gps_serial`, constantes `GPS_*` et
`GEOCODE_*`, intentions vocales localisation/navigation (`KEYWORDS_GPS`,
`KEYWORDS_NAVIGATE`, branches صيدلية/سبيطار/جامع/محطة), dépendances `pyserial` et
`pynmea2`, tests GPS/navigation associés. Phrase d'accueil et aide vocale mises à
jour. Le README affiche la photo du projet `assets/mourafiq-medina.png` en en-tête.

## Dossier `.claude/` (agents, skills, mémoire projet)

| Ressource | Rôle |
|-----------|------|
| `.claude/agents/darija-reviewer.md` | Relecture darija (naturalité + adéquation TTS/accessibilité) |
| `.claude/agents/pi-debugger.md` | Diagnostic runtime Pi (audio/BT, caméra, erreurs API) |
| `.claude/skills/run-tests/` | Lancer la suite de tests sur Windows sans matériel |
| `.claude/skills/deploy-pi/` | Checklist déploiement Windows → Raspberry Pi |
| `.claude/skills/tune-claude/` | Profils coût/qualité Claude (eco / mixte / max) via `.env` |
| `.claude/memory/decisions.md` | Journal des décisions (le POURQUOI) — **à consulter avant de re-trancher un choix de modèle/architecture** |

## Maintenance de ce fichier (économie de tokens)

Ce CLAUDE.md est chargé dans **chaque** session. Le tenir à jour après chaque changement significatif évite aux prochaines sessions de ré-explorer le code (gros poste de tokens). Règle : après un edit notable (nouveau module, nouvelle constante config, fix de comportement), mettre à jour la table concernée ici **dans le même commit**. Rester concis — ne pas dupliquer ce que le code/les commits disent déjà.

## Known Non-Issues

- ALSA/JACK spam supprimé par `suprimer_alsa()` dans `src/audio/speaker.py`
- Traceback `Picamera2.close()` sur Ctrl+C : bug connu PiCamera2, pas fonctionnel

## Free/Cheap API Alternatives

| Besoin | Gratuit | Payant |
|--------|---------|--------|
| NLP Darija | **Groq** `llama-3.1-8b-instant` (fallback) | **Claude Sonnet 5** (défaut) |
| STT Arabe | **Groq** `whisper-large-v3` (défaut, gratuit) | OpenAI Whisper $0.006/min |
| TTS Arabe | **Azure Speech** F0 500K car./mois (défaut) ; edge-tts + gTTS (fallbacks) | ElevenLabs écarté (pas de voix darija, cher) |
| Description de scène | — (aucune option gratuite, YOLO retiré) | **Claude** (obligatoire, `ANTHROPIC_API_KEY`) |
| OCR | **Tesseract** local (défaut) | Claude (`OCR_PROVIDER=claude`) |
