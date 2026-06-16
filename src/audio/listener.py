"""
Écoute micro — VAD, calibration et transcription Groq Whisper.

Contient aussi les utilitaires liés au micro :
  - suprimer_alsa() : supprime le spam ALSA/JACK au démarrage
  - calibrer_micro() : mesure le bruit ambiant et calcule VOL_SEUIL

Timeout automatique après 8s sans voix pour éviter tout blocage infini.
"""
import os
import contextlib
import wave
import time

import numpy as np

try:
    import pyaudio
    _PYAUDIO_OK = True
except ImportError:
    _PYAUDIO_OK = False

from config.settings import AUDIO_WAV, TIMEOUT_ECOUTE
from src.core import state

# Anti-écho : purge ~0.4s de micro au début de chaque écoute, le temps que la
# queue audio du haut-parleur (latence Bluetooth) ne soit plus captée par le micro.
_PURGE_CHUNKS = int(0.4 * 16000 / 1024)
# Filtre anti-bruit : minimum de parole (~0.4s) pour valider une capture.
# En dessous = bruit / écho résiduel / hallucination Whisper → on ignore.
_MIN_VOIX_CHUNKS = int(0.4 * 16000 / 1024)


# ── Utilitaires micro ─────────────────────────────────────────────────────────

@contextlib.contextmanager
def suprimer_alsa():
    """Redirige stderr vers /dev/null pour supprimer le spam ALSA/JACK."""
    devnull    = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)


def calibrer_micro() -> int:
    """
    Écoute le bruit ambiant pendant 2 secondes et calcule le seuil de détection vocale.
    Retourne le seuil calculé (minimum 150).
    """
    if not _PYAUDIO_OK:
        print('PyAudio absent — seuil par défaut: 200')
        return 200

    with suprimer_alsa():
        p      = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1,
                        rate=16000, input=True, frames_per_buffer=1024)
    volumes = []
    for _ in range(30):
        data = stream.read(1024, exception_on_overflow=False)
        vol  = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
        volumes.append(vol)
    stream.stop_stream()
    stream.close()
    p.terminate()

    bruit = float(np.mean(volumes))
    seuil = max(150, int(bruit * 3))
    print(f'Bruit ambiant: {bruit:.0f} → Seuil voix: {seuil}')
    return seuil


# ── Reconnaissance vocale ─────────────────────────────────────────────────────

def reconnaitre_voix() -> str:
    """
    Écoute le micro jusqu'à détection d'une phrase, puis transcrit avec Whisper.
    Retourne la transcription (str) ou '' si timeout / erreur.
    Timeout : 8s sans voix → retour automatique.
    """
    if not _PYAUDIO_OK:
        print('PyAudio absent — écoute désactivée')
        time.sleep(5)
        return ''

    print('En attente de voix...')

    # Anti-écho : ne pas écouter pendant que l'assistant parle, puis laisser
    # retomber la queue audio (latence Bluetooth) avant d'ouvrir le micro.
    while state.conversation_active.is_set():
        time.sleep(0.05)

    with suprimer_alsa():
        p      = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1,
                        rate=16000, input=True, frames_per_buffer=1024)

    # Purge le tampon micro (écho résiduel du haut-parleur capté au démarrage).
    for _ in range(_PURGE_CHUNKS):
        stream.read(1024, exception_on_overflow=False)

    frames  = []
    silence = 0
    parole  = False
    voix    = 0  # nombre de chunks réellement vocaux (pour le filtre anti-bruit)
    timeout = 0  # chunks sans voix (reset à chaque détection vocale)

    while True:
        data   = stream.read(1024, exception_on_overflow=False)
        chunk  = np.frombuffer(data, dtype=np.int16)
        volume = np.abs(chunk).mean()

        if volume > state.VOL_SEUIL:
            # Voix active
            parole  = True
            voix   += 1
            silence = 0
            timeout = 0
            frames.append(data)
        elif parole:
            # Fin de phrase — attente silence pour confirmer
            silence += 1
            frames.append(data)
            if silence > 16:
                break
        else:
            # Pas encore de parole — incrémenter le timeout
            timeout += 1
            if timeout >= TIMEOUT_ECOUTE:
                print('Timeout écoute (8s sans voix)')
                break

    stream.stop_stream()
    stream.close()
    p.terminate()

    if not frames:
        return ''

    # Filtre anti-bruit : capture trop courte → bruit / écho / hallucination.
    if voix < _MIN_VOIX_CHUNKS:
        print('Capture trop courte — ignorée (bruit/écho)')
        return ''

    # Sauvegarde WAV
    wf = wave.open(AUDIO_WAV, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(b''.join(frames))
    wf.close()

    return _transcrire()


def _transcrire() -> str:
    """Délègue la transcription au provider STT configuré (voir src/providers/stt.py)."""
    from src.providers.stt import transcribe
    return transcribe()
