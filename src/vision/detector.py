"""
Thread vision — description automatique continue (scène + OCR), 100% Claude.
YOLO a été retiré (détection locale trop faible pour un usage réel) : plus de
détection d'objets par mots-clés, plus de fallback local hors-ligne. describe_scene()
et read_text() parlent clairement de l'indisponibilité si Claude ne répond pas
(voir src/providers/vision_ai.py, src/providers/ocr.py) — jamais de silence.
"""
import time
from concurrent.futures import ThreadPoolExecutor

from config.settings import AUTO_DESCRIBE_INTERVAL, VOICE_PRIORITY
from src.core import state
from src.audio.speaker import parler
from src.audio.text_clean import couper_phrase_incomplete
from src.vision.camera import capturer

# Phrases « rien à lire » communes aux deux providers OCR — Tesseract renvoie
# l'une exactement, Claude la phrase sentinelle du prompt (_OCR_SYSTEM_PROMPT)
# mais parfois avec des VARIANTES de formulation (« ماكاينش فيها حتى نص... »,
# vu dans les logs réels : la variante échappait au filtre et la phrase creuse
# était parlée à chaque cycle). Sert à ne PAS annoncer ces réponses vides.
_OCR_SANS_RESULTAT = (
    'ماكاين حتى نص',        # sentinelle exacte du prompt
    'ماكاينش فيها حتى نص',  # variante observée (log 2026-07-11)
    'ماكاينش حتى نص',
    'ما كاين حتى نص',
    'ماكاين أي نص',
    'ماكاينش أي نص',
    'ماكاين أي كتابة',
    'ماقدرتش نقرا',         # Tesseract indisponible
)


def _attendre_parole_finie(max_s: float = 20.0) -> None:
    """Attend que l'assistant ait fini de parler (conversation_active — toujours,
    ne jamais parler par-dessus sa propre voix), et — SEULEMENT si
    VOICE_PRIORITY=1 — que l'utilisateur ait fini sa phrase (user_speaking).
    Par défaut (VOICE_PRIORITY=0) la narration N'attend PAS le micro : la STT
    est inutilisable sur le matériel actuel et le moindre bruit classé « voix »
    par le VAD suspendait la narration → longs silences. Borne de sécurité
    max_s : si un signal restait coincé, la narration reprend quand même."""
    deadline = time.monotonic() + max_s
    while time.monotonic() < deadline:
        occupe = state.conversation_active.is_set() or (
            VOICE_PRIORITY and state.user_speaking.is_set())
        if not occupe:
            return
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

    # Scène et OCR partent en PARALLÈLE sur la même capture (appels réseau IO) :
    # temps mort = max(scène, OCR) ≈ 2.5s au lieu de la somme ≈ 5s → moins de
    # silence entre narrations et moins de décalage caméra→parole.
    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='AutoSceneAPI')

    while True:
        try:
            time.sleep(AUTO_DESCRIBE_INTERVAL)

            # ATTENDRE (au lieu de sauter le cycle entier) : fin de la sortie
            # audio en cours ET fin de la parole de l'utilisateur — sa voix est
            # prioritaire sur la narration. Capture APRÈS l'attente → image
            # fraîche au moment où on peut effectivement parler.
            _attendre_parole_finie()

            img = capturer()  # flux 640×480 — boucle éco, pas de still HQ ici

            # Les deux appels Claude en parallèle sur la même capture.
            futur_scene = executor.submit(describe_scene, img)
            futur_texte = executor.submit(read_text, img, remember=False)

            # Les réponses plafonnées par max_tokens tombent souvent en plein
            # mot → couper à la dernière phrase complète (TTS propre).
            desc = couper_phrase_incomplete(futur_scene.result())
            # Une sortie audio a pu démarrer pendant l'appel → re-vérifier
            # avant de prendre la parole.
            _attendre_parole_finie()
            if desc:
                parler(desc)

            texte = couper_phrase_incomplete(futur_texte.result())
            if texte and not any(s in texte for s in _OCR_SANS_RESULTAT):
                _attendre_parole_finie()
                parler(texte)

        except Exception as e:
            print(f'Erreur description auto: {e}')
            time.sleep(1)
