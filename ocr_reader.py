import pytesseract
from PIL import Image

import state
from audio import parler
from groq_service import groq_darija


def lire_texte():
    """
    Capture une image avec la caméra, extrait le texte avec Tesseract (arabe + français),
    puis reformule le contenu en darija via Groq et le lit à voix haute.
    """
    try:
        parler('انتظر كنقرا')

        with state.camera_lock:
            img = state.camera.capture_array()

        img_pil = Image.fromarray(img)
        texte   = pytesseract.image_to_string(img_pil, lang='ara+fra')

        if texte.strip():
            print(f'Texte lu: {texte}')
            parler(groq_darija(f'مكتوب في الصورة: {texte} — قل ذلك بالدارجة'))
        else:
            parler('ماكاين حتى نص')

    except Exception as e:
        print(f'Erreur OCR: {e}')
        parler('ماقدرتش نقرا')
