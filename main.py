"""
Assistant IA pour Malvoyants — Maroc
Raspberry Pi 4 | Master IT TAM UM5 2026

Point d'entrée principal.
Initialise le matériel, lance les threads vision et conversation.
"""

import time
import threading
import subprocess
from pathlib import Path

from config import GROQ_API_KEY, MODEL_PATH, BASE_DIR
import state
from audio import calibrer_micro, suprimer_alsa, parler
from vision import mode_vision
from conversation import mode_conversation
from gps import init_gps


def init():
    print('=' * 50)
    print('Chargement Assistant IA Malvoyants...')

    # Créer les répertoires temp/ et logs/ s'ils n'existent pas
    (BASE_DIR / 'temp').mkdir(exist_ok=True)
    (BASE_DIR / 'logs').mkdir(exist_ok=True)

    # YOLO — chargement du modèle de détection d'objets
    print('Chargement YOLO...')
    from ultralytics import YOLO
    state.model = YOLO(MODEL_PATH)

    # Caméra PiCamera2 — RGB888 640×480
    print('Chargement caméra...')
    from picamera2 import Picamera2
    state.camera = Picamera2()
    cam_config   = state.camera.create_preview_configuration(
        main={'format': 'RGB888', 'size': (640, 480)}
    )
    state.camera.configure(cam_config)
    state.camera.start()
    time.sleep(2)  # délai de stabilisation de la caméra

    # Vérification mpg123
    print('Vérification mpg123...')
    if subprocess.run(['which', 'mpg123'], capture_output=True).returncode != 0:
        print('AVERTISSEMENT: mpg123 non installé ! sudo apt install mpg123')

    # Client Groq — NLP (LLaMA) et STT (Whisper)
    print('Chargement Groq...')
    from groq import Groq
    state.groq_client = Groq(api_key=GROQ_API_KEY)

    # GPS — connexion série optionnelle
    print('Connexion GPS...')
    state.gps_serial = init_gps()

    # Vérification micro
    print('Vérification micro...')
    import pyaudio
    with suprimer_alsa():
        _p = pyaudio.PyAudio()
    try:
        _info = _p.get_default_input_device_info()
        print(f'Micro détecté: {_info["name"]}')
    except Exception:
        print('AVERTISSEMENT: Aucun micro détecté !')
    _p.terminate()

    # Calibration bruit ambiant (2s) — calcule VOL_SEUIL
    print('Calibration bruit ambiant (2s)...')
    state.VOL_SEUIL = calibrer_micro()

    print('Tout est prêt !')
    print('=' * 50)


def main():
    init()

    # Message d'accueil
    parler('مرحبا أنا مساعدك الذكي ديال المكفوفين كيفاش نعاونك')

    # Lancement des deux threads daemon
    t1 = threading.Thread(target=mode_vision,       name='Vision',       daemon=True)
    t2 = threading.Thread(target=mode_conversation, name='Conversation',  daemon=True)
    t1.start()
    t2.start()
    print('Vision + Conversation actifs !')

    # Boucle principale — attend Ctrl+C pour arrêt propre
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Arrêt...')
        if state.gps_serial:
            state.gps_serial.close()
        state.camera.stop()


if __name__ == '__main__':
    main()
