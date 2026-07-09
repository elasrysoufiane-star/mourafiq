<p align="center">
  <img src="assets/mourafiq-medina.png" alt="Mourafiq IA — مرافق : utilisateur portant la caméra pectorale Mourafiq dans une médina marocaine" width="100%">
</p>

# Mourafiq — مرافق
### Assistant IA pour personnes malvoyantes au Maroc
**Raspberry Pi 4 | Darija marocaine | Master IT TAM UM5 2026**

---

## Présentation

Mourafiq est un assistant IA embarqué sur Raspberry Pi 4 qui aide les personnes malvoyantes à comprendre leur environnement et interagir avec lui. Il répond entièrement en **darija marocaine** (arabe dialectal marocain).

**Fonctionnalités :**
- Description détaillée de la scène par IA (Claude vision — nécessite `ANTHROPIC_API_KEY`)
- Description automatique en continu (AutoScene : scène + texte visible, toutes les 10 s)
- Lecture de texte arabe et français (Claude par défaut, fallback Tesseract OCR local)
- Reconnaissance vocale arabe (Groq Whisper large-v3 + VAD webrtcvad)
- Conversation en darija (Claude Sonnet, fallback Groq LLaMA 3.1)
- Mot de réveil « مرافق » + fenêtre de suivi pour enchaîner les questions
- Mémoire de conversation (questions de suivi, dernière image gardée)
- Synthèse vocale marocaine `ar-MA-JamalNeural` (Azure Speech, fallback edge-tts/gTTS)
- Sortie audio Bluetooth (mpg123 + PipeWire)
- Logs runtime horodatés dans `logs/` pour le débogage

---

## Structure du projet

```
mourafiq/
├── main.py                    # Point d'entrée → src.core.app.main()
├── config/
│   └── settings.py            # Toutes les constantes de configuration
├── src/
│   ├── core/
│   │   ├── state.py           # État partagé entre threads (locks, matériel)
│   │   ├── memory.py          # Mémoire de conversation (texte + dernière image)
│   │   ├── logging_setup.py   # Tee console → logs/mourafiq_*.log horodaté
│   │   └── app.py             # init() + main() — matériel lazy-loaded
│   ├── audio/
│   │   ├── speaker.py         # parler() — TTS + mpg123
│   │   ├── listener.py        # reconnaitre_voix() — VAD webrtcvad + Whisper
│   │   └── text_clean.py      # Nettoyage Markdown avant synthèse vocale
│   ├── vision/
│   │   ├── camera.py          # capturer(hq=) — flux 640×480 ou still pleine résolution
│   │   └── detector.py        # mode_auto_scene() — description auto (scène + OCR)
│   ├── ocr/
│   │   └── reader.py          # lire_texte() — capture + providers.ocr
│   ├── ai/
│   │   ├── groq_client.py     # groq_darija() — LLaMA 3.1 (fallback gratuit)
│   │   └── claude_client.py   # claude_darija()/describe_scene()/read_text() — VLM
│   ├── providers/             # Couche de routage configurable via .env
│   │   ├── ai.py              # get_ai_response() — claude/groq/openai
│   │   ├── stt.py             # transcribe() — groq/openai
│   │   ├── tts.py             # synthesize() — azure/edge/gtts/elevenlabs
│   │   ├── vision_ai.py       # describe_scene() — 100% Claude
│   │   └── ocr.py             # read_text() — claude/local (Tesseract)
│   └── conversation/
│       ├── intents.py         # process_command() + constantes KEYWORDS_*
│       └── commands.py        # mode_conversation() — thread écoute
├── assets/                    # Photo du projet (README)
├── tests/                     # Tests unitaires (Windows/Linux, sans matériel)
├── temp/                      # Fichiers audio temporaires (auto-créé)
└── logs/                      # Logs runtime horodatés (auto-créé)
```

---

## Installation sur Raspberry Pi

### 1. Prérequis système

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra \
                   mpg123 python3-picamera2
```

### 2. Environnement virtuel

```bash
python3 -m venv /home/som/projet_ia
source /home/som/projet_ia/bin/activate
pip install -r requirements.txt
```

### 3. Clés API

Copier `.env.example` en `.env` et remplir les clés :

```bash
cp .env.example .env
```

| Clé | Obligatoire | Rôle | Où l'obtenir |
|---|---|---|---|
| `GROQ_API_KEY` | **Oui** | STT Whisper + fallback conversation | [console.groq.com](https://console.groq.com) (gratuit) |
| `ANTHROPIC_API_KEY` | **Oui pour la vision** | Description de scène, OCR, conversation | [console.anthropic.com](https://console.anthropic.com) |
| `AZURE_SPEECH_KEY` | Non | TTS officiel (tier F0 gratuit 500K car./mois) ; vide = edge-tts | [portal.azure.com](https://portal.azure.com) |

Sans `ANTHROPIC_API_KEY`, l'assistant continue de discuter (Groq) et de lire
(Tesseract), mais annonce clairement à l'oral qu'il ne peut pas décrire la
scène — il ne reste jamais muet.

---

## Démarrage

```bash
source /home/som/projet_ia/bin/activate
cd ~/mourafiq

