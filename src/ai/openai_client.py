"""
Interface OpenAI (GPT-4o) — cerveau complet : conversation, vision, OCR, STT, TTS.
Branche feat/gpt4o-assistant : alternative 100% OpenAI à Groq/Claude.

Quatre entrées :
  gpt4o_darija(question)          — texte seul → réponse darija courte (chat)
  gpt4o_describe_scene(image, q)  — image (numpy RGB) + question → darija (vision)
  gpt4o_read_text(image)          — image (numpy RGB) → texte lu + reformulé darija (OCR)
  gpt4o_transcribe(audio_path)    — fichier audio → texte (Whisper/STT OpenAI)
  gpt4o_tts(texte, out_path)      — texte → fichier audio (TTS OpenAI)

Optimisation :
  • appelé uniquement à la demande (géré en amont) → 0 coût au repos
  • image redimensionnée + JPEG compressée avant envoi (mêmes leviers que Claude)
  • max_tokens court (réponse parlée)
  • 3 tentatives avec backoff sur erreurs retryable (429/rate_limit)

Import du SDK `openai` en lazy (dans _get_client) → ce module reste importable
sur Windows sans la lib ni la clé, pour les tests.
"""
import base64
import io
import time

from config.settings import (
    OPENAI_API_KEY,
    OPENAI_TEXT_MODEL, OPENAI_VISION_MODEL,
    OPENAI_STT_MODEL, OPENAI_TTS_MODEL, OPENAI_TTS_VOICE,
    OPENAI_MAX_TOKENS, OPENAI_IMG_MAX_PX, OPENAI_IMG_QUALITY,
)

_VISION_SYSTEM_PROMPT = (
    'أنت مساعد بصري ذكي للمكفوفين في المغرب. '
    'تتكلم الدارجة المغربية فقط. '
    'وصف المشهد لي قدام المستخدم بإيجاز مفيد للسلامة: '
    'الأشياء المهمة، الاتجاه، والمسافة التقريبية. '
    'ردك قصير جدا — جملة وحدة ولا جوج بحال الإنسان لي كيهضر بسرعة. '
    'أمثلة: كاين طبلة قدامك على بعد متر، وكرسي على اليمين / '
    'الطريق سالكة، سير نيشان / حذاك باب على اليسار، حل بشوية'
)

_CHAT_SYSTEM_PROMPT = (
    'أنت "مرافق"، مساعد ذكي للمكفوفين في المغرب. '
    'كتهضر غير بالدارجة المغربية، بأسلوب دافئ ومطمئن. '
    'جاوب بإيجاز: جملة ولا جوج، بحال واحد كيهضر مع صاحبو. '
    'إلا ما فهمتيش السؤال مزيان، طلب منو يعاودو بلطف، وما تختارعش الجواب. '
    'إلا بغا يعرف شنو قدامو قولو يقول "شنو قدامي"، '
    'وإلا بغا يقرا شي حاجة قولو يقول "قرا ليا".'
)

_OCR_SYSTEM_PROMPT = (
    'أنت مساعد للمكفوفين في المغرب. كاين صورة فيها نص مكتوب '
    '(عربي ولا فرنسي). قرا النص وقولو بالدارجة المغربية بشكل واضح ومختصر. '
    'إلا ماكاين حتى نص فالصورة قول "ماكاين حتى نص".'
)

_client = None


def _get_client():
    """Crée (une fois) le client openai. Import lazy → testable sans la lib."""
    global _client
    if _client is None:
        import openai
        _client = openai.OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _encode_image(image) -> str:
    """numpy RGB array → JPEG redimensionné/compressé → base64 (str)."""
    from PIL import Image
    img = Image.fromarray(image)
    img.thumbnail((OPENAI_IMG_MAX_PX, OPENAI_IMG_MAX_PX))
    buf = io.BytesIO()
    img.convert('RGB').save(buf, format='JPEG', quality=OPENAI_IMG_QUALITY)
    return base64.standard_b64encode(buf.getvalue()).decode('utf-8')


