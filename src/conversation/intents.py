"""
Routage des commandes vocales vers les actions correspondantes.

Les constantes KEYWORDS_* sont définies au niveau module pour être
importables et testables sans dépendances matérielles.
"""
from src.audio.speaker import parler
from src.providers.ai import get_ai_response
from src.providers.vision_ai import describe_scene
from src.vision.camera import capturer
from src.ocr.reader import lire_texte

# ── Mots-clés par intention ───────────────────────────────────────────────────
# Exportés pour les tests unitaires
# PAS de 'شنو' ni 'واش' seuls : ce sont les mots interrogatifs de base de la
# darija — ils matcheraient quasiment TOUTE question libre (« واش غادية طيح
# الشتا؟ ») et déclencheraient la caméra au lieu du chat. Le chat garde le
# suivi visuel via memory.get_last_image().
KEYWORDS_VISION   = ['قدامي', 'شوف', 'وصف']
KEYWORDS_OCR      = ['قرا', 'اقرأ', 'قراءة']
KEYWORDS_HELP     = ['عاون', 'مساعدة', 'شنو تقدر']
# 'سلامة' (avec ة) matche les adieux (بسلامة / مع السلامة) SANS matcher le
# salut courant 'السلام عليكم' / 'سلام' → évite l'arrêt accidentel quand on salue.
# 'باراكا'/'بركا' (« assez ») remplacent 'بارك' qui matchait les remerciements
# courants ('الله يبارك فيك') et arrêtait l'app quand l'utilisateur dit merci.
KEYWORDS_STOP     = ['وقف', 'باراكا', 'بركا', 'إيقاف', 'سلامة']
# Mot de réveil + variantes probables de transcription Whisper (« مرافق »).
KEYWORDS_WAKE     = ['مرافق', 'مرفق', 'مورافيق', 'مرافيق', 'مورافق']


def contient_wake(commande: str) -> bool:
    """True si la commande contient le mot de réveil (ou une variante)."""
    return any(w in commande for w in KEYWORDS_WAKE)


def retirer_wake(commande: str) -> str:
    """Retire le mot de réveil de la commande, retourne le reste nettoyé."""
    out = commande
    for w in KEYWORDS_WAKE:
        out = out.replace(w, ' ')
    return out.strip(' ،.؟!')


def process_command(commande: str) -> bool:
    """
    Route la commande vers l'action correspondante.
    Retourne False si l'utilisateur demande l'arrêt, True sinon.
    """
    # Description de la scène à la demande — Claude VLM (message vocal clair
    # d'indisponibilité si Claude échoue, pas de fallback local, YOLO retiré).
    # La question vocale est transmise telle quelle au VLM (ex. « واش كاين شي حد؟ »).
    # hq=True → modèle haute qualité (Sonnet) car c'est une vraie question posée.
    if any(m in commande for m in KEYWORDS_VISION):
        img = capturer(hq=True)  # still haute résolution — vraie question posée
        parler(describe_scene(img, commande, hq=True))

    # Lecture OCR
    elif any(m in commande for m in KEYWORDS_OCR):
        lire_texte()

    # Aide
    elif any(m in commande for m in KEYWORDS_HELP):
        parler('نقدر نعاونك بـ: شنو قدامي باش نوصف ليك، ولا قرا ليا باش نقرا ليك المكتوب')

    # Arrêt
    elif any(m in commande for m in KEYWORDS_STOP):
        parler('مع السلامة بالتوفيق')
        return False

    # Question libre → Groq LLaMA
    else:
        parler(get_ai_response(commande))

    return True
