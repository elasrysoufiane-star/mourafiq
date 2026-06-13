"""
Synthèse vocale — sortie audio uniquement.

Le routage TTS (edge / gTTS / ElevenLabs) est géré dans src/providers/tts.py.
Configurer TTS_PROVIDER dans .env pour changer de provider.

conversation_active est activé UNIQUEMENT ici, pendant la sortie audio.
La vision tourne librement pendant l'écoute micro.
"""
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
    from src.providers.tts import synthesize
    synthesize(texte)
