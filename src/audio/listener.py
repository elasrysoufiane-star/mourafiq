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
    with suprimer_alsa():
        p      = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1,
                        rate=16000, input=True, frames_per_buffer=1024)

    frames  = []
    silence = 0
    parole  = False
    timeout = 0  # chunks sans voix (reset à chaque détection vocale)

    while True:
        data   = stream.read(1024, exception_on_overflow=False)
        chunk  = np.frombuffer(data, dtype=np.int16)
        volume = np.abs(chunk).mean()

        if volume > state.VOL_SEUIL:
            # Voix active
            parole  = True
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

    # Sauvegarde WAV
    wf = wave.open(AUDIO_WAV, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(b''.join(frames))
    wf.close()

    return _transcrire()


def _transcrire() -> str:
    """Envoie le WAV à Groq Whisper, 3 tentatives avec backoff."""
    for tentative in range(3):
        try:
            with open(AUDIO_WAV, 'rb') as f:
                result = state.groq_client.audio.transcriptions.create(
                    model='whisper-large-v3-turbo',
                    file=f,
                    language='ar'
                )
            texte = result.text.strip()
            print(f'Compris: {texte}')
            return texte
        except Exception as e:
            if '429' in str(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota Whisper, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur transcription: {e}')
                return ''
    return ''
