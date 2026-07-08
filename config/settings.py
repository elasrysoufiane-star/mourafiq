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
# Défauts = MEILLEURE QUALITÉ (décision 2026-07-08, assistant pour malvoyant) :
# le .env ne contient que les clés API, toute la config vit ici. Sans clé, chaque
# provider retombe automatiquement sur le gratuit (claude→groq, azure→edge,
# OCR claude→Tesseract) — l'app tourne toujours, jamais de silence.
DEMO_MODE    = os.environ.get('DEMO_MODE',    'free')
AI_PROVIDER  = os.environ.get('AI_PROVIDER',  'claude') # claude (défaut, fallback groq) | groq | openai | ollama
STT_PROVIDER = os.environ.get('STT_PROVIDER', 'groq')   # groq | openai
TTS_PROVIDER = os.environ.get('TTS_PROVIDER', 'azure')  # azure (défaut, fallback edge) | edge | gtts | elevenlabs
# OCR : 'claude' = lecture par Claude vision (arabe/français/manuscrit, défaut,
# fallback Tesseract). 'local' = Tesseract + Groq (gratuit, hors-ligne).
OCR_PROVIDER = os.environ.get('OCR_PROVIDER', 'claude') # claude | local

# Modèle STT Groq. Défaut = whisper-large-v3 (meilleure transcription darija,
# gratuit sur Groq). STT_MODEL=whisper-large-v3-turbo si la vitesse prime.
STT_MODEL = os.environ.get('STT_MODEL', 'whisper-large-v3')

