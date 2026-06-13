import time

from config import CONF_SEUIL
from translations import traductions
import state
from audio import parler


def mode_vision():
    """
    Thread vision — tourne en continu.
    Détecte les objets avec YOLO et annonce chaque nouveau objet en darija.
    Fix 1 : s'arrête uniquement pendant parler() (conversation_active),
    tourne librement pendant l'écoute micro.
    """
    dernier = ''
    print('Mode Vision démarré...')

    while True:
        try:
            # Pause uniquement pendant la sortie audio
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

                    if conf > CONF_SEUIL and obj in traductions:
                        if obj != dernier:
                            print(f'Vision: {obj} {conf:.0%}')
                            parler(traductions[obj])
                            dernier = obj
                            time.sleep(3)  # pause entre deux annonces

            time.sleep(0.1)  # limite le CPU entre les frames

        except Exception as e:
            print(f'Erreur vision: {e}')
            time.sleep(1)
