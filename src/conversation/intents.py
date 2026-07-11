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
KEYWORDS_VISION   = ['شنو', 'قدامي', 'واش', 'شوف', 'وصف']
KEYWORDS_OCR      = ['قرا', 'اقرأ', 'قراءة']
KEYWORDS_HELP     = ['عاون', 'مساعدة', 'شنو تقدر']
# 'سلامة' (avec ة) matche les adieux (بسلامة / مع السلامة) SANS matcher le
# salut courant 'السلام عليكم' / 'سلام' → évite l'arrêt accidentel quand on salue.
KEYWORDS_STOP     = ['وقف', 'بارك', 'إيقاف', 'سلامة']
# Mot de réveil + variantes probables de transcription Whisper (« مرافق »).
KEYWORDS_WAKE     = ['مرافق', 'مرفق', 'مورافيق', 'مرافيق', 'مورافق']

# Message d'aide — partagé entre le mot-clé AIDE et l'intention devinée.
_MSG_AIDE = 'نقدر نعاونك بـ: شنو قدامي باش نوصف ليك، ولا قرا ليا باش نقرا ليك المكتوب'


def _intention_claude(commande: str) -> str:
    """Filet de sécurité STT : le micro déforme les mots (« شنو قدامي » →
    « كثمانين ») — quand aucun mot-clé ne matche, Claude devine l'intention
    probable par similarité phonétique. Retourne SCENE/LIRE/AIDE/CHAT ;
    CHAT si clé absente ou échec (→ question libre, comportement historique).
    Import lazy + jamais d'exception (règle projet)."""
    from config.settings import ANTHROPIC_API_KEY
    if not ANTHROPIC_API_KEY:
        return 'CHAT'
    try:
        from src.ai.claude_client import claude_intention
        return claude_intention(commande)
    except Exception as e:
        print(f'Classification intention échouée ({e}) — question libre')
        return 'CHAT'


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
        parler(_MSG_AIDE)

    # Arrêt — UNIQUEMENT par mot-clé exact (jamais deviné par Claude :
    # une transcription déformée ne doit pas pouvoir éteindre l'assistant).
    elif any(m in commande for m in KEYWORDS_STOP):
        parler('مع السلامة بالتوفيق')
        return False

    # Aucun mot-clé — la transcription est peut-être DÉFORMÉE (micro bruité).
    # Claude devine l'intention probable avant de traiter en question libre.
    else:
        intention = _intention_claude(commande)
        if intention == 'SCENE':
            img = capturer(hq=True)
            # Question par défaut (la transcription originale est du charabia).
            parler(describe_scene(img, 'شنو قدامي؟', hq=True))
        elif intention == 'LIRE':
            lire_texte()
        elif intention == 'AIDE':
            parler(_MSG_AIDE)
        else:  # CHAT — question libre
            parler(get_ai_response(commande))

    return True
