"""
État partagé entre les threads vision et conversation.
Tous les objets matériels sont initialisés par src.core.app.init().
"""
import threading

# ── Verrous ───────────────────────────────────────────────────────────────────
camera_lock = threading.Lock()   # sérialise tous les appels camera.capture_array()
audio_lock  = threading.Lock()   # sérialise tous les appels parler()

# Fix 1 : conversation_active est géré UNIQUEMENT dans parler()
# La vision tourne librement pendant l'écoute micro.
# Il est activé uniquement pendant la sortie audio.
conversation_active = threading.Event()

# ── Objets matériels (initialisés par app.init()) ─────────────────────────────
camera      = None   # Picamera2
model       = None   # ultralytics.YOLO
groq_client = None   # groq.Groq
gps_serial  = None   # serial.Serial

# Micro disponible ? Mis à jour par app.init(). False → mode vision seul
# (le thread conversation n'est pas lancé, pas de boucle de timeouts inutile).
mic_ok = False

# Seuil volume micro — calibré au démarrage par calibrer_micro()
VOL_SEUIL = 200
