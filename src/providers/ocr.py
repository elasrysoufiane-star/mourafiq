"""
Provider OCR — lecture de texte depuis une image.
Routage selon OCR_PROVIDER dans config/settings.py.

Providers supportés :
  local  — Tesseract (ara+fra) + reformulation Groq (gratuit, hors-ligne, défaut)
  claude — Claude vision lit + résume (arabe/français/manuscrit/panneaux, payant)

Règles (cohérentes avec les autres providers) :
  • Mode par défaut = gratuit (local). Ne pas changer le défaut dans le code.
  • OCR_PROVIDER=claude → si ANTHROPIC_API_KEY absente OU échec (pas d'Internet),
    fallback automatique vers Tesseract local — jamais d'exception non gérée.
  • read_text() retourne TOUJOURS une phrase darija prête à être lue à voix haute
    (y compris « ماكاين حتى نص » quand il n'y a rien). L'appelant n'a qu'à parler.
  • remember=False (boucle AutoScene) : ne mémorise pas — lecture de fond
    répétée toutes les AUTO_DESCRIBE_INTERVAL s, pas un tour de dialogue.

Imports lazy (pytesseract/PIL/claude_client) — testable sur Windows sans matériel.
"""
from config.settings import OCR_PROVIDER, ANTHROPIC_API_KEY


def read_text(image, remember: bool = True) -> str:
    """Lit le texte d'une image (numpy RGB) → phrase darija à lire à voix haute.
    `remember` : True à la demande (« قرا ليا »), False dans la boucle AutoScene
    (évite de polluer la mémoire de conversation avec une lecture de fond)."""
    if OCR_PROVIDER == 'claude':
        if ANTHROPIC_API_KEY:
            try:
                return _claude_ocr(image, remember)
            except Exception as e:
                print(f'OCR Claude échec ({e}) — fallback Tesseract')
        else:
            print('ANTHROPIC_API_KEY manquant — fallback OCR Tesseract')
    return _local_ocr(image)


def _claude_ocr(image, remember: bool) -> str:
    from src.ai.claude_client import claude_read_text
    return claude_read_text(image, remember=remember)


def _local_ocr(image) -> str:
    """Tesseract (ara+fra) → reformulation darija via Groq. Gratuit, hors-ligne."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        print('AVERTISSEMENT: pytesseract/PIL absent (pip install pytesseract pillow)')
        return 'ماقدرتش نقرا — Tesseract غير متوفر'

    texte = pytesseract.image_to_string(Image.fromarray(image), lang='ara+fra')
    if not texte.strip():
        return 'ماكاين حتى نص'

    apercu = texte[:100] + '...' if len(texte) > 100 else texte
    print(f'Texte lu (Tesseract): {apercu}')
    from src.providers.ai import get_ai_response
    return get_ai_response(f'مكتوب في الصورة: {texte} — قل ذلك بالدارجة')
