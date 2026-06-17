"""
Lecture OCR — capture caméra puis délègue au provider OCR (src/providers/ocr.py)
et lit le résultat à voix haute.

Le routage Tesseract local / Claude vision est dans src/providers/ocr.py
(configurer OCR_PROVIDER dans .env). Ici : capture + sortie audio uniquement.
"""
from src.core import state
from src.audio.speaker import parler


def lire_texte() -> None:
    """Capture une image, lit le texte (provider OCR) et l'annonce en darija."""
    try:
        parler('انتظر كنقرا')

        with state.camera_lock:
            img = state.camera.capture_array()

        from src.providers.ocr import read_text
        parler(read_text(img))

    except Exception as e:
        print(f'Erreur OCR: {e}')
        parler('ماقدرتش نقرا')
