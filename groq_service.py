import time
import wave

import pyaudio
import numpy as np

from config import AUDIO_WAV, TIMEOUT_ECOUTE
import state
from audio import suprimer_alsa


def groq_darija(question):
    """
    Envoie une question à LLaMA 3.1 via Groq et retourne une réponse en darija marocaine.
    3 tentatives avec backoff exponentiel en cas de quota dépassé (429).
    """
    for tentative in range(3):
        try:
            response = state.groq_client.chat.completions.create(
                model='llama-3.1-8b-instant',
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'أنت مساعد ذكي للمكفوفين في المغرب. '
                            'تتكلم الدارجة المغربية فقط. '
                            'ردودك قصيرة جدا — جملة واحدة فقط. '
                            'أمثلة: كاين كرسي قدامك / سير على اليمين بعد 50 متر / مكتوب صيدلية الأمل'
                        )
                    },
                    {'role': 'user', 'content': question}
                ],
                max_tokens=80,
                temperature=0.3
            )
            reponse = response.choices[0].message.content.strip()
            print(f'Groq darija: {reponse}')
            return reponse
        except Exception as e:
            if '429' in str(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota dépassé, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur Groq: {e}')
                return 'عفوا ماقدرتش نفهم'


def reconnaitre_voix():
    """
    Écoute le micro via VAD (Voice Activity Detection), enregistre la phrase,
    puis la transcrit avec Groq Whisper en arabe.
    Timeout automatique après 30s sans voix détectée.
    """
    print('En attente de voix...')
    with suprimer_alsa():
        p      = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1,
                        rate=16000, input=True, frames_per_buffer=1024)

    frames  = []
    silence = 0
    parole  = False
    timeout = 0  # chunks sans voix (reset dès qu'une voix est détectée)

    while True:
        data   = stream.read(1024, exception_on_overflow=False)
        chunk  = np.frombuffer(data, dtype=np.int16)
        volume = np.abs(chunk).mean()

        if volume > state.VOL_SEUIL:
            # Voix détectée — enregistrement en cours
            parole   = True
            silence  = 0
            timeout  = 0
            frames.append(data)
        elif parole:
            # Silence après parole — on attend la fin de la phrase
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

    # Sauvegarde du fichier WAV
    wf = wave.open(AUDIO_WAV, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(b''.join(frames))
    wf.close()

    # Transcription Groq Whisper avec 3 tentatives
    for tentative in range(3):
        try:
            with open(AUDIO_WAV, 'rb') as f:
                transcription = state.groq_client.audio.transcriptions.create(
                    model='whisper-large-v3-turbo',
                    file=f,
                    language='ar'
                )
            texte = transcription.text.strip()
            print(f'Compris: {texte}')
            return texte
        except Exception as e:
            if '429' in str(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota transcription, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur transcription: {e}')
                return ''
