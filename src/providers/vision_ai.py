"""
Provider Vision-Langage (VLM) — description de scène à la demande.
Routage selon VISION_AI_PROVIDER dans config/settings.py.

Providers supportés :
  local  — YOLO + Groq (gratuit, défaut)
  claude — Claude multimodal (payant, compréhension de scène riche)

Règles :
  • Appelé UNIQUEMENT sur intention vocale (jamais en continu) → 0 token au repos.
  • Fallback automatique vers 'local' si ANTHROPIC_API_KEY absente — jamais d'exception.
  • Cooldown : réutilise la dernière description si rappelé en < VISION_COOLDOWN s
    (anti double-déclenchement STT + économie de tokens).
  • YOLO/Tesseract/GPS restent toujours locaux — pas de cloud pour ces composants.

Import claude_client en lazy (dans _claude_scene) — testable Windows sans clé.
"""
import time

from config.settings import (
    VISION_AI_PROVIDER, ANTHROPIC_API_KEY, VISION_COOLDOWN, CONF_SEUIL,
    CLAUDE_VISION_MODEL, CLAUDE_VISION_MODEL_HQ,
)
from src.core import state
from src.providers.ai import get_ai_response

_last_time = 0.0
_last_desc = ''


def describe_scene(image, question: str = 'شنو قدامي؟', hq: bool = False) -> str:
    """Décrit la scène via le provider configuré. Retourne une phrase darija.

    hq=True  → appel À LA DEMANDE (question vocale) : modèle haute qualité
               (CLAUDE_VISION_MODEL_HQ, ex. Sonnet) + on ignore le cache (réponse
               fraîche à une vraie question).
    hq=False → boucle automatique continue : modèle économique
               (CLAUDE_VISION_MODEL, ex. Haiku) + cooldown anti double-appel.
    """
    global _last_time, _last_desc
    now = time.time()
    if not hq and _last_desc and (now - _last_time) < VISION_COOLDOWN:
        return _last_desc

    if VISION_AI_PROVIDER == 'claude':
        if ANTHROPIC_API_KEY:
            try:
                desc = _claude_scene(image, question, hq)
            except Exception as e:
                # Claude en panne (Internet, quota, API) → les yeux restent
                # vivants grâce au YOLO local, jamais de silence.
                print(f'Claude vision indisponible ({e}) — fallback YOLO local')
                desc = _local_scene(image)
        else:
            print('ANTHROPIC_API_KEY manquant — fallback vision locale (YOLO)')
            desc = _local_scene(image)
    else:
        desc = _local_scene(image)

    _last_time, _last_desc = time.time(), desc
    return desc


def _claude_scene(image, question: str, hq: bool) -> str:
    from src.ai.claude_client import claude_describe_scene
    model = CLAUDE_VISION_MODEL_HQ if hq else CLAUDE_VISION_MODEL
    # hq=True = question vocale → mémorise (suivi possible). hq=False = boucle
    # auto sans micro → pas de mémoire (pas de conversation + coût continu).
    return claude_describe_scene(image, question, model=model, remember=hq)


def _local_scene(image) -> str:
    """Fallback gratuit : YOLO local → liste d'objets → phrase darija via Groq."""
    r = state.model(image, verbose=False)[0]
    objets = [
        r.names[int(box.cls)]
        for box in r.boxes[:3]
        if float(box.conf) > CONF_SEUIL
    ]
    if objets:
        return get_ai_response(
            f'الأشياء أمام المستخدم: {", ".join(objets)} قل ذلك بالدارجة'
        )
    return 'الطريق واضحة ماكاين والو'
