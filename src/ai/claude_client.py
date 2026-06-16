"""
Interface Claude (Anthropic) — cerveau vision+langage à la demande.
Modèles par défaut : claude-haiku-4-5 (multimodal, rapide, le moins cher).

Deux entrées :
  claude_darija(question)            — texte seul → réponse darija courte
  claude_describe_scene(image, q)    — image (numpy RGB) + question → darija

Optimisation des tokens :
  • appelé UNIQUEMENT à la demande (géré en amont) → 0 token au repos
  • image redimensionnée à CLAUDE_IMG_MAX_PX + JPEG qualité CLAUDE_IMG_QUALITY
    (le coût en tokens d'une image monte avec sa résolution → gros levier)
  • max_tokens court (réponse parlée)
  • marqueur de prompt caching sur le prompt système (n'aide que si le prompt
    dépasse le minimum cacheable du modèle ; sans effet sinon, jamais d'erreur)
  • usage loggé (input / cache_read / output) pour suivre la consommation réelle

Import du SDK `anthropic` en lazy (dans _get_client) → ce module reste
importable sur Windows sans la lib ni la clé, pour les tests.
3 tentatives avec backoff (429 / overloaded), comme groq_client.
"""
import base64
import io
import time

from config.settings import (
    ANTHROPIC_API_KEY,
    CLAUDE_TEXT_MODEL, CLAUDE_VISION_MODEL,
    CLAUDE_MAX_TOKENS, CLAUDE_IMG_MAX_PX, CLAUDE_IMG_QUALITY,
)

# Prompt VISION — description de scène pour un malvoyant (sécurité, concision).
_VISION_SYSTEM_PROMPT = (
    'أنت مساعد بصري ذكي للمكفوفين في المغرب. '
    'تتكلم الدارجة المغربية فقط. '
    'وصف المشهد لي قدام المستخدم بإيجاز مفيد للسلامة: '
    'الأشياء المهمة، الاتجاه، والمسافة التقريبية. '
    'ردك قصير جدا — جملة وحدة ولا جوج بحال الإنسان لي كيهضر بسرعة. '
    'أمثلة: كاين طبلة قدامك على بعد متر، وكرسي على اليمين / '
    'الطريق سالكة، سير نيشان / حذاك باب على اليسار، حل بشوية'
)

# Prompt CONVERSATION — questions libres en darija (chaleureux, concis,
# tolérant aux transcriptions imparfaites : demande de répéter au lieu d'inventer).
_CHAT_SYSTEM_PROMPT = (
    'أنت "مرافق"، مساعد ذكي للمكفوفين في المغرب. '
    'كتهضر غير بالدارجة المغربية، بأسلوب دافئ ومطمئن. '
    'جاوب بإيجاز: جملة ولا جوج، بحال واحد كيهضر مع صاحبو. '
    'إلا ما فهمتيش السؤال مزيان، طلب منو يعاودو بلطف، وما تختارعش الجواب. '
    'إلا بغا يعرف شنو قدامو قولو يقول "شنو قدامي"، '
    'وإلا بغا يقرا شي حاجة قولو يقول "قرا ليا".'
)

_client = None


def _get_client():
    """Crée (une fois) le client anthropic. Import lazy → testable sans la lib."""
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _encode_image(image) -> str:
    """numpy RGB array → JPEG redimensionné/compressé → base64 (str)."""
    from PIL import Image
    img = Image.fromarray(image)
    # thumbnail conserve le ratio et ne fait que réduire (jamais agrandir)
    img.thumbnail((CLAUDE_IMG_MAX_PX, CLAUDE_IMG_MAX_PX))
    buf = io.BytesIO()
    img.convert('RGB').save(buf, format='JPEG', quality=CLAUDE_IMG_QUALITY)
    return base64.standard_b64encode(buf.getvalue()).decode('utf-8')


def _log_usage(resp, tag: str) -> None:
    """Trace la consommation de tokens pour suivre le coût."""
    try:
        u = resp.usage
        cache = getattr(u, 'cache_read_input_tokens', 0)
        print(f'Claude {tag} usage: in={u.input_tokens} cache_read={cache} '
              f'out={u.output_tokens}')
    except Exception:
        pass


def _extract_text(resp) -> str:
    """Premier bloc texte de la réponse, ou ''."""
    return next((b.text for b in resp.content if b.type == 'text'), '').strip()


def _system_block(prompt: str):
    """Bloc système avec marqueur de cache (sans effet si prompt trop court)."""
    return [{
        'type': 'text',
        'text': prompt,
        'cache_control': {'type': 'ephemeral'},
    }]


def _retryable(e) -> bool:
    s = str(e).lower()
    return '429' in s or 'rate_limit' in s or 'overloaded' in s or '529' in s


def claude_darija(question: str) -> str:
    """Question texte → réponse darija courte. Message d'erreur si échec."""
    for tentative in range(3):
        try:
            resp = _get_client().messages.create(
                model=CLAUDE_TEXT_MODEL,
                max_tokens=CLAUDE_MAX_TOKENS,
                system=_system_block(_CHAT_SYSTEM_PROMPT),
                messages=[{'role': 'user', 'content': question}],
            )
            _log_usage(resp, 'texte')
            reponse = _extract_text(resp)
            print(f'Claude darija: {reponse}')
            return reponse
        except Exception as e:
            if _retryable(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota Claude, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur Claude: {e}')
                return 'عفوا ماقدرتش نفهم'
    return 'عفوا ماقدرتش نفهم'


def claude_describe_scene(image, question: str = 'شنو قدامي؟') -> str:
    """Image (numpy RGB) + question → description de scène en darija."""
    for tentative in range(3):
        try:
            data = _encode_image(image)
            resp = _get_client().messages.create(
                model=CLAUDE_VISION_MODEL,
                max_tokens=CLAUDE_MAX_TOKENS,
                system=_system_block(_VISION_SYSTEM_PROMPT),
                messages=[{'role': 'user', 'content': [
                    {'type': 'image', 'source': {
                        'type': 'base64',
                        'media_type': 'image/jpeg',
                        'data': data,
                    }},
                    {'type': 'text', 'text': question},
                ]}],
            )
            _log_usage(resp, 'scene')
            reponse = _extract_text(resp)
            print(f'Claude scene: {reponse}')
            return reponse
        except Exception as e:
            if _retryable(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota Claude vision, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur Claude vision: {e}')
                return 'عفوا ماقدرتش نشوف مزيان'
    return 'عفوا ماقدرتش نشوف مزيان'
