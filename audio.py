import os
import contextlib
import subprocess
import asyncio

import pyaudio
import numpy as np
from gtts import gTTS

try:
    import edge_tts
    EDGE_TTS_OK = True
except ImportError:
    EDGE_TTS_OK = False
    print('AVERTISSEMENT: edge-tts absent — fallback gTTS actif (pip install edge-tts)')

from config import AUDIO_MP3, EDGE_VOICE
import state


@contextlib.contextmanager
def suprimer_alsa():
    """Redirige stderr vers /dev/null pour supprimer le bruit ALSA/JACK au démarrage."""
    devnull    = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)


def parler(texte):
    """
    Synthétise et joue du texte en arabe.
    Fix 1 : bloque la vision (conversation_active) uniquement pendant la sortie audio.
    Priorité : edge-tts (ar-MA) → fallback gTTS → mpg123 pour la lecture Bluetooth.
    """
    state.conversation_active.set()
    with state.audio_lock:
        try:
            print(f'Pi dit: {texte}')
            tts_ok = False

            # Tentative edge-tts (voix marocaine plus naturelle)
            if EDGE_TTS_OK:
                try:
                    # asyncio.run() fonctionne depuis un thread Python 3.7+
                    asyncio.run(
                        edge_tts.Communicate(texte, voice=EDGE_VOICE).save(AUDIO_MP3)
                    )
                    tts_ok = True
                except Exception as e:
                    print(f'edge-tts échoué ({e}), fallback gTTS...')

            # Fallback gTTS si edge-tts indisponible ou en erreur
            if not tts_ok:
                gTTS(text=texte, lang='ar').save(AUDIO_MP3)

            # mpg123 bloque jusqu'à la fin réelle — fiable sur Bluetooth
            subprocess.run(['mpg123', '-q', AUDIO_MP3], check=False)

        except Exception as e:
            print(f'Erreur audio: {e}')
    state.conversation_active.clear()


def calibrer_micro():
    """
    Écoute le bruit ambiant pendant 2 secondes et calcule le seuil de détection vocale.
    Retourne le seuil calculé (minimum 150).
    """
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
