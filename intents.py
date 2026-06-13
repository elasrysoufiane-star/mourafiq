import state
from audio import parler
from groq_service import groq_darija
from ocr_reader import lire_texte
from gps import get_gps, naviguer


def process_command(commande):
    """
    Route la commande vocale reconnue vers l'action correspondante.
    Retourne False si l'utilisateur demande à arrêter, True sinon.
    """

    # Localisation GPS
    if any(m in commande for m in ['وين', 'فين', 'أين', 'موقع', 'فاين']):
        lat, lon = get_gps()
        if lat and lat != 0:
            parler(groq_darija(f'موقع المستخدم: {lat:.4f}, {lon:.4f} أخبره بالدارجة'))
        else:
            parler('ماقدرتش نلقى موقعك دابا')

    # Description de la scène visible
    elif any(m in commande for m in ['شنو', 'قدامي', 'واش', 'شوف', 'وصف']):
        with state.camera_lock:
            img = state.camera.capture_array()
        r = state.model(img, verbose=False)[0]
        objets = [
            r.names[int(box.cls)]
            for box in r.boxes[:3]
            if float(box.conf) > 0.5
        ]
        if objets:
            parler(groq_darija(f'الأشياء أمام المستخدم: {", ".join(objets)} قل ذلك بالدارجة'))
        else:
            parler('الطريق واضحة ماكاين والو')

    # Lecture OCR
    elif any(m in commande for m in ['قرا', 'اقرأ', 'قراءة']):
        lire_texte()

    # Navigation vers des lieux communs
    elif 'صيدلية' in commande:
        naviguer('الصيدلية')
    elif any(m in commande for m in ['سبيطار', 'مستشفى']):
        naviguer('السبيطار')
    elif 'جامع' in commande:
        naviguer('الجامع')
    elif 'محطة' in commande:
        naviguer('المحطة')
    elif any(m in commande for m in ['ودي', 'روح', 'مشي']):
        naviguer('الوجهة')

    # Aide
    elif any(m in commande for m in ['عاون', 'مساعدة', 'شنو تقدر']):
        parler('نقدر نعاونك بـ: شنو قدامي، قرا ليا، وين أنا، ودي للصيدلية')

    # Arrêt de l'assistant
    elif any(m in commande for m in ['وقف', 'بارك', 'إيقاف', 'سلام']):
        parler('مع السلامة بالتوفيق')
        return False

    # Question libre → Groq LLaMA
    else:
        parler(groq_darija(commande))

    return True