# Bluetooth (oraimo SpaceBuds Air)
bluetoothctl connect 28:52:E0:23:61:6F
pactl set-default-sink $(pactl list sinks short | grep bluez | awk '{print $2}')

python3 main.py
```

Au démarrage, l'assistant se présente puis :
- **AutoScene** décrit la scène et lit le texte visible toutes les 10 s (`AUTO_DESCRIBE_INTERVAL`), avec ou sans micro ;
- **Conversation** s'active en plus si un micro est détecté — dire « **مرافق** » (mot de réveil) puis la commande.

---

## Commandes vocales

| Commande darija | Action |
|---|---|
| `مرافق` | Mot de réveil (puis fenêtre de suivi de 15 s) |
| `شنو قدامي` / `شوف` / `وصف` | Décrit la scène en détail (Claude vision HQ) |
| `قرا ليا` / `اقرأ` | Lit le texte visible (OCR) |
| `عاونني` / `مساعدة` | Liste les commandes |
| `وقف` / `بارك` / `بسلامة` | Arrête l'assistant |
| Toute autre question | Réponse libre en darija (Claude, fallback Groq) |

---

## Providers et configuration

Défauts du code = **meilleure qualité** ; chaque brique retombe automatiquement
sur le gratuit si la clé manque ou si l'appel échoue (jamais de crash) :

| Composant | Défaut | Fallback | Variable `.env` |
|---|---|---|---|
| Conversation | Claude `claude-sonnet-5` | Groq `llama-3.1-8b-instant` (gratuit) | `AI_PROVIDER` |
| Description de scène | Claude (Haiku/Sonnet selon contexte) | Message vocal clair (pas de fallback local) | — |
| OCR | Claude | Tesseract local (gratuit) | `OCR_PROVIDER` |
| STT | Groq `whisper-large-v3` | — | `STT_PROVIDER`, `STT_MODEL` |
| TTS | Azure Speech `ar-MA-JamalNeural` | edge-tts → gTTS (gratuits) | `TTS_PROVIDER` |

Réglages utiles dans `.env` : `AUTO_DESCRIBE_INTERVAL` (coût/fréquence de la
description auto ; `0` = désactivée), `CLAUDE_VISION_MODEL`,
`CLAUDE_VISION_MODEL_HQ`, `CLAUDE_IMG_MAX_PX`. Voir `config/settings.py`
pour la liste complète commentée.

---

## Tests (Windows & Linux, sans matériel)

```bash
pip install pytest
pytest tests/ -v

# Ou individuellement
python3 tests/test_config.py
python3 tests/test_intents.py
python3 tests/test_providers.py
python3 tests/test_fallbacks.py
```

---

## Dépannage

**Pas de son Bluetooth :**
```bash
systemctl --user start wireplumber pipewire pipewire-pulse
bluetoothctl connect 28:52:E0:23:61:6F
```

**Vision muette :**
- Vérifier `ANTHROPIC_API_KEY` dans `.env` (la scène passe toujours par Claude)
- Vérifier la connexion Internet du Pi
- Consulter le dernier log dans `logs/`

**Micro ne répond pas :**
- Vérifier avec `arecord -l`
- Relancer dans un environnement silencieux pour recalibration
- Dire le mot de réveil « مرافق » avant la commande

---

## API utilisées

| Service | Modèle | Coût |
|---|---|---|
| Claude (Anthropic) | `claude-sonnet-5` (conversation/vision/OCR) | Payant |
| Groq NLP | `llama-3.1-8b-instant` | Gratuit (14 400 req/jour) |
| Groq STT | `whisper-large-v3` | Gratuit (7 200 req/jour) |
| Azure Speech TTS | `ar-MA-JamalNeural` | Gratuit (tier F0, 500K car./mois) |
| edge-tts / gTTS | `ar-MA-JamalNeural` / — | Gratuit (fallback) |
| ElevenLabs | `eleven_multilingual_v2` | Payant (option `TTS_PROVIDER=elevenlabs`) |
