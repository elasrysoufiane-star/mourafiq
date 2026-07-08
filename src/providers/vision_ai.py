"""
Provider Vision-Langage (VLM) — description de scène à la demande et dans la
boucle automatique. 100% Claude : YOLO a été retiré (détection locale par
mots-clés jugée trop faible pour un usage réel) — plus de fallback hors-ligne.

Règles :
  • Cooldown : réutilise la dernière description si rappelé en < VISION_COOLDOWN s
    (anti double-déclenchement STT + économie de tokens).
  • Si ANTHROPIC_API_KEY absente OU appel Claude en échec (Internet, quota...) :
    message vocal clair d'indisponibilité — jamais de silence, jamais d'exception
    non gérée, mais plus de détection locale de secours (voir .claude/memory/decisions.md).

Import claude_client en lazy (dans _claude_scene) — testable Windows sans clé.
"""
import time

from config.settings import (
    ANTHROPIC_API_KEY, VISION_COOLDOWN,
    CLAUDE_VISION_MODEL, CLAUDE_VISION_MODEL_HQ,
    CLAUDE_MAX_TOKENS, CLAUDE_SCENE_AUTO_MAX_TOKENS,
)

_last_time = 0.0
_last_desc = ''

_INDISPONIBLE = 'ماقدرتش نشوف دابا، تأكد من الأنترنت ديالك'


def describe_scene(image, question: str = 'شنو قدامي؟', hq: bool = False) -> str:
    """Décrit la scène via Claude. Retourne une phrase darija.

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

    if not ANTHROPIC_API_KEY:
        print('ANTHROPIC_API_KEY manquant — vision indisponible (pas de fallback local)')
        desc = _INDISPONIBLE
    else:
        try:
            desc = _claude_scene(image, question, hq)
        except Exception as e:
            print(f'Claude vision indisponible ({e}) — pas de fallback local')
            desc = _INDISPONIBLE

    _last_time, _last_desc = time.time(), desc
    return desc


def _claude_scene(image, question: str, hq: bool) -> str:
    from src.ai.claude_client import claude_describe_scene
    model = CLAUDE_VISION_MODEL_HQ if hq else CLAUDE_VISION_MODEL
    # Budget tokens séparé : riche à la demande (vraie question), court dans la
    # boucle de fond (narration brève → ne monopolise pas la parole, moins d'écho).
    max_tokens = CLAUDE_MAX_TOKENS if hq else CLAUDE_SCENE_AUTO_MAX_TOKENS
    # hq=True = question vocale → mémorise (suivi possible). hq=False = boucle
    # auto de fond (narration continue, pas un tour de dialogue) → pas de
    # mémoire, pour éviter un contexte qui grossit en continu.
    return claude_describe_scene(image, question, model=model, remember=hq,
                                 max_tokens=max_tokens)
