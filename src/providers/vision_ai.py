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
  • YOLO/Tesseract restent toujours locaux — pas de cloud pour ces composants.

Import claude_client en lazy (dans _claude_scene) — testable Windows sans clé.
"""
import socket
import time
import urllib.error

from config.settings import (
    VISION_AI_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY,
    VISION_COOLDOWN, CONF_SEUIL,
)
from src.core import state
from src.providers.ai import get_ai_response

_last_time = 0.0
_last_desc = ''

# Erreurs réseau/connexion uniquement — pas d'Internet ou hôte injoignable.
_NETWORK_ERRORS = (socket.gaierror, ConnectionError, TimeoutError, OSError,
                    urllib.error.URLError)


def describe_scene(image, question: str = 'شنو قدامي؟') -> str:
    """Décrit la scène via le provider configuré. Retourne une phrase darija."""
    global _last_time, _last_desc
    now = time.time()
    if _last_desc and (now - _last_time) < VISION_COOLDOWN:
        return _last_desc

    if VISION_AI_PROVIDER == 'claude':
        if not ANTHROPIC_API_KEY:
            print('ANTHROPIC_API_KEY manquant — fallback vision locale (YOLO)')
            desc = _local_scene(image)
        else:
            try:
                desc = _claude_scene(image, question)
            except _NETWORK_ERRORS as e:
                print(f'Claude inaccessible (pas d\'Internet ?) — fallback YOLO: {e}')
                desc = _local_scene(image)
            except Exception as e:
                if 'Connection' in type(e).__name__ or 'Timeout' in type(e).__name__:
                    print(f'Claude inaccessible (pas d\'Internet ?) — fallback YOLO: {e}')
                    desc = _local_scene(image)
                else:
                    raise
    elif VISION_AI_PROVIDER == 'openai':
        if not OPENAI_API_KEY:
            print('OPENAI_API_KEY manquant — fallback vision locale (YOLO)')
            desc = _local_scene(image)
        else:
            try:
                desc = _openai_scene(image, question)
            except _NETWORK_ERRORS as e:
                print(f'GPT-4o inaccessible (pas d\'Internet ?) — fallback YOLO: {e}')
                desc = _local_scene(image)
            except Exception as e:
                if 'Connection' in type(e).__name__ or 'Timeout' in type(e).__name__:
                    print(f'GPT-4o inaccessible (pas d\'Internet ?) — fallback YOLO: {e}')
                    desc = _local_scene(image)
                else:
                    raise
    else:
        desc = _local_scene(image)

    _last_time, _last_desc = time.time(), desc
    return desc


def _claude_scene(image, question: str) -> str:
    from src.ai.claude_client import claude_describe_scene
    return claude_describe_scene(image, question)


def _openai_scene(image, question: str) -> str:
    from src.ai.openai_client import gpt4o_describe_scene
    return gpt4o_describe_scene(image, question)


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
