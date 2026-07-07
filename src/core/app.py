"""
Initialisation du matériel et boucle principale.
Les imports matériels (Picamera2, Groq) sont chargés à l'intérieur de init()
pour ne pas bloquer les tests sur Windows.
"""
import time
import threading
import subprocess

from config.settings import (
    GROQ_API_KEY, BASE_DIR, AUTO_DESCRIBE_INTERVAL,
    HQ_CAPTURE_ENABLED,
)
from src.core import state
from src.audio.speaker import parler
from src.audio.listener import suprimer_alsa, calibrer_micro
from src.vision.detector import mode_auto_scene
from src.conversation.commands import mode_conversation
from src.gps.location import init_gps, position_actuelle


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

    # Caméra PiCamera2 — import lazy
    print('Chargement caméra...')
    from picamera2 import Picamera2
    state.camera = Picamera2()
    cam_cfg = state.camera.create_preview_configuration(
        main={'format': 'RGB888', 'size': (640, 480)}
    )
    state.camera.configure(cam_cfg)
    # Config still HAUTE RÉSOLUTION (pleine résolution capteur) pour l'OCR et
    # la scène à la demande — utilisée ponctuellement via switch_mode dans
    # src/vision/camera.py. La boucle AutoScene garde le flux 640×480 rapide.
    if HQ_CAPTURE_ENABLED:
        try:
            state.camera_still_cfg = state.camera.create_still_configuration(
                main={'format': 'RGB888'}
            )
        except Exception as e:
            print(f'AVERTISSEMENT: still HQ indisponible ({e}) → captures 640×480')
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
        print('AVERTISSEMENT: Aucun micro détecté → pas d\'écoute (AutoScene reste actif).')
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

    if state.gps_serial:
        pos = position_actuelle()
        if pos:
            parler(pos)
        else:
            parler('ماقدرتش نلقى موقعك دابا، خرج برا باش يتقى الإشارة')

    actifs = []

    # AutoScene tourne TOUJOURS (que l'utilisateur parle ou non) — description
    # détaillée périodique de la caméra par la voix, indépendante du micro.
    if AUTO_DESCRIBE_INTERVAL > 0:
        t3 = threading.Thread(target=mode_auto_scene, name='AutoScene', daemon=True)
        t3.start()
        actifs.append(f'AutoScene ({AUTO_DESCRIBE_INTERVAL:.0f}s)')

    # Conversation lancée EN PLUS si un micro est présent — répond aux questions
    # sans jamais couper la description automatique de la scène.
    if state.mic_ok:
        t2 = threading.Thread(target=mode_conversation, name='Conversation', daemon=True)
        t2.start()
        actifs.append('Conversation')
    else:
        print('AVERTISSEMENT: pas de micro détecté — écoute désactivée.')

    print((' + '.join(actifs) if actifs else 'Aucun mode') + ' actif(s) !')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Arrêt...')
        if state.gps_serial:
            state.gps_serial.close()
        state.camera.stop()