OLLAMA_URL   = os.environ.get('OLLAMA_URL',   'http://127.0.0.1:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'mistral')

# ── Clés API optionnelles (payant — laisser vide si non utilisé) ──────────────
# Azure Speech — TTS officiel : même voix marocaine ar-MA-JamalNeural qu'edge-tts
# (catalogue identique), API stable avec SLA. Tier F0 GRATUIT : 500K car./mois,
# largement assez pour l'usage quotidien. portal.azure.com → « Speech service ».
# Clé vide = fallback automatique edge-tts (même voix, non officiel).
AZURE_SPEECH_KEY    = os.environ.get('AZURE_SPEECH_KEY',    '')
AZURE_SPEECH_REGION = os.environ.get('AZURE_SPEECH_REGION', 'westeurope')
ELEVENLABS_API_KEY  = os.environ.get('ELEVENLABS_API_KEY',  '')
# Voice ID depuis lab.elevenlabs.io/voice-library — vide = voix par défaut (Adam)
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', '')
OPENAI_API_KEY      = os.environ.get('OPENAI_API_KEY',      '')

# ── Claude (Anthropic) — cerveau vision+langage à la demande ──────────────────
# Clé sur console.anthropic.com (format sk-ant-...). Vide = fallback Groq/local.
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
# Modèles — stratégie MIXTE par défaut (decisions.md 2026-07-06/08) :
# Sonnet 5 partout à la demande (conversation, « شنو قدامي؟ », OCR — qualité,
# $2/$10 par 1M en intro jusqu'au 31/08/2026), Haiku 4.5 pour la boucle
# continue AutoScene ($1/$5 par 1M — 600 appels/h à 6s, le coût est là).
# Opus 4-8 écarté pour la conversation : latence vocale trop pénalisante.
CLAUDE_TEXT_MODEL   = os.environ.get('CLAUDE_TEXT_MODEL',   'claude-sonnet-5')
CLAUDE_VISION_MODEL = os.environ.get('CLAUDE_VISION_MODEL', 'claude-haiku-4-5')
# Modèle vision « haute qualité » pour les appels À LA DEMANDE (question vocale
# « شنو قدامي؟ », lecture OCR) — réponse plus fine. La boucle auto continue,
# elle, utilise CLAUDE_VISION_MODEL (moins cher).
CLAUDE_VISION_MODEL_HQ = os.environ.get('CLAUDE_VISION_MODEL_HQ', 'claude-sonnet-5')
# Optimisation tokens : réponse parlée donc courte ; image redimensionnée +
# compressée avant envoi (les tokens image montent avec la résolution).
CLAUDE_MAX_TOKENS  = int(os.environ.get('CLAUDE_MAX_TOKENS',  '150'))
# La lecture OCR a besoin de plus de place qu'une description de scène
# (rentre une lettre / notice entière) → plafond séparé, plus large.
CLAUDE_OCR_MAX_TOKENS = int(os.environ.get('CLAUDE_OCR_MAX_TOKENS', '400'))
# 1568 = lettre/notice lisible sur le still HQ (~2400 tokens ≈ $0.005/lecture
# en sonnet-5). Sans effet sur la boucle continue (source 640px, jamais agrandie).
CLAUDE_IMG_MAX_PX  = int(os.environ.get('CLAUDE_IMG_MAX_PX',  '1568'))
CLAUDE_IMG_QUALITY = int(os.environ.get('CLAUDE_IMG_QUALITY', '70'))
# Capture still HAUTE RÉSOLUTION (pleine résolution capteur) pour l'OCR et la
# scène à la demande, via switch_mode (~0.5-1s, ponctuel). La boucle AutoScene
# garde le flux 640×480. 0 = désactivé (tout en 640×480, comportement d'avant).
# Monter CLAUDE_IMG_MAX_PX (.env) pour que le still profite vraiment au VLM.
HQ_CAPTURE_ENABLED = os.environ.get('HQ_CAPTURE_ENABLED', '1') not in ('0', 'false', 'False', '')
# Anti double-appel : réutilise la dernière description si < N secondes.
VISION_COOLDOWN    = float(os.environ.get('VISION_COOLDOWN', '3'))
# Description automatique de scène (Claude) + lecture OCR, TOUJOURS active
# (avec ou sans micro, que l'utilisateur parle ou non) — tourne en parallèle
# de la conversation. Toutes les N secondes : capture → describe_scene() +
# read_text() → parle. 0 = désactivé.
# La scène nécessite ANTHROPIC_API_KEY (pas de fallback local, YOLO retiré).
# Attention coût (≈600 appels/h à 6s pour la scène, × 2 si OCR_PROVIDER=claude
# aussi) — voir CLAUDE.md.
AUTO_DESCRIBE_INTERVAL = float(os.environ.get('AUTO_DESCRIBE_INTERVAL', '6'))

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

# ── Logs runtime ──────────────────────────────────────────────────────────────
# Capture TOUTE la sortie console (tous les print(), tous les threads) dans
# logs/mourafiq_AAAAMMJJ_HHMMSS.log, horodatée + nom du thread — pour déboguer
# (latences, timeouts API, ordre des threads) et copier le log facilement.
# LOG_TO_FILE=0 → console seule (comportement d'avant). LOG_KEEP_FILES = nombre
# de fichiers log gardés (les plus anciens sont supprimés → carte SD du Pi).
LOG_TO_FILE    = os.environ.get('LOG_TO_FILE', '1') not in ('0', 'false', 'False', '')
LOG_KEEP_FILES = int(os.environ.get('LOG_KEEP_FILES', '20'))

# ── Chemins fichiers audio temporaires ───────────────────────────────────────
AUDIO_MP3 = str(BASE_DIR / 'temp' / 'audio.mp3')
AUDIO_WAV = str(BASE_DIR / 'temp' / 'audio.wav')

# ── Text-to-Speech ────────────────────────────────────────────────────────────
# Voix marocaine (homme), utilisée par Azure Speech ET edge-tts (même catalogue).
# Alternatives :
#   ar-MA-MounaNeural (femme marocaine)
#   ar-EG-SalmaNeural (femme égyptienne)
EDGE_VOICE = 'ar-MA-JamalNeural'

# ── Reconnaissance vocale ─────────────────────────────────────────────────────
# Timeout d'écoute micro : 8s sans voix → retour automatique
# 16000 samples/s ÷ 1024 samples/chunk × 8s ≈ 125 chunks
TIMEOUT_ECOUTE = int(8 * 16000 / 1024)

# Index PyAudio du micro. 1 = périphérique pipewire (défaut historique du Pi).
# -1 = laisser PyAudio choisir le micro par défaut du système — à utiliser
# quand un micro USB sera branché (les index changent avec les périphériques).
MIC_DEVICE_INDEX = int(os.environ.get('MIC_DEVICE_INDEX', '1'))

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
# chat et la vision À LA DEMANDE (la boucle AutoScene de fond ne l'alimente pas).
# 0 = sans mémoire (chaque tour isolé, comportement précédent). Plus haut = plus
# de contexte mais plus de tokens par appel.
CONV_MEMORY_TURNS = int(os.environ.get('CONV_MEMORY_TURNS', '6'))
