"""
Lecture OCR — capture caméra + Tesseract (ara+fra) + reformulation Groq.
Annonce le texte détecté en darija via parler().
"""
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

from src.core import state
from src.audio.speaker import parler
from src.ai.groq_client import groq_darija


def lire_texte() -> None:
    """
    Capture une image, extrait le texte avec Tesseract (arabe + français),
    reformule en darija via Groq LLaMA et lit à voix haute.
    """
    if not (_TESSERACT_OK and _PIL_OK):
        parler('ماقدرتش نقرا — Tesseract غير متوفر')
        return

    try:
        parler('انتظر كنقرا')

        with state.camera_lock:
            img = state.camera.capture_array()

        img_pil = Image.fromarray(img)
        texte   = pytesseract.image_to_string(img_pil, lang='ara+fra')

        if texte.strip():
            print(f'Texte lu: {texte[:100]}...' if len(texte) > 100 else f'Texte lu: {texte}')
            parler(groq_darija(f'مكتوب في الصورة: {texte} — قل ذلك بالدارجة'))
        else:
            parler('ماكاين حتى نص')

    except Exception as e:
        print(f'Erreur OCR: {e}')
        parler('ماقدرتش نقرا')
