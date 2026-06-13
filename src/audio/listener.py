"""
Écoute micro avec VAD (Voice Activity Detection) et transcription Groq Whisper.
Timeout automatique après 30s sans voix pour éviter tout blocage infini.
"""
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
from src.audio.speaker import suprimer_alsa


def reconnaitre_voix() -> str:
    """
    Écoute le micro jusqu'à détection d'une phrase, puis transcrit avec Whisper.
    Retourne la transcription (str) ou '' si timeout / erreur.
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
                print('Timeout écoute (30s sans voix)')
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
