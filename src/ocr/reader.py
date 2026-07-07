"""
Lecture OCR — capture caméra puis délègue au provider OCR (src/providers/ocr.py)
et lit le résultat à voix haute.

Le routage Tesseract local / Claude vision est dans src/providers/ocr.py
(configurer OCR_PROVIDER dans .env). Ici : capture + sortie audio uniquement.
Capture en HAUTE RÉSOLUTION (hq=True) : lire une lettre ou une notice exige
plus de pixels que le flux 640×480 de la boucle AutoScene.
"""
from src.audio.speaker import parler
from src.vision.camera import capturer


def lire_texte() -> None:
    """Capture une image HQ, lit le texte (provider OCR) et l'annonce en darija."""
    try:
        parler('انتظر كنقرا')

        img = capturer(hq=True)

        from src.providers.ocr import read_text
        parler(read_text(img))

    except Exception as e:
        print(f'Erreur OCR: {e}')
        parler('ماقدرتش نقرا')
