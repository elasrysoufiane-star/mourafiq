"""
Provider TTS — synthèse vocale vers AUDIO_MP3 + lecture mpg123.
Routage selon TTS_PROVIDER dans config/settings.py.

Providers supportés :
  azure      — Azure Speech officiel, même voix ar-MA-JamalNeural qu'edge-tts
               (défaut, tier F0 gratuit 500K car./mois, fallback edge si clé absente)
  edge       — edge-tts ar-MA-JamalNeural (gratuit, non officiel)
  gtts       — Google TTS arabe (fallback gratuit)
  elevenlabs — ElevenLabs multilingual v2 (payant, mode démo)

Ordre de fallback automatique si provider indisponible :
  azure → edge → gtts   (et elevenlabs → edge → gtts)
"""
import subprocess
import asyncio

from config.settings import (
    TTS_PROVIDER,
    AZURE_SPEECH_KEY, AZURE_SPEECH_REGION,
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
    AUDIO_MP3, EDGE_VOICE,
)

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
    if TTS_PROVIDER == 'azure':
        if not AZURE_SPEECH_KEY:
            print('AZURE_SPEECH_KEY manquant — fallback edge-tts')
            _edge_synthesize(texte)
        else:
            try:
                _azure_synthesize(texte)
            except Exception as e:
                print(f'Azure Speech échoué ({e}) — fallback edge-tts')
                _edge_synthesize(texte)
    elif TTS_PROVIDER == 'elevenlabs':
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
    else:  # edge (défaut)
        _edge_synthesize(texte)


def _azure_synthesize(texte: str) -> None:
    """Azure Speech REST — API officielle de la même voix marocaine qu'edge-tts
    (catalogue de voix identique). Stdlib uniquement, pas de SDK à installer."""
    import urllib.request
    from xml.sax.saxutils import escape

    lang = '-'.join(EDGE_VOICE.split('-')[:2])  # 'ar-MA-JamalNeural' → 'ar-MA'
    ssml = (
        f"<speak version='1.0' xml:lang='{lang}'>"
        f"<voice name='{EDGE_VOICE}'>{escape(texte)}</voice></speak>"
    )
    request = urllib.request.Request(
        f'https://{AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1',
        data=ssml.encode('utf-8'),
        headers={
            'Ocp-Apim-Subscription-Key': AZURE_SPEECH_KEY,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3',
            'User-Agent': 'mourafiq',
        },
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        audio = response.read()
    with open(AUDIO_MP3, 'wb') as f:
        f.write(audio)
    print(f'TTS: Azure Speech ({EDGE_VOICE}, {AZURE_SPEECH_REGION})')
    subprocess.run(['mpg123', '-q', AUDIO_MP3], check=False)


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
