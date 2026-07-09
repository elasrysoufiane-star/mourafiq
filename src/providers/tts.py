"""
Provider TTS — synthèse vocale vers AUDIO_MP3 + lecture mpg123.
Routage selon TTS_PROVIDER dans config/settings.py.

Providers supportés :
  edge       — edge-tts ar-MA-JamalNeural (défaut, gratuit)
  gtts       — Google TTS arabe (fallback gratuit)
  elevenlabs — ElevenLabs multilingual v2 (payant, mode démo)
  openai     — OpenAI TTS (payant, pas de voix darija dédiée)

Ordre de fallback automatique si provider indisponible :
  elevenlabs → edge → gtts
  openai (réseau/clé absente) → edge → gtts
"""
import socket
import subprocess
import asyncio
import urllib.error

from config.settings import (
    TTS_PROVIDER,
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
    OPENAI_API_KEY,
    AUDIO_MP3, EDGE_VOICE,
)

_NETWORK_ERRORS = (socket.gaierror, ConnectionError, TimeoutError, OSError,
                    urllib.error.URLError)

try:
    import edge_tts
    _EDGE_OK = True
except ImportError:
    _EDGE_OK = False

try:
    from gtts import gTTS
    _GTTS_OK = True
except ImportError:
    _GTTS_OK = False


def synthesize(texte: str) -> None:
    """Synthétise le texte et le joue via mpg123 selon le provider configuré."""
    if TTS_PROVIDER == 'elevenlabs':
        if not ELEVENLABS_API_KEY:
            print('ELEVENLABS_API_KEY manquant — fallback edge-tts')
            _edge_synthesize(texte)
        else:
            try:
                _elevenlabs_synthesize(texte)
            except Exception as e:
                print(f'ElevenLabs échoué ({e}) — fallback edge-tts')
                _edge_synthesize(texte)
    elif TTS_PROVIDER == 'gtts':
        _gtts_synthesize(texte)
    elif TTS_PROVIDER == 'openai':
        if not OPENAI_API_KEY:
            print('OPENAI_API_KEY manquant — fallback edge-tts')
            _edge_synthesize(texte)
        else:
            try:
                _openai_synthesize(texte)
            except _NETWORK_ERRORS as e:
                print(f'OpenAI TTS inaccessible (pas d\'Internet ?) — fallback edge-tts: {e}')
                _edge_synthesize(texte)
            except Exception as e:
                if 'Connection' in type(e).__name__ or 'Timeout' in type(e).__name__:
                    print(f'OpenAI TTS inaccessible (pas d\'Internet ?) — fallback edge-tts: {e}')
                    _edge_synthesize(texte)
                else:
                    print(f'OpenAI TTS échoué ({e}) — fallback edge-tts')
                    _edge_synthesize(texte)
    else:  # edge (défaut)
        _edge_synthesize(texte)


def _edge_synthesize(texte: str) -> None:
    if _EDGE_OK:
        try:
            asyncio.run(edge_tts.Communicate(texte, voice=EDGE_VOICE).save(AUDIO_MP3))
            print(f'TTS: edge-tts ({EDGE_VOICE})')
            subprocess.run(['mpg123', '-q', AUDIO_MP3], check=False)
            return
        except Exception as e:
            print(f'edge-tts échoué ({e}) — fallback gTTS')
    else:
        print('edge-tts absent — fallback gTTS')
    _gtts_synthesize(texte)


def _gtts_synthesize(texte: str) -> None:
    if _GTTS_OK:
        try:
            gTTS(text=texte, lang='ar').save(AUDIO_MP3)
            print('TTS: gTTS (ar)')
            subprocess.run(['mpg123', '-q', AUDIO_MP3], check=False)
            return
        except Exception as e:
            print(f'gTTS échoué: {e}')
    print('Aucun moteur TTS disponible !')


def _openai_synthesize(texte: str) -> None:
    from src.ai.openai_client import gpt4o_tts
    gpt4o_tts(texte, AUDIO_MP3)
    subprocess.run(['mpg123', '-q', AUDIO_MP3], check=False)


def _elevenlabs_synthesize(texte: str) -> None:
    """ElevenLabs multilingual v2 — nécessite ELEVENLABS_API_KEY."""
    from elevenlabs.client import ElevenLabs
    # Adam (pNInz6obpgDQGcFmaJgB) est utilisé par défaut si ELEVENLABS_VOICE_ID est vide.
    # Voir lab.elevenlabs.io/voice-library pour choisir une voix arabophone.
    voice_id = ELEVENLABS_VOICE_ID or 'pNInz6obpgDQGcFmaJgB'
    print('TTS: ElevenLabs (eleven_multilingual_v2)')
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    response = client.text_to_speech.convert(
        text=texte,
        voice_id=voice_id,
        model_id='eleven_multilingual_v2',
        output_format='mp3_44100_128',
    )
    with open(AUDIO_MP3, 'wb') as f:
        for chunk in response:
            f.write(chunk)
    subprocess.run(['mpg123', '-q', AUDIO_MP3], check=False)
