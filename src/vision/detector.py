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


def _attendre_parole_finie(max_s: float = 20.0) -> None:
    """Attend que l'assistant ait fini de parler (conversation_active) ET que
    l'utilisateur ait fini sa phrase + son traitement (user_speaking) — la voix
    de l'utilisateur est PRIORITAIRE sur la narration de fond, sinon l'anti-écho
    annulait sa capture dès que la boucle reprenait la parole (« il n'écoute
    pas »). Borne de sécurité max_s : si un signal restait coincé (bug, bruit
    continu classé voix), la narration reprend quand même."""
    deadline = time.monotonic() + max_s
    while ((state.conversation_active.is_set() or state.user_speaking.is_set())
           and time.monotonic() < deadline):
        time.sleep(0.2)


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

    while True:
        try:
            time.sleep(AUTO_DESCRIBE_INTERVAL)

            # ATTENDRE (au lieu de sauter le cycle entier) : fin de la sortie
            # audio en cours ET fin de la parole de l'utilisateur — sa voix est
            # prioritaire sur la narration. Capture APRÈS l'attente → image
            # fraîche au moment où on peut effectivement parler.
            _attendre_parole_finie()

            img = capturer()  # flux 640×480 — boucle éco, pas de still HQ ici

            desc = describe_scene(img)
            # L'utilisateur a pu commencer à parler PENDANT l'appel Claude
            # (~2-4s) → re-vérifier avant de prendre la parole.
            _attendre_parole_finie()
            if desc:
                parler(desc)

            texte = read_text(img, remember=False)
            if texte and not any(s in texte for s in _OCR_SANS_RESULTAT):
                _attendre_parole_finie()
                parler(texte)

        except Exception as e:
            print(f'Erreur description auto: {e}')
            time.sleep(1)
