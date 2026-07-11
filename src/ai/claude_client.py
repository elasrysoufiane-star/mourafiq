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

Échec définitif → ClaudeError (jamais une phrase d'erreur silencieuse) :
la couche providers attrape et bascule — Groq pour le chat, Tesseract pour
l'OCR, message vocal clair pour la scène (pas de fallback local, YOLO
retiré) — l'assistant ne doit JAMAIS perdre la voix parce que Claude est
indisponible.
"""
import base64
import io
import time

from config.settings import (
    ANTHROPIC_API_KEY, ANTHROPIC_API_KEY_FALLBACK,
    CLAUDE_TEXT_MODEL, CLAUDE_VISION_MODEL, CLAUDE_OCR_MODEL,
    CLAUDE_INTENT_MODEL,
    CLAUDE_MAX_TOKENS, CLAUDE_OCR_MAX_TOKENS,
    CLAUDE_IMG_MAX_PX, CLAUDE_IMG_QUALITY,
)
from src.core import memory

# Consigne anti-Markdown commune : le texte part en TTS, qui lit les `*` et `-`
# littéralement. On l'ajoute à chaque prompt système (la synthèse a aussi un
# nettoyage de secours dans src/audio/text_clean.py).
_NO_MARKDOWN = (
    '\nهضر بحال واحد كيهضر بفمو: بلا نجوم (*)، بلا نقط (-)، بلا لائحة، '
    'بلا عناوين. غير جمل عادية.'
)

# Prompt VISION — « les yeux » d'un malvoyant. Priorité absolue : la SÉCURITÉ,
# annoncée en premier et avec insistance. Puis position, distance, et quoi faire.
# Couvre la rue, l'intérieur et la lecture. Court (il écoute, il ne lit pas).
_VISION_SYSTEM_PROMPT = (
    'أنت "مرافق"، نتا هوما العينين د واحد المكفوف فالمغرب. '
    'كتهضر غير الدارجة المغربية. دورك يتحرك بأمان ويفهم شنو دايرين بيه.\n'
    'القواعد:\n'
    '١. السلامة قبل كلشي: إلا كاين شي خطر (طوموبيل، دراجة، حفرة، درج، ماء، '
    'حاجة طايحة، شي حد جاي عليه) قولو فاللول وبقوة وعاود حقق عليه: '
    '"عندك! كاين درج قدامك بزاف، وقف!".\n'
    '٢. كن دقيق فالمكان والمسافة: قدامك / على اليمين / على اليسار / وراك، '
    'والمسافة بالتقريب: "حدا رجليك"، "على بعد خطوتين"، "بعيد شوية".\n'
    '٣. قولو شنو يدير: "وقف"، "دور على اليمين"، "زيد بشوية"، "طلع بالعقل".\n'
    '٤. قصير وواضح: جملة ولا جوج، الأهم فاللول.\n'
    '٥. إلا الطريق سالمة طمنو: "الطريق سالكة، سير نيشان".\n'
    '٦. إلا طلب منك تقرا شي مكتوب، قرا ليه النص وقولو المعنى بالدارجة.\n'
    'كون هادي ومطمئن، بحال صاحب كيمشي حداه.'
    + _NO_MARKDOWN
)

# Prompt CONVERSATION — compagnon darija (chaleureux, concis, patient,
# tolérant aux transcriptions imparfaites : demande de répéter au lieu d'inventer).
_CHAT_SYSTEM_PROMPT = (
    'أنت "مرافق"، مساعد وصاحب للمكفوفين في المغرب. '
    'كتهضر غير بالدارجة المغربية، بأسلوب دافئ ومطمئن وصبور. '
    'جاوب بإيجاز: جملة ولا جوج، بحال واحد كيهضر مع صاحبو. '
    'إلا ما فهمتيش السؤال مزيان، طلب منو يعاودو بلطف، وما تختارعش الجواب. '
    'إلا بغا يعرف شنو قدامو قولو يقول "شنو قدامي"، '
    'وإلا بغا يقرا شي حاجة قولو يقول "قرا ليا".'
    + _NO_MARKDOWN
)

# Prompt OCR — lecture de texte pour un malvoyant. Lit ET donne le sens utile.
_OCR_SYSTEM_PROMPT = (
    'أنت "مرافق"، كتقرا للمكفوفين فالمغرب. شوف التصويرة وقرا النص لي فيها. '
    'كتهضر غير الدارجة المغربية وكتكون واضح.\n'
    '- إلا كانت رسالة ولا ورقة: قرا الأهم وقول المعنى بإيجاز.\n'
    '- إلا كان دواء: قول سميتو والجرعة إلا بانو.\n'
    '- إلا كانت لافطة ولا بلاكة ولا سومة: قول شنو مكتوب فيها.\n'
    '- إلا ماكاينش نص واضح، قول غير: "ماكاين حتى نص نقدر نقراه".'
    + _NO_MARKDOWN
)

# Prompt INTENTION — filet de sécurité STT : le micro (adaptateur jack→USB)
# déforme les mots (« شنو قدامي » → « كثمانين »). Quand aucun mot-clé ne matche,
# Claude devine l'intention PROBABLE par similarité phonétique/contexte, au
# lieu de traiter le charabia comme une question libre. Réponse = UN mot.
_INTENT_SYSTEM_PROMPT = (
    'المستخدم مكفوف مغربي كيهضر بالدارجة عبر ميكروفون رديء: النص اللي كيجيك '
    'من التعرف الصوتي غالبا مشوه ولا ناقص. مهمتك: حدد شنو غالبا بغا المستخدم، '
    'حتى إلا كانت الكلمات مشوهة (قارن النطق والحروف المتشابهة).\n'
    'جاوب بكلمة وحدة فقط من هاد اللائحة:\n'
    'SCENE — بغا وصف اللي قدامو (أمثلة: شنو قدامي، شوف شنو كاين، وصف ليا)\n'
    'LIRE — بغا تقرا ليه نص مكتوب/ورقة/دوا (أمثلة: قرا ليا، اقرأ)\n'
    'AIDE — بغا يعرف شنو تقدر دير ليه (أمثلة: عاوني، مساعدة)\n'
    'CHAT — سؤال حر ولا هضرة عادية واضحة\n'
    'إلا ما كنتيش متأكد بين SCENE/LIRE/AIDE، جاوب CHAT.'
)

# Thinking désactivé explicitement : sur claude-sonnet-5 le thinking adaptatif
# est ACTIF par défaut quand le paramètre est omis — il consommerait le budget
# max_tokens (réponse parlée courte) et ajouterait de la latence vocale.
# 'disabled' est accepté par haiku-4-5 / sonnet-4-6 / sonnet-5 / opus-4-8.
_THINKING_OFF = {'type': 'disabled'}


class ClaudeError(Exception):
    """Échec définitif d'un appel Claude (après retries). La couche providers
    l'attrape pour basculer (Groq pour le chat, Tesseract pour l'OCR, message
    vocal clair pour la scène — pas de fallback local, YOLO retiré)."""


# Un client anthropic par clé API (principale + secours), créé à la demande.
_clients = {}

# Timeout par requête. Le SDK anthropic défaut à 10 MIN (httpx) — sur un réseau
# Pi dégradé/instable, un appel qui traîne bloque tout le cycle AutoScene
# (silence total : ni description, ni erreur, ni fallback) pendant potentiellement
# plusieurs minutes. 15s est largement suffisant pour un appel VLM/texte normal.
_TIMEOUT_S = 15.0


def _get_client(api_key: str):
    """Client anthropic pour une clé donnée (créé une fois, mis en cache).
    Import lazy → testable sans la lib. max_retries=0 : les retries sont gérés
    dans _create() (log + backoff visibles) — le SDK ne doit pas retry en
    silence, ça retarderait l'erreur/le fallback parlé."""
    if api_key not in _clients:
        import anthropic
        _clients[api_key] = anthropic.Anthropic(
            api_key=api_key, timeout=_TIMEOUT_S, max_retries=0,
        )
    return _clients[api_key]


