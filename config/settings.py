import os
from pathlib import Path

# Racine du projet (parent de config/)
BASE_DIR = Path(__file__).parent.parent

# ── Groq API ──────────────────────────────────────────────────────────────────
# Ne jamais mettre la clé directement ici — utiliser une variable d'environnement.
# Sur le Pi : echo 'export GROQ_API_KEY="gsk_..."' >> ~/.bashrc
# .get() permet d'importer ce module sans la clé (utile pour les tests)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ── GPS ───────────────────────────────────────────────────────────────────────
GPS_PORT = '/dev/ttyS0'
GPS_BAUD = 9600

# ── Chemins fichiers audio temporaires ───────────────────────────────────────
AUDIO_MP3 = str(BASE_DIR / 'temp' / 'audio.mp3')
AUDIO_WAV = str(BASE_DIR / 'temp' / 'audio.wav')

# ── Modèle YOLO ───────────────────────────────────────────────────────────────
MODEL_PATH = str(BASE_DIR / 'models' / 'yolov8n.pt')

# ── Détection d'objets ────────────────────────────────────────────────────────
# Seuil de confiance YOLO — abaissé à 0.50 pour mieux détecter les objets
# Tester 0.45 si des objets réels sont encore trop souvent ratés
CONF_SEUIL = 0.50

# ── Text-to-Speech ────────────────────────────────────────────────────────────
# Voix edge-tts marocaine (homme). Alternatives :
#   ar-MA-MounaNeural (femme marocaine)
#   ar-EG-SalmaNeural (femme égyptienne)
EDGE_VOICE = 'ar-MA-JamalNeural'

# ── Reconnaissance vocale ─────────────────────────────────────────────────────
# Timeout d'écoute micro : 8s sans voix → retour automatique
# 16000 samples/s ÷ 1024 samples/chunk × 8s ≈ 125 chunks
TIMEOUT_ECOUTE = int(8 * 16000 / 1024)
