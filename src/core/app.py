"""
Initialisation du matériel et boucle principale.
Les imports matériels (YOLO, Picamera2, Groq) sont chargés à l'intérieur
de init() pour ne pas bloquer les tests sur Windows.
"""
import time
import threading
import subprocess

from config.settings import GROQ_API_KEY, MODEL_PATH, BASE_DIR, AUTO_DESCRIBE_INTERVAL
from src.core import state
from src.audio.speaker import parler
from src.audio.listener import suprimer_alsa, calibrer_micro
from src.vision.detector import mode_vision, mode_auto_scene
from src.conversation.commands import mode_conversation
from src.gps.location import init_gps


def _verifier_config():
    """Vérifie que les variables d'environnement obligatoires sont définies."""
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY manquant.\n"
            "Exécuter : export GROQ_API_KEY='gsk_...'\n"
            "Ou ajouter dans ~/.bashrc puis : source ~/.bashrc"
        )


def init():
    """Initialise tout le matériel dans l'ordre correct."""
    _verifier_config()

    print('=' * 50)
    print('Chargement Assistant IA Malvoyants...')

    # Créer les répertoires runtime si absents
    (BASE_DIR / 'temp').mkdir(exist_ok=True)
    (BASE_DIR / 'logs').mkdir(exist_ok=True)

    # YOLO — import lazy pour ne pas bloquer les tests Windows
    print('Chargement YOLO...')
    from ultralytics import YOLO
    state.model = YOLO(MODEL_PATH)

    # Caméra PiCamera2 — import lazy
    print('Chargement caméra...')
    from picamera2 import Picamera2
    state.camera = Picamera2()
    cam_cfg = state.camera.create_preview_configuration(
        main={'format': 'RGB888', 'size': (640, 480)}
    )
    state.camera.configure(cam_cfg)
    state.camera.start()
    time.sleep(2)  # stabilisation caméra

    # Vérification mpg123
    print('Vérification mpg123...')
    if subprocess.run(['which', 'mpg123'], capture_output=True).returncode != 0:
        print('AVERTISSEMENT: mpg123 non installé → sudo apt install mpg123')

    # Client Groq — NLP (LLaMA) + STT (Whisper)
    print('Chargement Groq...')
    from groq import Groq
    state.groq_client = Groq(api_key=GROQ_API_KEY)

    # GPS — connexion série optionnelle
    print('Connexion GPS...')
    state.gps_serial = init_gps()

    # Vérification micro → state.mic_ok pilote le lancement du thread conversation.
    print('Vérification micro...')
    import pyaudio
    with suprimer_alsa():
        _p = pyaudio.PyAudio()
    try:
        _info = _p.get_default_input_device_info()
        state.mic_ok = True
        print(f'Micro détecté: {_info["name"]}')
    except Exception:
        state.mic_ok = False
        print('AVERTISSEMENT: Aucun micro détecté → mode vision seul (pas d\'écoute).')
    _p.terminate()

    # Calibration bruit ambiant (2s) → calcule VOL_SEUIL.
    # Sautée sans micro (lirait du silence / planterait sur un index absent).
    if state.mic_ok:
        print('Calibration bruit ambiant (2s)...')
        state.VOL_SEUIL = calibrer_micro()

    print('Tout est prêt !')
    print('=' * 50)


def main():
    """Point d'entrée principal — lance les threads et attend Ctrl+C."""
    init()

    parler('السلام عليكم، أنا مرافق، مساعدك الذكي. قول ليا "شنو قدامي" '
           'باش نوصف ليك لي قدامك، "قرا ليا" للقراءة، ولا "وين أنا" للموقع. أنا معاك.')

    t1 = threading.Thread(target=mode_vision, name='Vision', daemon=True)
    t1.start()

    # Thread conversation lancé UNIQUEMENT si un micro est présent — sinon
    # mode vision seul (évite la boucle « En attente de voix → Timeout 8s »).
    if state.mic_ok:
        t2 = threading.Thread(target=mode_conversation, name='Conversation', daemon=True)
        t2.start()
        print('Vision + Conversation actifs !')
    elif AUTO_DESCRIBE_INTERVAL > 0:
        # Sans micro : pas de commande vocale → description automatique périodique.
        t3 = threading.Thread(target=mode_auto_scene, name='AutoScene', daemon=True)
        t3.start()
        print(f'Vision + description auto ({AUTO_DESCRIBE_INTERVAL:.0f}s) actives '
              '(pas de micro).')
    else:
        print('Vision seule active (pas de micro — écoute désactivée).')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Arrêt...')
        if state.gps_serial:
            state.gps_serial.close()
        state.camera.stop()