def _api_keys() -> list:
    """Clés à essayer dans l'ordre : PRINCIPALE puis SECOURS (si définie)."""
    return [k for k in (ANTHROPIC_API_KEY, ANTHROPIC_API_KEY_FALLBACK) if k]


def _create(tag: str = '', **kwargs):
    """messages.create avec DOUBLE robustesse :
      1. retries backoff (429 / overloaded / 529) sur la MÊME clé ;
      2. bascule sur la clé de SECOURS si la principale est épuisée/invalide/en panne.
    ClaudeError si toutes les clés échouent → la couche providers bascule
    (Groq pour le chat, Tesseract pour l'OCR, message vocal clair pour la scène)."""
    keys = _api_keys()
    if not keys:
        raise ClaudeError('ANTHROPIC_API_KEY manquante')
    derniere_err = None
    for i, key in enumerate(keys):
        for tentative in range(3):
            try:
                return _get_client(key).messages.create(**kwargs)
            except Exception as e:
                derniere_err = e
                if _retryable(e) and tentative < 2:
                    attente = 5 * (2 ** tentative)
                    print(f'Quota Claude {tag}, attente {attente}s...')
                    time.sleep(attente)
                    continue
                break  # échec non-retryable ou retries épuisés → clé suivante
        if i < len(keys) - 1:
            print(f'Clé Claude #{i + 1} en échec ({derniere_err}) — bascule sur la clé de secours')
    print(f'Erreur Claude {tag}: {derniere_err}')
    raise ClaudeError(str(derniere_err))


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
    """Question texte → réponse darija courte. Retries + bascule de clé API dans
    _create(). ClaudeError si échec définitif (l'appelant — providers.ai —
    bascule alors sur Groq)."""
    # Suivi VISUEL : si une image a été vue à la demande, on la rattache à la
    # question texte → « شنو كانت الحاجة الزرقاء؟ » marche même sans nouvelle
    # capture. CLAUDE_TEXT_MODEL (Opus) est multimodal.
    last_img = memory.get_last_image()
    if last_img:
        user_content = [
            {'type': 'image', 'source': {
                'type': 'base64', 'media_type': 'image/jpeg', 'data': last_img,
            }},
            {'type': 'text', 'text': question},
        ]
    else:
        user_content = question
    resp = _create(
        tag='texte',
        model=CLAUDE_TEXT_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        thinking=_THINKING_OFF,
        system=_system_block(_CHAT_SYSTEM_PROMPT),
        messages=memory.get_history() + [{'role': 'user', 'content': user_content}],
    )
    _log_usage(resp, 'texte')
    reponse = _extract_text(resp)
    print(f'Claude darija: {reponse}')
    memory.add_turn(question, reponse)
    return reponse


