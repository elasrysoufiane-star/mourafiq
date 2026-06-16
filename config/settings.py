import os
from pathlib import Path

# Charge automatiquement le fichier .env s'il existe (python-dotenv optionnel)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # sans python-dotenv : utiliser export ou .bashrc manuellement

# Racine du projet (parent de config/)
BASE_DIR = Path(__file__).parent.parent

# ── Groq API ──────────────────────────────────────────────────────────────────
# Ne jamais mettre la clé directement ici — utiliser une variable d'environnement.
# Sur le Pi : echo 'export GROQ_API_KEY="gsk_..."' >> ~/.bashrc
# .get() permet d'importer ce module sans la clé (utile pour les tests)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ── Mode et providers ─────────────────────────────────────────────────────────
# DEMO_MODE : 'free' (défaut) ou 'demo' (documentation uniquement, pas de logique)
DEMO_MODE    = os.environ.get('DEMO_MODE',    'free')
AI_PROVIDER  = os.environ.get('AI_PROVIDER',  'groq')   # groq | openai | claude
STT_PROVIDER = os.environ.get('STT_PROVIDER', 'groq')   # groq | openai
TTS_PROVIDER = os.environ.get('TTS_PROVIDER', 'edge')   # edge | gtts | elevenlabs

# Modèle STT Groq. Défaut = turbo (rapide, gratuit). Pour la précision max :
# STT_MODEL=whisper-large-v3 (un peu plus lent, meilleure transcription darija).
STT_MODEL = os.environ.get('STT_MODEL', 'whisper-large-v3-turbo')

# Provider de compréhension de scène (VLM, appelé UNIQUEMENT à la demande).
# 'local' = YOLO + Groq (gratuit, défaut). 'claude' = Claude multimodal (payant).
# Fallback automatique vers 'local' si ANTHROPIC_API_KEY absente.
VISION_AI_PROVIDER = os.environ.get('VISION_AI_PROVIDER', 'local')  # local | claude

# ── Clés API optionnelles (payant — laisser vide si non utilisé) ──────────────
ELEVENLABS_API_KEY  = os.environ.get('ELEVENLABS_API_KEY',  '')
# Voice ID depuis lab.elevenlabs.io/voice-library — vide = voix par défaut (Adam)
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', '')
OPENAI_API_KEY      = os.environ.get('OPENAI_API_KEY',      '')

# ── Claude (Anthropic) — cerveau vision+langage à la demande ──────────────────
# Clé sur console.anthropic.com (format sk-ant-...). Vide = fallback Groq/local.
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
# Modèles. Haiku 4.5 = défaut (multimodal, rapide, le moins cher : $1/$5 par 1M).
# Pour la qualité max : CLAUDE_VISION_MODEL=claude-opus-4-8 ($5/$25 par 1M).
CLAUDE_TEXT_MODEL   = os.environ.get('CLAUDE_TEXT_MODEL',   'claude-haiku-4-5')
CLAUDE_VISION_MODEL = os.environ.get('CLAUDE_VISION_MODEL', 'claude-haiku-4-5')
# Optimisation tokens : réponse parlée donc courte ; image redimensionnée +
# compressée avant envoi (les tokens image montent avec la résolution).
CLAUDE_MAX_TOKENS  = int(os.environ.get('CLAUDE_MAX_TOKENS',  '150'))
CLAUDE_IMG_MAX_PX  = int(os.environ.get('CLAUDE_IMG_MAX_PX',  '768'))
CLAUDE_IMG_QUALITY = int(os.environ.get('CLAUDE_IMG_QUALITY', '70'))
# Anti double-appel : réutilise la dernière description si < N secondes.
VISION_COOLDOWN    = float(os.environ.get('VISION_COOLDOWN', '3'))

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

# ── Mot de réveil (wake word) ─────────────────────────────────────────────────
# L'appareil n'exécute une commande qu'après avoir entendu son nom (« مرافق »),
# puis reste à l'écoute WAKE_FOLLOWUP_WINDOW secondes (fenêtre de suivi) — tu peux
# enchaîner plusieurs questions sans répéter le mot. Évite les fausses commandes
# (écho, bruit, hallucinations Whisper). WAKE_WORD_ENABLED=0 → écoute continue.
WAKE_WORD_ENABLED    = os.environ.get('WAKE_WORD_ENABLED', '1') not in ('0', 'false', 'False', '')
WAKE_FOLLOWUP_WINDOW = float(os.environ.get('WAKE_FOLLOWUP_WINDOW', '15'))
