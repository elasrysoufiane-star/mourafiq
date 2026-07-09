"""
Lecture OCR — capture caméra + extraction de texte + lecture en darija.
Routage selon OCR_PROVIDER dans config/settings.py.

Providers supportés :
  local  — Tesseract (ara+fra) + reformulation Groq/Claude/OpenAI (défaut, gratuit)
  openai — lecture directe via GPT-4o vision (payant)

Fallback automatique vers 'local' si clé absente ou erreur réseau (pas
d'Internet) — jamais d'exception non gérée vers l'utilisateur.
"""
import socket
import urllib.error

try:
    import pytesseract
    _TESSERACT_OK = True
except ImportError:
    _TESSERACT_OK = False
    print('AVERTISSEMENT: pytesseract absent (pip install pytesseract)')

try:
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

from config.settings import OCR_PROVIDER, OPENAI_API_KEY
from src.core import state
from src.audio.speaker import parler
from src.providers.ai import get_ai_response

_NETWORK_ERRORS = (socket.gaierror, ConnectionError, TimeoutError, OSError,
                    urllib.error.URLError)


def lire_texte() -> None:
    """Capture une image, en extrait le texte via le provider configuré et le lit."""
    try:
        parler('انتظر كنقرا')

        with state.camera_lock:
            img = state.camera.capture_array()

        if OCR_PROVIDER == 'openai' and OPENAI_API_KEY:
            try:
                parler(_openai_ocr(img))
                return
            except _NETWORK_ERRORS as e:
                print(f'GPT-4o inaccessible (pas d\'Internet ?) — fallback Tesseract: {e}')
            except Exception as e:
                if 'Connection' in type(e).__name__ or 'Timeout' in type(e).__name__:
                    print(f'GPT-4o inaccessible (pas d\'Internet ?) — fallback Tesseract: {e}')
                else:
                    raise
        elif OCR_PROVIDER == 'openai':
            print('OPENAI_API_KEY manquant — fallback Tesseract')

        _tesseract_ocr(img)

    except Exception as e:
        print(f'Erreur OCR: {e}')
        parler('ماقدرتش نقرا')


def _openai_ocr(img) -> str:
    from src.ai.openai_client import gpt4o_read_text
    return gpt4o_read_text(img)


def _tesseract_ocr(img) -> None:
    if not (_TESSERACT_OK and _PIL_OK):
        parler('ماقدرتش نقرا — Tesseract غير متوفر')
        return

    img_pil = Image.fromarray(img)
    texte   = pytesseract.image_to_string(img_pil, lang='ara+fra')

    if texte.strip():
        print(f'Texte lu: {texte[:100]}...' if len(texte) > 100 else f'Texte lu: {texte}')
        parler(get_ai_response(f'مكتوب في الصورة: {texte} — قل ذلك بالدارجة'))
    else:
        parler('ماكاين حتى نص')
