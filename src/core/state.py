"""
État partagé entre les threads AutoScene et conversation.
Tous les objets matériels sont initialisés par src.core.app.init().
"""
import threading

# ── Verrous ───────────────────────────────────────────────────────────────────
camera_lock = threading.Lock()   # sérialise tous les appels camera.capture_array()
audio_lock  = threading.Lock()   # sérialise tous les appels parler()

# Fix 1 : conversation_active est géré UNIQUEMENT dans parler()
# AutoScene tourne librement pendant l'écoute micro.
# Il est activé uniquement pendant la sortie audio.
conversation_active = threading.Event()

# ── Objets matériels (initialisés par app.init()) ─────────────────────────────
camera      = None   # Picamera2
camera_still_cfg = None  # config still HQ (OCR / scène à la demande) — None = indisponible
groq_client = None   # groq.Groq
gps_serial  = None   # serial.Serial

# Micro disponible ? Mis à jour par app.init(). False → thread Conversation non
# lancé (AutoScene reste actif — pas de boucle de timeouts inutile).
mic_ok = False

# Seuil volume micro — calibré au démarrage par calibrer_micro()
VOL_SEUIL = 200
