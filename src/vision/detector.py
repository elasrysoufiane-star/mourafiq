"""
Thread vision — boucle YOLO continue.
Détecte les objets avec YOLOv8n et annonce chaque nouveau objet en darija.
Se met en pause uniquement pendant la sortie audio (conversation_active).
"""
import time

from config.settings import CONF_SEUIL
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