def _retryable(e) -> bool:
    s = str(e).lower()
    return '429' in s or 'rate_limit' in s or 'overloaded' in s


def gpt4o_darija(question: str) -> str:
    """Question texte → réponse darija courte. Message d'erreur si échec."""
    for tentative in range(3):
        try:
            resp = _get_client().chat.completions.create(
                model=OPENAI_TEXT_MODEL,
                max_tokens=OPENAI_MAX_TOKENS,
                messages=[
                    {'role': 'system', 'content': _CHAT_SYSTEM_PROMPT},
                    {'role': 'user', 'content': question},
                ],
            )
            reponse = (resp.choices[0].message.content or '').strip()
            print(f'GPT-4o darija: {reponse}')
            return reponse
        except Exception as e:
            if _retryable(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota GPT-4o, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur GPT-4o: {e}')
                raise
    raise RuntimeError('GPT-4o: échec après 3 tentatives')


def gpt4o_describe_scene(image, question: str = 'شنو قدامي؟') -> str:
    """Image (numpy RGB) + question → description de scène en darija."""
    for tentative in range(3):
        try:
            data = _encode_image(image)
            resp = _get_client().chat.completions.create(
                model=OPENAI_VISION_MODEL,
                max_tokens=OPENAI_MAX_TOKENS,
                messages=[
                    {'role': 'system', 'content': _VISION_SYSTEM_PROMPT},
                    {'role': 'user', 'content': [
                        {'type': 'text', 'text': question},
                        {'type': 'image_url', 'image_url': {
                            'url': f'data:image/jpeg;base64,{data}',
                        }},
                    ]},
                ],
            )
            reponse = (resp.choices[0].message.content or '').strip()
            print(f'GPT-4o scene: {reponse}')
            return reponse
        except Exception as e:
            if _retryable(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota GPT-4o vision, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur GPT-4o vision: {e}')
                raise
    raise RuntimeError('GPT-4o vision: échec après 3 tentatives')


def gpt4o_read_text(image) -> str:
    """Image (numpy RGB) → texte détecté reformulé en darija (OCR via vision)."""
    for tentative in range(3):
        try:
            data = _encode_image(image)
            resp = _get_client().chat.completions.create(
                model=OPENAI_VISION_MODEL,
                max_tokens=OPENAI_MAX_TOKENS,
                messages=[
                    {'role': 'system', 'content': _OCR_SYSTEM_PROMPT},
                    {'role': 'user', 'content': [
                        {'type': 'text', 'text': 'قرا ليا هاد النص'},
                        {'type': 'image_url', 'image_url': {
                            'url': f'data:image/jpeg;base64,{data}',
                        }},
                    ]},
                ],
            )
            reponse = (resp.choices[0].message.content or '').strip()
            print(f'GPT-4o OCR: {reponse}')
            return reponse
        except Exception as e:
            if _retryable(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota GPT-4o OCR, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur GPT-4o OCR: {e}')
                raise
    raise RuntimeError('GPT-4o OCR: échec après 3 tentatives')


def gpt4o_transcribe(audio_path: str) -> str:
    """Fichier audio (WAV) → texte transcrit (Whisper/STT OpenAI)."""
    with open(audio_path, 'rb') as f:
        result = _get_client().audio.transcriptions.create(
            model=OPENAI_STT_MODEL,
            file=f,
            language='ar',
            temperature=0.0,
        )
    texte = result.text.strip()
    print(f'Compris (GPT-4o): {texte}')
    return texte


def gpt4o_tts(texte: str, out_path: str) -> None:
    """Texte → fichier audio sauvegardé sur out_path (TTS OpenAI)."""
    resp = _get_client().audio.speech.create(
        model=OPENAI_TTS_MODEL,
        voice=OPENAI_TTS_VOICE,
        input=texte,
    )
    resp.write_to_file(out_path)
    print(f'TTS: OpenAI ({OPENAI_TTS_MODEL}/{OPENAI_TTS_VOICE})')
