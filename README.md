# Mourafiq — مرافق
### Assistant IA pour personnes malvoyantes au Maroc
**Raspberry Pi 4 | Darija marocaine | Master IT TAM UM5 2026**

---

## Présentation

Mourafiq est un assistant IA embarqué sur Raspberry Pi 4 qui aide les personnes malvoyantes à se déplacer et interagir avec leur environnement. Il répond entièrement en **darija marocaine** (arabe dialectal marocain).

**Fonctionnalités :**
- Description de scène en détail par IA (Claude vision — nécessite `ANTHROPIC_API_KEY`)
- Lecture de texte arabe et français (Tesseract OCR, ou Claude)
- Reconnaissance vocale arabe (Groq Whisper)
- Réponses en darija (Groq LLaMA 3.1)
- Navigation GPS avec instructions vocales
- Sortie audio Bluetooth (edge-tts + mpg123 + PipeWire)

---

## Structure du projet

```
mourafiq/
├── main.py                    # Point d'entrée
├── config/
│   └── settings.py            # Constantes (ports, seuils, chemins, voix)
├── src/
│   ├── core/
│   │   ├── state.py           # État partagé entre threads
│   │   └── app.py             # Initialisation matériel + boucle principale
│   ├── audio/
│   │   ├── speaker.py         # parler() — edge-tts/gTTS + mpg123
│   │   └── listener.py        # reconnaitre_voix() — VAD + Whisper
│   ├── vision/
│   │   ├── camera.py          # capturer(hq=) — capture 640×480 / still HQ
│   │   └── detector.py        # mode_auto_scene() — description auto (Claude)
│   ├── ocr/
│   │   └── reader.py          # lire_texte() — Tesseract ara+fra ou Claude
│   ├── gps/
│   │   └── location.py        # get_gps(), naviguer()
│   ├── ai/
│   │   ├── groq_client.py     # groq_darija() — LLaMA 3.1
│   │   └── claude_client.py   # claude_darija()/describe_scene()/read_text()
│   └── conversation/
│       ├── intents.py         # process_command() + constantes KEYWORDS_*
│       └── commands.py        # mode_conversation() — thread écoute
├── tests/
│   ├── test_config.py
│   └── test_intents.py
├── temp/                      # Fichiers audio temporaires (auto-créé)
└── logs/                      # Logs runtime (auto-créé)
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

### 3. Clé API Groq (gratuite)

1. Créer un compte sur [console.groq.com](https://console.groq.com)
2. **API Keys → Create API Key** (format `gsk_...`)
3. Ajouter dans `~/.bashrc` :

```bash
echo 'export GROQ_API_KEY="gsk_votre_cle"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Clé API Claude (pour la description de scène)

La description de scène et la lecture OCR détaillées nécessitent Claude — sans
clé, l'assistant continue de répondre en darija (Groq) mais dit clairement
qu'il ne peut pas voir pour l'instant, au lieu de rester muet.

