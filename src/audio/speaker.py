"""
Synthèse vocale et utilitaires audio.

Priorité TTS : edge-tts (ar-MA-JamalNeural) → fallback gTTS
Lecteur audio : mpg123 (fiable sur Bluetooth, bloque jusqu'à la fin réelle)

Fix 1 : conversation_active est activé UNIQUEMENT ici, pendant la sortie audio.
        La vision tourne librement pendant l'écoute micro.
"""
import os
import contextlib
import subprocess
import asyncio
import time

import numpy as np

try:
    import edge_tts
    _EDGE_OK = True
except ImportError:
    _EDGE_OK = False
    print('AVERTISSEMENT: edge-tts absent — fallback gTTS (pip install edge-tts)')

try:
    from gtts import gTTS
    _GTTS_OK = True
except ImportError:
    _GTTS_OK = False
    print('AVERTISSEMENT: gTTS absent (pip install gtts)')

try:
    import pyaudio
    _PYAUDIO_OK = True
except ImportError:
    _PYAUDIO_OK = False

from config.settings import AUDIO_MP3, EDGE_VOICE
from src.core import state


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


def parler(texte: str) -> None:
    """
    Synthétise et joue du texte en darija marocaine.
    Active conversation_active pendant toute la durée de la sortie audio.
    """
    state.conversation_active.set()
    with state.audio_lock:
        try:
            print(f'Pi dit: {texte}')
            _jouer_tts(texte)
        except Exception as e:
            print(f'Erreur audio: {e}')
    state.conversation_active.clear()


def _jouer_tts(texte: str) -> None:
    """Génère le MP3 (edge-tts ou gTTS) puis le joue avec mpg123."""
    tts_ok = False

    # Tentative edge-tts — voix marocaine plus naturelle
    if _EDGE_OK:
        try:
            asyncio.run(
                edge_tts.Communicate(texte, voice=EDGE_VOICE).save(AUDIO_MP3)
            )
            tts_ok = True
        except Exception as e:
            print(f'edge-tts échoué ({e}), fallback gTTS...')

    # Fallback gTTS
    if not tts_ok:
        if _GTTS_OK:
            gTTS(text=texte, lang='ar').save(AUDIO_MP3)
        else:
            print('Aucun moteur TTS disponible !')
            return

    # mpg123 bloque jusqu'à la fin réelle — fiable sur Bluetooth
    subprocess.run(['mpg123', '-q', AUDIO_MP3], check=False)


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
