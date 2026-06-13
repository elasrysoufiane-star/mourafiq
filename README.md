# Mourafiq — مرافق
### Assistant IA pour personnes malvoyantes au Maroc
**Raspberry Pi 4 | Darija marocaine | Master IT TAM UM5 2026**

---

## Présentation

Mourafiq est un assistant IA embarqué sur Raspberry Pi 4 qui aide les personnes malvoyantes à se déplacer et interagir avec leur environnement. Il répond entièrement en **darija marocaine** (arabe dialectal marocain).

**Fonctionnalités :**
- Détection d'objets en temps réel (YOLOv8n)
- Lecture de texte arabe et français (Tesseract OCR)
- Reconnaissance vocale en arabe (Groq Whisper)
- Réponses en darija (Groq LLaMA 3.1)
- Navigation GPS avec instructions vocales
- Sortie audio via Bluetooth (mpg123 + PipeWire)

---

## Installation sur Raspberry Pi

### 1. Prérequis système

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra mpg123 python3-picamera2
```

### 2. Environnement virtuel

```bash
python3 -m venv /home/som/projet_ia
source /home/som/projet_ia/bin/activate
pip install -r requirements.txt
```

### 3. Clé API Groq (gratuite)

1. Créer un compte sur [console.groq.com](https://console.groq.com)
2. Aller dans **API Keys** → **Create API Key**
3. Copier la clé (format `gsk_...`)

```bash
echo 'export GROQ_API_KEY="gsk_votre_cle_ici"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Modèle YOLO

```bash
cd ~/mourafiq
git lfs pull          # télécharge yolov8n.pt via Git LFS
# Optionnel : déplacer dans models/
mkdir -p models && mv yolov8n.pt models/
```

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
| `شنو قدامي` / `شوف` | Décrit les objets devant la caméra |
| `قرا ليا` | Lit le texte visible (OCR) |
| `وين أنا` / `فاين أنا` | Indique la position GPS actuelle |
| `ودي للصيدلية` | Navigation vers la pharmacie |
| `ودي للسبيطار` | Navigation vers l'hôpital |
| `ودي للجامع` | Navigation vers la mosquée |
| `ودي للمحطة` | Navigation vers la gare |
| `عاونني` / `مساعدة` | Liste les commandes disponibles |
| `وقف` / `سلام` | Arrête l'assistant |

---

## Structure du projet

```
mourafiq/
├── main.py          # Point d'entrée — init + threads
├── config.py        # Constantes (ports, seuils, chemins)
├── state.py         # État partagé entre threads (locks, caméra, modèle)
├── audio.py         # parler() — edge-tts/gTTS + mpg123
├── vision.py        # Thread YOLO — détection continue
├── conversation.py  # Thread micro — écoute et dispatch
├── intents.py       # Routage des commandes vocales
├── groq_service.py  # groq_darija() + reconnaitre_voix()
├── ocr_reader.py    # Tesseract OCR
├── gps.py           # GPS série + navigation
├── translations.py  # Classes YOLO → phrases darija
├── requirements.txt
├── models/          # yolov8n.pt (optionnel, sinon racine)
├── temp/            # Fichiers audio temporaires (auto-créé)
└── logs/            # Logs (auto-créé)
```

---

## Dépannage

**Pas de son Bluetooth :**
```bash
systemctl --user start wireplumber pipewire pipewire-pulse
bluetoothctl connect 28:52:E0:23:61:6F
pactl list sinks short
```

**Vision ne détecte rien :**
- Vérifier que `GROQ_API_KEY` est défini (`echo $GROQ_API_KEY`)
- Réduire `CONF_SEUIL` à `0.45` dans `config.py`

**Micro ne répond pas :**
- Vérifier avec `arecord -l` que le micro est détecté
- Relancer `main.py` dans un environnement silencieux pour une meilleure calibration

**Quota Groq dépassé :**
- Groq offre 14 400 req/jour (LLM) et 7 200 req/jour (Whisper) gratuitement
- Vérifier l'utilisation sur [console.groq.com](https://console.groq.com)

---

## API utilisées

| Service | Modèle | Quota gratuit |
|---|---|---|
| Groq NLP | `llama-3.1-8b-instant` | 14 400 req/jour |
| Groq STT | `whisper-large-v3-turbo` | 7 200 req/jour |
| edge-tts TTS | `ar-MA-JamalNeural` | Gratuit (Microsoft) |
| gTTS (fallback) | — | Gratuit (Google) |