1. Créer un compte sur [console.anthropic.com](https://console.anthropic.com)
2. **API Keys → Create Key** (format `sk-ant-...`)
3. Ajouter dans `.env` : `ANTHROPIC_API_KEY=sk-ant-...`, `VISION_AI_PROVIDER` n'existe
   plus (la scène passe toujours par Claude) ; `OCR_PROVIDER=claude` est optionnel
   (défaut `local` = Tesseract, gratuit).

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

---

## Commandes vocales

| Commande darija | Action |
|---|---|
| `شنو قدامي` / `شوف` / `وصف` | Décrit les objets visibles |
| `قرا ليا` / `اقرأ` | Lit le texte (OCR) |
| `وين أنا` / `فاين أنا` | Position GPS actuelle |
| `ودي للصيدلية` | Navigation vers la pharmacie |
| `ودي للسبيطار` | Navigation vers l'hôpital |
| `ودي للجامع` | Navigation vers la mosquée |
| `ودي للمحطة` | Navigation vers la gare |
| `عاونني` / `مساعدة` | Liste les commandes |
| `وقف` / `بارك` / `سلام` | Arrête l'assistant |

---

## Tests (Windows & Linux)

```bash
# Depuis la racine du projet
python3 tests/test_config.py
python3 tests/test_intents.py

# Avec pytest (si installé)
pip install pytest
pytest tests/ -v
```

---

## Dépannage

**Pas de son Bluetooth :**
```bash
systemctl --user start wireplumber pipewire pipewire-pulse
bluetoothctl connect 28:52:E0:23:61:6F
```

**Vision muette :**
- Vérifier `echo $ANTHROPIC_API_KEY` (la scène passe toujours par Claude — pas
  de détection locale de secours)
- Vérifier la connexion Internet du Pi

**Micro ne répond pas :**
- Vérifier avec `arecord -l`
- Relancer dans un environnement silencieux pour recalibration

---

## Mode gratuit vs Mode démo

Mourafiq supporte deux modes de fonctionnement configurés via `.env` :

### Mode gratuit (conversation + OCR + GPS)

Copier `.env.example` en `.env` et laisser `DEMO_MODE=free`. La conversation,
la lecture de texte (Tesseract) et le GPS restent gratuits ; la **description
de scène nécessite `ANTHROPIC_API_KEY`** (YOLO a été retiré — trop peu fiable
pour un usage réel — donc plus de détection locale gratuite de secours).

```bash
cp .env.example .env
# Remplir GROQ_API_KEY (conversation/STT) + ANTHROPIC_API_KEY (vision)
```

| Composant | Provider | Coût |
|---|---|---|
| NLP / Darija | Groq `llama-3.1-8b-instant` | Gratuit (14 400 req/jour) |
| STT Arabe | Groq `whisper-large-v3-turbo` | Gratuit (7 200 req/jour) |
| TTS Arabe | edge-tts `ar-MA-JamalNeural` | Gratuit (Microsoft) |
| Fallback TTS | gTTS | Gratuit |
| Description de scène | Claude (`ANTHROPIC_API_KEY`) | **Payant** — indispensable, pas de fallback local |
| OCR | Tesseract (local, défaut) ou Claude | Gratuit / payant selon `OCR_PROVIDER` |
| GPS | NMEA série (local) | Gratuit |

### Mode démo (ElevenLabs TTS)

Voix plus naturelle et expressive pour les présentations. Nécessite un compte ElevenLabs.

```bash
# Dans .env :
DEMO_MODE=demo
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=votre_cle_ici
ELEVENLABS_VOICE_ID=              # laisser vide = voix Adam (supporte l'arabe)
```

1. Créer un compte sur [elevenlabs.io](https://elevenlabs.io)
2. **Profile → API Key** → copier la clé
3. (Optionnel) Choisir une voix arabophone sur [lab.elevenlabs.io/voice-library](https://lab.elevenlabs.io/voice-library)
4. Installer le SDK : `pip install elevenlabs`

Si `ELEVENLABS_API_KEY` est absent ou si le quota est dépassé, le système revient automatiquement sur edge-tts sans interruption.

### Changer de provider à chaud

```bash
# Passer en mode démo
export TTS_PROVIDER=elevenlabs
export ELEVENLABS_API_KEY=sk_...
python3 main.py

# Revenir au mode gratuit
export TTS_PROVIDER=edge
python3 main.py
```

---

## API utilisées

| Service | Modèle | Quota gratuit |
|---|---|---|
| Groq NLP | `llama-3.1-8b-instant` | 14 400 req/jour |
| Groq STT | `whisper-large-v3-turbo` | 7 200 req/jour |
| edge-tts | `ar-MA-JamalNeural` | Gratuit (Microsoft) |
| gTTS | — | Gratuit (fallback) |
| ElevenLabs | `eleven_multilingual_v2` | Payant (mode démo) |
