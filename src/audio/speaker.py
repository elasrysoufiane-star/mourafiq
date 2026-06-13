"""
Synthèse vocale — sortie audio uniquement.

Priorité TTS : edge-tts (ar-MA-JamalNeural) → fallback gTTS
Lecteur audio : mpg123 (fiable sur Bluetooth, bloque jusqu'à la fin réelle)

conversation_active est activé UNIQUEMENT ici, pendant la sortie audio.
La vision tourne librement pendant l'écoute micro.
"""
import subprocess
import asyncio

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

from config.settings import AUDIO_MP3, EDGE_VOICE
from src.core import state


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
