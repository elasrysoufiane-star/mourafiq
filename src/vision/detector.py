"""
Thread vision — boucle YOLO continue.
Détecte les objets avec YOLOv8n et annonce chaque nouveau objet en darija.
Se met en pause uniquement pendant la sortie audio (conversation_active).
"""
import time

from config.settings import CONF_SEUIL, AUTO_DESCRIBE_INTERVAL
from src.core import state
from src.audio.speaker import parler
from src.vision.translations import traductions


def mode_vision() -> None:
    """
    Boucle principale du thread vision.
    Capture → YOLO → annonce si objet nouveau avec confiance > CONF_SEUIL.
    Pause de 3s entre deux annonces pour ne pas saturer l'utilisateur.
    """
    dernier = ''
    print('Mode Vision démarré...')

    while True:
        try:
            # Pause seulement pendant la sortie audio
            if state.conversation_active.is_set():
                time.sleep(0.5)
                continue

            with state.camera_lock:
                img = state.camera.capture_array()

            results = state.model(img, verbose=False)
            for r in results:
                for box in r.boxes:
                    obj  = r.names[int(box.cls)]
                    conf = float(box.conf)

                    if conf > CONF_SEUIL and obj in traductions and obj != dernier:
                        print(f'Vision: {obj} {conf:.0%}')
                        parler(traductions[obj])
                        dernier = obj
                        time.sleep(3)

            time.sleep(0.1)  # limite le CPU entre les frames

        except Exception as e:
            print(f'Erreur vision: {e}')
            time.sleep(1)


def mode_auto_scene() -> None:
    """
    Boucle de description automatique — mode SANS MICRO uniquement.
    Toutes les AUTO_DESCRIBE_INTERVAL secondes : capture → describe_scene() → parle.
    Comme il n'y a pas de commande vocale (« شنو قدامي؟ ») pour déclencher la
    description, cette boucle prend le relais.

    describe_scene() route selon VISION_AI_PROVIDER :
      • 'claude' (+ ANTHROPIC_API_KEY) → Claude VLM (payant, description riche)
      • 'local' (défaut)              → YOLO + Groq (gratuit)
    Le cooldown VISION_COOLDOWN est respecté côté describe_scene().
    """
    from src.providers.vision_ai import describe_scene
    print(f'Mode description auto démarré (chaque {AUTO_DESCRIBE_INTERVAL:.0f}s)...')

    while True:
        try:
            time.sleep(AUTO_DESCRIBE_INTERVAL)

            # Ne pas capturer/parler par-dessus une sortie audio en cours.
            if state.conversation_active.is_set():
                continue

            with state.camera_lock:
                img = state.camera.capture_array()

            desc = describe_scene(img)
            if desc:
                parler(desc)

        except Exception as e:
            print(f'Erreur description auto: {e}')
            time.sleep(1)
