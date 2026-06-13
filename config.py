import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Clé API Groq — jamais dans le code, toujours via variable d'environnement
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# GPS
GPS_PORT = '/dev/ttyS0'
GPS_BAUD = 9600

# Fichiers audio temporaires (créés par main.py au démarrage)
AUDIO_MP3 = str(BASE_DIR / 'temp' / 'audio.mp3')
AUDIO_WAV = str(BASE_DIR / 'temp' / 'audio.wav')

# Seuil de confiance YOLO — réduit à 0.50 pour mieux détecter
# Tester 0.45 si des objets réels sont encore trop souvent ratés
CONF_SEUIL = 0.50

# Voix edge-tts marocaine (ar-MA-JamalNeural = homme marocain)
# Alternatives: ar-MA-MounaNeural (femme), ar-EG-SalmaNeural (égyptien)
EDGE_VOICE = 'ar-MA-JamalNeural'

# Timeout écoute micro : 30s sans voix → retour automatique
# 16000 samples/s ÷ 1024 samples/chunk × 30s ≈ 468 chunks
TIMEOUT_ECOUTE = int(30 * 16000 / 1024)

# Chemin modèle YOLO — supporte models/ ou racine du projet
_model_new  = BASE_DIR / 'models' / 'yolov8n.pt'
_model_root = BASE_DIR / 'yolov8n.pt'
MODEL_PATH  = str(_model_new if _model_new.exists() else _model_root)