def claude_intention(commande: str) -> str:
    """Classifie une transcription darija BRUITÉE en intention probable.
    Retourne 'SCENE' | 'LIRE' | 'AIDE' | 'CHAT' (CHAT par défaut si ambigu).
    Modèle rapide (CLAUDE_INTENT_MODEL, haiku) + réponse d'un seul mot → ~1s.
    JAMAIS d'intention ARRÊT ici (sécurité : l'arrêt exige le mot-clé exact).
    Pas de mémoire de conversation (classification pure, pas un tour de dialogue).
    ClaudeError si échec — l'appelant retombe sur la question libre."""
    resp = _create(
        tag='intent',
        model=CLAUDE_INTENT_MODEL,
        max_tokens=10,
        thinking=_THINKING_OFF,
        system=[{'type': 'text', 'text': _INTENT_SYSTEM_PROMPT}],
        messages=[{'role': 'user', 'content': commande}],
    )
    mot = _extract_text(resp).upper()
    for intention in ('SCENE', 'LIRE', 'AIDE'):
        if intention in mot:
            print(f'Intention devinée: {intention} (transcription: {commande})')
            return intention
    return 'CHAT'


def _vision_call(image, question, system_prompt, model, max_tokens, tag,
                 remember=False):
    """Appel multimodal générique (image + texte) avec retries. Usine commune
    à la description de scène et à la lecture OCR.
    ClaudeError si échec définitif → la couche providers bascule (message vocal
    clair pour la scène, pas de fallback local — YOLO retiré ; Tesseract pour l'OCR).

    remember=True → enregistre l'échange (question + réponse) ET garde l'image
    pour un suivi visuel en chat, UNIQUEMENT en cas de succès (un échec ne
    pollue ni la mémoire ni la dernière image). L'historique reste TEXTE ;
    l'image, elle, n'est gardée que comme « dernière vue » (memory.set_last_image)."""
    data = _encode_image(image)
    resp = _create(
        tag=tag,
        model=model,
        max_tokens=max_tokens,
        thinking=_THINKING_OFF,
        system=_system_block(system_prompt),
        messages=memory.get_history() + [{'role': 'user', 'content': [
            {'type': 'image', 'source': {
                'type': 'base64',
                'media_type': 'image/jpeg',
                'data': data,
            }},
            {'type': 'text', 'text': question},
        ]}],
    )
    _log_usage(resp, tag)
    reponse = _extract_text(resp)
    print(f'Claude {tag}: {reponse}')
    if remember:
        memory.set_last_image(data)
        memory.add_turn(question, reponse)
    return reponse


def claude_describe_scene(image, question: str = 'شنو قدامي؟', model: str = None,
                          remember: bool = True, max_tokens: int = None) -> str:
    """Image (numpy RGB) + question → description de scène en darija.
    `model` permet de choisir le modèle (continu vs à la demande).
    `max_tokens` : budget séparé — riche à la demande (CLAUDE_MAX_TOKENS),
    court en boucle de fond (CLAUDE_SCENE_AUTO_MAX_TOKENS) — voir providers.vision_ai.
    `remember` : True à la demande (suivi possible), False en boucle auto de
    fond (narration continue, pas un tour de dialogue — évite un contexte
    qui grossit en continu).
    ClaudeError si échec → providers.vision_ai renvoie un message vocal clair
    d'indisponibilité (pas de fallback local, YOLO retiré)."""
    return _vision_call(
        image, question, _VISION_SYSTEM_PROMPT,
        model or CLAUDE_VISION_MODEL, max_tokens or CLAUDE_MAX_TOKENS,
        'scene', remember=remember,
    )


def claude_read_text(image, model: str = None, remember: bool = True) -> str:
    """Image (numpy RGB) → lecture + sens du texte en darija (OCR par VLM).
    Plus de tokens que la scène (peut contenir une lettre entière).
    `model` : à la demande = Opus (CLAUDE_OCR_MODEL, précision max) ; boucle de
    fond = modèle continu — choisi par providers.ocr selon `remember`.
    `remember` : True à la demande (suivi possible : « عاود », « شنو التاريخ؟ »),
    False en boucle AutoScene (lecture de fond, pas un tour de dialogue).
    ClaudeError si échec → providers.ocr bascule sur Tesseract local."""
    return _vision_call(
        image, 'قرا ليا هاد المكتوب', _OCR_SYSTEM_PROMPT,
        model or CLAUDE_OCR_MODEL, CLAUDE_OCR_MAX_TOKENS,
        'ocr', remember=remember,
    )
