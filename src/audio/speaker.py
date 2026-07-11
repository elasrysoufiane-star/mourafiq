"""
Synthèse vocale — sortie audio uniquement.

Le routage TTS (edge / gTTS / ElevenLabs) est géré dans src/providers/tts.py.
Configurer TTS_PROVIDER dans .env pour changer de provider.

conversation_active est activé UNIQUEMENT ici, pendant la sortie audio.
La vision tourne librement pendant l'écoute micro.
"""
from src.core import state
from src.audio.text_clean import clean_for_speech


def parler(texte: str) -> None:
    """
    Synthétise et joue du texte en darija marocaine.
    Nettoie le Markdown (gras/listes/titres) avant de parler — sinon le TTS le
    lit littéralement. Active conversation_active pendant toute la sortie audio.
    """
    texte = clean_for_speech(texte)
    # set/clear À L'INTÉRIEUR du verrou : sinon un appelant en attente du verrou
    # joue son audio APRÈS que le premier ait fait clear() → l'anti-écho du
    # listener ne voit rien et le micro transcrit la voix de l'assistant.
    with state.audio_lock:
        state.conversation_active.set()
        try:
            print(f'Pi dit: {texte}')
            _jouer_tts(texte)
        except Exception as e:
            print(f'Erreur audio: {e}')
        finally:
            state.conversation_active.clear()


def _jouer_tts(texte: str) -> None:
    from src.providers.tts import synthesize
    synthesize(texte)
