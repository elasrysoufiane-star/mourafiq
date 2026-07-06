"""
Provider STT — transcription vocale depuis AUDIO_WAV.
Routage selon STT_PROVIDER dans config/settings.py.

Providers supportés :
  groq   — Whisper large-v3-turbo (défaut, gratuit)
  openai — Whisper openai (futur, fallback groq si clé absente)

Le fichier WAV doit déjà exister (écrit par reconnaitre_voix() dans listener.py).
"""
import time

from config.settings import STT_PROVIDER, STT_MODEL, OPENAI_API_KEY, AUDIO_WAV

# Biais de langue uniquement — une phrase courte et neutre en darija.
# NE PAS mettre de liste de mots-clés ici : sur audio faible, Whisper recrache
# le contenu du prompt (hallucination), ce qui fabrique de fausses commandes.
_DARIJA_PROMPT = 'تسجيل صوتي بالدارجة المغربية.'


def transcribe() -> str:
    """Transcrit AUDIO_WAV via le provider STT configuré. Retourne '' si erreur."""
    if STT_PROVIDER == 'openai':
        if not OPENAI_API_KEY:
            print('OPENAI_API_KEY manquant — fallback Groq STT')
        else:
            return _openai_transcribe()
    return _groq_transcribe()


def _groq_transcribe() -> str:
    from src.core import state
    for tentative in range(3):
        try:
            with open(AUDIO_WAV, 'rb') as f:
                result = state.groq_client.audio.transcriptions.create(
                    model=STT_MODEL,
                    file=f,
                    language='ar',
                    prompt=_DARIJA_PROMPT,
                    temperature=0.0,
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


def _openai_transcribe() -> str:
    print('OpenAI STT provider: non encore implémenté — fallback Groq')
    return _groq_transcribe()
