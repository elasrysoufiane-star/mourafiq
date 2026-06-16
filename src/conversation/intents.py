"""
Routage des commandes vocales vers les actions correspondantes.

Les constantes KEYWORDS_* sont définies au niveau module pour être
importables et testables sans dépendances matérielles.
"""
from src.core import state
from src.audio.speaker import parler
from src.providers.ai import get_ai_response
from src.providers.vision_ai import describe_scene
from src.ocr.reader import lire_texte
from src.gps.location import get_gps, naviguer

# ── Mots-clés par intention ───────────────────────────────────────────────────
# Exportés pour les tests unitaires
KEYWORDS_GPS      = ['وين', 'فين', 'أين', 'موقع', 'فاين']
KEYWORDS_VISION   = ['شنو', 'قدامي', 'واش', 'شوف', 'وصف']
KEYWORDS_OCR      = ['قرا', 'اقرأ', 'قراءة']
KEYWORDS_HELP     = ['عاون', 'مساعدة', 'شنو تقدر']
KEYWORDS_STOP     = ['وقف', 'بارك', 'إيقاف', 'سلام']
KEYWORDS_NAVIGATE = ['ودي', 'روح', 'مشي']


def process_command(commande: str) -> bool:
    """
    Route la commande vers l'action correspondante.
    Retourne False si l'utilisateur demande l'arrêt, True sinon.
    """
    # Localisation GPS
    if any(m in commande for m in KEYWORDS_GPS):
        lat, lon = get_gps()
        if lat and lat != 0:
            parler(get_ai_response(f'موقع المستخدم: {lat:.4f}, {lon:.4f} أخبره بالدارجة'))
        else:
            parler('ماقدرتش نلقى موقعك دابا')

    # Description de la scène à la demande — VLM (Claude) ou fallback YOLO local.
    # La question vocale est transmise telle quelle au VLM (ex. « واش كاين شي حد؟ »).
    elif any(m in commande for m in KEYWORDS_VISION):
        with state.camera_lock:
            img = state.camera.capture_array()
        parler(describe_scene(img, commande))

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
        parler('نقدر نعاونك بـ: شنو قدامي، قرا ليا، وين أنا، ودي للصيدلية')

    # Arrêt
    elif any(m in commande for m in KEYWORDS_STOP):
        parler('مع السلامة بالتوفيق')
        return False

    # Question libre → Groq LLaMA
    else:
        parler(get_ai_response(commande))

    return True
