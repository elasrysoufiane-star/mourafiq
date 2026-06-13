import threading

# Verrous et événements partagés entre les threads vision et conversation
camera_lock = threading.Lock()
audio_lock  = threading.Lock()

# Fix 1 : conversation_active est activé UNIQUEMENT pendant parler()
# La vision continue de tourner librement pendant l'écoute micro
conversation_active = threading.Event()

# Objets matériels — initialisés par main.py au démarrage
camera      = None   # Picamera2
model       = None   # YOLO
groq_client = None   # Groq
gps_serial  = None   # serial.Serial

# Seuil de détection vocale — calibré au démarrage dans main.py
VOL_SEUIL = 200
