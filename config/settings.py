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
AI_PROVIDER  = os.environ.get('AI_PROVIDER',  'groq')   # groq | openai | claude | ollama
STT_PROVIDER = os.environ.get('STT_PROVIDER', 'groq')   # groq | openai
TTS_PROVIDER = os.environ.get('TTS_PROVIDER', 'edge')   # edge | gtts | elevenlabs
# OCR : 'local' = Tesseract + Groq (gratuit, hors-ligne, défaut).
# 'claude' = lecture par Claude vision (arabe/français/manuscrit), fallback Tesseract.
OCR_PROVIDER = os.environ.get('OCR_PROVIDER', 'local')  # local | claude

# Modèle STT Groq. Défaut = turbo (rapide, gratuit). Pour la précision max :
# STT_MODEL=whisper-large-v3 (un peu plus lent, meilleure transcription darija).
STT_MODEL = os.environ.get('STT_MODEL', 'whisper-large-v3-turbo')

# Provider de compréhension de scène (VLM, appelé UNIQUEMENT à la demande).
# 'local' = YOLO + Groq (gratuit, défaut). 'claude' = Claude multimodal (payant).
# Fallback automatique vers 'local' si ANTHROPIC_API_KEY absente.
VISION_AI_PROVIDER = os.environ.get('VISION_AI_PROVIDER', 'local')  # local | claude

OLLAMA_URL   = os.environ.get('OLLAMA_URL',   'http://127.0.0.1:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'mistral')

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
# Modèle vision « haute qualité » pour les appels À LA DEMANDE (question vocale
# « شنو قدامي؟ », lecture OCR) — réponse plus fine. La boucle auto continue, elle,
# utilise CLAUDE_VISION_MODEL (moins cher). Défaut = même modèle (aucun surcoût
# tant qu'on ne le règle pas sur sonnet/opus dans .env).
CLAUDE_VISION_MODEL_HQ = os.environ.get('CLAUDE_VISION_MODEL_HQ', CLAUDE_VISION_MODEL)
# Optimisation tokens : réponse parlée donc courte ; image redimensionnée +
# compressée avant envoi (les tokens image montent avec la résolution).
CLAUDE_MAX_TOKENS  = int(os.environ.get('CLAUDE_MAX_TOKENS',  '150'))
# La lecture OCR a besoin de plus de place qu'une description de scène
# (rentre une lettre / notice entière) → plafond séparé, plus large.
CLAUDE_OCR_MAX_TOKENS = int(os.environ.get('CLAUDE_OCR_MAX_TOKENS', '400'))
CLAUDE_IMG_MAX_PX  = int(os.environ.get('CLAUDE_IMG_MAX_PX',  '768'))
CLAUDE_IMG_QUALITY = int(os.environ.get('CLAUDE_IMG_QUALITY', '70'))
# Capture still HAUTE RÉSOLUTION (pleine résolution capteur) pour l'OCR et la
# scène à la demande, via switch_mode (~0.5-1s, ponctuel). La boucle YOLO garde
# le flux 640×480. 0 = désactivé (tout en 640×480, comportement d'avant).
# Monter CLAUDE_IMG_MAX_PX (.env) pour que le still profite vraiment au VLM.
HQ_CAPTURE_ENABLED = os.environ.get('HQ_CAPTURE_ENABLED', '1') not in ('0', 'false', 'False', '')
# Anti double-appel : réutilise la dernière description si < N secondes.
VISION_COOLDOWN    = float(os.environ.get('VISION_COOLDOWN', '3'))
# Description automatique de scène en mode SANS MICRO (pas de commande vocale).
# Toutes les N secondes : capture → describe_scene() → parle. 0 = désactivé.
# Pour utiliser Claude ici : VISION_AI_PROVIDER=claude + ANTHROPIC_API_KEY.
# Attention coût si provider=claude (≈720 appels/h à 5s) — voir CLAUDE.md.
AUTO_DESCRIBE_INTERVAL = float(os.environ.get('AUTO_DESCRIBE_INTERVAL', '5'))

# ── GPS ───────────────────────────────────────────────────────────────────────
# Surchargeable via .env (cohérent avec le reste de la config).
GPS_PORT = os.environ.get('GPS_PORT', '/dev/ttyS0')
GPS_BAUD = int(os.environ.get('GPS_BAUD', '9600'))
# Durée max de lecture des trames NMEA avant abandon (évite de bloquer le thread).
GPS_READ_TIMEOUT = float(os.environ.get('GPS_READ_TIMEOUT', '3'))
# Reverse geocoding : convertit lat/lon → adresse parlable (rue, quartier, ville)
# via OpenStreetMap Nominatim (gratuit, pas de clé, nécessite Internet).
# 0 → désactivé : on annonce alors les coordonnées brutes (comportement précédent).
GEOCODE_ENABLED = os.environ.get('GEOCODE_ENABLED', '1') not in ('0', 'false', 'False', '')
GEOCODE_TIMEOUT = float(os.environ.get('GEOCODE_TIMEOUT', '5'))

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

# ── Mémoire de conversation ───────────────────────────────────────────────────
# Nombre de tours (échange user+assistant) gardés en contexte et renvoyés à
# Claude → permet une vraie discussion avec questions de suivi : « وزيد على
# اليسار؟ », « عاود », « زيدني تفاصيل », sans tout réexpliquer. Partagée entre le
# chat et la vision À LA DEMANDE (la boucle auto sans micro ne l'alimente pas).
# 0 = sans mémoire (chaque tour isolé, comportement précédent). Plus haut = plus
# de contexte mais plus de tokens par appel.
CONV_MEMORY_TURNS = int(os.environ.get('CONV_MEMORY_TURNS', '6'))
