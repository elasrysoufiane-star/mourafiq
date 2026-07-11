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
# Clé de SECOURS : si la PRINCIPALE échoue (quota épuisé, clé invalide/expirée,
# panne réseau/API), les appels Claude basculent AUTOMATIQUEMENT dessus, sans
# rien couper (voir claude_client._create). Vide = pas de secours. 2ᵉ clé sk-ant-.
ANTHROPIC_API_KEY_FALLBACK = os.environ.get('ANTHROPIC_API_KEY_FALLBACK', '')
# Modèles — priorité QUALITÉ MAX (demande explicite, coût no-object, présentation).
# Opus 4-8 sur TOUS les chemins À LA DEMANDE : conversation, « شنو قدامي؟ », OCR.
# ⚠️ Opus = +latence vocale (quelques secondes de plus par réponse) — assumé pour
# la qualité. La boucle CONTINUE reste Sonnet 5 (Opus impraticable à ~600 appels/h ;
# de toute façon la boucle est OFF en mode démo, AUTO_DESCRIBE_INTERVAL=0).
CLAUDE_TEXT_MODEL   = os.environ.get('CLAUDE_TEXT_MODEL',   'claude-opus-4-8')
# Boucle continue AutoScene (si réactivée) : Sonnet 5 — Opus trop lent en continu.
CLAUDE_VISION_MODEL = os.environ.get('CLAUDE_VISION_MODEL', 'claude-sonnet-5')
# Scène À LA DEMANDE (« شنو قدامي؟ ») : Opus 4-8 (qualité max).
CLAUDE_VISION_MODEL_HQ = os.environ.get('CLAUDE_VISION_MODEL_HQ', 'claude-opus-4-8')
# OCR À LA DEMANDE (« قرا ليا ») : Opus 4-8 = lecture la plus précise (petits
# caractères, manuscrit, posologie). L'OCR de fond (boucle) reste sur
# CLAUDE_VISION_MODEL (Sonnet) — voir src/providers/ocr.py.
CLAUDE_OCR_MODEL = os.environ.get('CLAUDE_OCR_MODEL', 'claude-opus-4-8')
# Budgets tokens SÉPARÉS par contexte (levier dialogue). À la demande + chat =
# riche (l'utilisateur a posé une vraie question) ; boucle de fond = court
# (narration brève qui ne monopolise pas la parole → moins d'écho/chevauchement).
CLAUDE_MAX_TOKENS  = int(os.environ.get('CLAUDE_MAX_TOKENS',  '300'))
# Boucle AutoScene uniquement : description de fond courte (~8s parlé).
CLAUDE_SCENE_AUTO_MAX_TOKENS = int(os.environ.get('CLAUDE_SCENE_AUTO_MAX_TOKENS', '80'))
# La lecture OCR a besoin de plus de place qu'une description de scène
# (rentre une lettre / notice entière) → plafond séparé, plus large.
CLAUDE_OCR_MAX_TOKENS = int(os.environ.get('CLAUDE_OCR_MAX_TOKENS', '400'))
# 1568 = lettre/notice lisible sur le still HQ (~2400 tokens). Sans effet sur la
# boucle continue (source 640px, jamais agrandie). Monter la RÉSOLUTION au-delà
# est inutile (Claude redimensionne) — pour lire des petits caractères, c'est la
# QUALITÉ JPEG qui compte (CLAUDE_IMG_QUALITY ci-dessous).
CLAUDE_IMG_MAX_PX  = int(os.environ.get('CLAUDE_IMG_MAX_PX',  '1568'))
# 90 (au lieu de 70) → petits caractères plus nets pour l'OCR. Coût no-object.
CLAUDE_IMG_QUALITY = int(os.environ.get('CLAUDE_IMG_QUALITY', '90'))
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
# 4 = « YEUX PERMANENTS » (défaut 2026-07-11, jour de la présentation) : la STT
# reste peu fiable sur le matériel actuel → la démo ne dépend PAS de la voix.
# Toutes les 4s (dès la fin de la parole précédente) : capture → description de
# scène + lecture de texte → voix. Le thread Conversation tourne quand même en
# plus si un micro est là. 0 = mode à la demande (l'assistant ne parle que sur
# commande vocale). La scène nécessite ANTHROPIC_API_KEY (pas de fallback local).
AUTO_DESCRIBE_INTERVAL = float(os.environ.get('AUTO_DESCRIBE_INTERVAL', '4'))

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

# Index PyAudio du micro. -1 (défaut depuis 2026-07-11) = micro par défaut du
# système — adapté au micro USB (adaptateur jack→USB) : les index PyAudio
# changent dès que le matériel audio change (Bluetooth/USB), un index figé
# finit par pointer sur le mauvais périphérique (OSError -9997). L'ouverture
# est de toute façon robuste : index configuré → défaut système, 16 kHz →
# taux natif (src/audio/listener.py _ouvrir_micro).
MIC_DEVICE_INDEX = int(os.environ.get('MIC_DEVICE_INDEX', '-1'))

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
# de contexte mais plus de tokens par appel. 15 (coût no-object) → dialogue de
# suivi bien plus riche. En complément, la DERNIÈRE image vue à la demande est
# gardée (src/core/memory.py) et rattachée à la question chat suivante → suivi
# VISUEL (« شنو كانت الحاجة الزرقاء؟ ») même quand la question est en texte.
CONV_MEMORY_TURNS = int(os.environ.get('CONV_MEMORY_TURNS', '15'))
