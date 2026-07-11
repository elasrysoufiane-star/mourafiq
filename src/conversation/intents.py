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
from src.gps.location import position_actuelle, naviguer

# ── Mots-clés par intention ───────────────────────────────────────────────────
# Exportés pour les tests unitaires
KEYWORDS_GPS      = ['وين', 'فين', 'أين', 'موقع', 'فاين']
KEYWORDS_VISION   = ['شنو', 'قدامي', 'واش', 'شوف', 'وصف']
KEYWORDS_OCR      = ['قرا', 'اقرأ', 'قراءة']
KEYWORDS_HELP     = ['عاون', 'مساعدة', 'شنو تقدر']
# 'سلامة' (avec ة) matche les adieux (بسلامة / مع السلامة) SANS matcher le
# salut courant 'السلام عليكم' / 'سلام' → évite l'arrêt accidentel quand on salue.
KEYWORDS_STOP     = ['وقف', 'بارك', 'إيقاف', 'سلامة']
KEYWORDS_NAVIGATE = ['ودي', 'روح', 'مشي']
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
    # Localisation GPS — adresse réelle (reverse geocoding) si dispo, sinon coords.
    if any(m in commande for m in KEYWORDS_GPS):
        reponse = position_actuelle()
        parler(reponse if reponse else 'ماقدرتش نلقى موقعك دابا')

    # Description de la scène à la demande — Claude VLM (message vocal clair
    # d'indisponibilité si Claude échoue, pas de fallback local, YOLO retiré).
    # La question vocale est transmise telle quelle au VLM (ex. « واش كاين شي حد؟ »).
    # hq=True → modèle haute qualité (Sonnet) car c'est une vraie question posée.
    elif any(m in commande for m in KEYWORDS_VISION):
        img = capturer(hq=True)  # still haute résolution — vraie question posée
        parler(describe_scene(img, commande, hq=True))

    # Lecture OCR
    elif any(m in commande for m in KEYWORDS_OCR):
        lire_texte()

    # Navigation — lieux spécifiques d'abord
    elif 'صيدلية' in commande:
        naviguer('الصيدلية')
    elif any(m in commande for m in ['سبيطار', 'مستشفى']):
        naviguer('السبيطار')
    elif 'جامع' in commande:
        naviguer('الجامع')
    elif 'محطة' in commande:
        naviguer('المحطة')
    elif any(m in commande for m in KEYWORDS_NAVIGATE):
        naviguer('الوجهة')

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
