"""
Thread vision — description automatique continue (scène + OCR), 100% Claude.
YOLO a été retiré (détection locale trop faible pour un usage réel) : plus de
détection d'objets par mots-clés, plus de fallback local hors-ligne. describe_scene()
et read_text() parlent clairement de l'indisponibilité si Claude ne répond pas
(voir src/providers/vision_ai.py, src/providers/ocr.py) — jamais de silence.
"""
import time

from config.settings import AUTO_DESCRIBE_INTERVAL
from src.core import state
from src.audio.speaker import parler
from src.vision.camera import capturer

# Phrases « rien à lire » communes aux deux providers OCR — Tesseract renvoie
# l'une des deux exactement, Claude une variante qui commence pareil (voir
# _local_ocr et _OCR_SYSTEM_PROMPT dans claude_client.py). Sert à ne PAS
# annoncer ces phrases creuses à chaque cycle de la boucle auto (bruyant).
_OCR_SANS_RESULTAT = ('ماكاين حتى نص', 'ماقدرتش نقرا')


def mode_auto_scene() -> None:
    """
    Boucle de description automatique — TOUJOURS active (avec ou sans micro,
    que l'utilisateur parle ou non). Toutes les AUTO_DESCRIBE_INTERVAL
    secondes : capture → describe_scene() + read_text() → parle. Tourne en
    parallèle du thread Conversation ; une commande vocale (« شنو قدامي؟ »
    ou « قرا ليا ») déclenche en plus une réponse immédiate à la demande,
    sans jamais couper cette boucle de fond (mêmes verrous `camera_lock` /
    `audio_lock`).

    Deux appels par cycle, sur la MÊME capture (pas de second accès caméra) :
      • describe_scene() — scène/obstacles par Claude VLM. Si Claude échoue
        (pas d'Internet, quota, clé absente) : message vocal clair
        d'indisponibilité, PLUS de détection locale de secours (YOLO retiré).
      • read_text()      — texte visible (panneau, étiquette...), routé par
        OCR_PROVIDER ('claude' → VLM, sinon Tesseract local) ; les réponses
        creuses (_OCR_SANS_RESULTAT : aucun texte / Tesseract indisponible)
        sont tues pour ne pas les répéter toutes les AUTO_DESCRIBE_INTERVAL s ;
        remember=False (pas un tour de dialogue, voir src/core/memory.py)
    Capture en 640×480 (pas de still HQ ici → pas de stall caméra périodique) ;
    le cooldown VISION_COOLDOWN est respecté côté describe_scene().
    """
    from src.providers.vision_ai import describe_scene
    from src.providers.ocr import read_text
    print(f'Mode description auto démarré (chaque {AUTO_DESCRIBE_INTERVAL:.0f}s)...')

    # Dédoublonnage : ne pas répéter la MÊME annonce à chaque cycle — scène
    # inchangée, même panneau relu, ou message d'indisponibilité Claude
    # (sinon « ماقدرتش نشوف دابا » en boucle infinie sans Internet).
    derniere_desc = ''
    dernier_texte = ''

    while True:
        try:
            time.sleep(AUTO_DESCRIBE_INTERVAL)

            # Ne pas capturer/parler par-dessus une sortie audio en cours.
            if state.conversation_active.is_set():
                continue

            img = capturer()  # flux 640×480 — boucle éco, pas de still HQ ici

            desc = describe_scene(img)
            if desc and desc != derniere_desc:
                parler(desc)
            derniere_desc = desc

            texte = read_text(img, remember=False)
            if (texte and texte != dernier_texte
                    and not any(s in texte for s in _OCR_SANS_RESULTAT)):
                parler(texte)
            dernier_texte = texte

        except Exception as e:
            print(f'Erreur description auto: {e}')
            time.sleep(1)
