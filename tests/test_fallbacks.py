"""
Tests des fallbacks providers quand Claude est indisponible (panne, quota,
pas d'Internet). Règle projet n°2 : jamais d'exception non gérée — l'assistant
d'un malvoyant ne doit JAMAIS devenir silencieux, même sans bascule locale.

Chaîne testée :
  claude_client  → lève ClaudeError après retries (au lieu d'avaler l'erreur)
  providers.ai   → attrape → fallback Groq
  providers.vision_ai → attrape → message vocal clair (YOLO retiré, plus de
                        détection locale de secours)
  providers.ocr  → attrape → fallback Tesseract

Fonctionne sur Windows sans matériel, sans SDK anthropic, sans clé API.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai import claude_client
from src.ai.claude_client import ClaudeError
from src.core import memory
from src.providers import ai as providers_ai
from src.providers import vision_ai as providers_vision
from src.providers import ocr as providers_ocr


class _FakeMessages:
    def create(self, **kwargs):
        raise RuntimeError('connexion impossible (test)')


class _FakeClient:
    messages = _FakeMessages()


def _avec_client_casse(fonction):
    """Exécute `fonction` avec un client Claude qui échoue, puis restaure."""
    ancien_client = claude_client._client
    ancien_encode = claude_client._encode_image
    claude_client._client = _FakeClient()
    claude_client._encode_image = lambda image: 'fake-base64'
    try:
        return fonction()
    finally:
        claude_client._client = ancien_client
        claude_client._encode_image = ancien_encode


def test_claude_darija_leve_claude_error():
    """Échec non-retryable → ClaudeError immédiate (pas de phrase avalée)."""
    memory.reset()
    def appel():
        try:
            claude_client.claude_darija('سلام')
        except ClaudeError:
            return True
        return False
    assert _avec_client_casse(appel), 'claude_darija doit lever ClaudeError'
    assert memory.get_history() == [], 'un échec ne doit pas polluer la mémoire'


def test_claude_scene_leve_claude_error():
    def appel():
        try:
            claude_client.claude_describe_scene(object())
        except ClaudeError:
            return True
        return False
    assert _avec_client_casse(appel), 'claude_describe_scene doit lever ClaudeError'


def test_claude_ocr_leve_claude_error():
    def appel():
        try:
            claude_client.claude_read_text(object())
        except ClaudeError:
            return True
        return False
    assert _avec_client_casse(appel), 'claude_read_text doit lever ClaudeError'


def test_ai_fallback_groq():
    """AI_PROVIDER=claude + Claude en panne → réponse Groq, pas d'exception."""
    anciens = (providers_ai.AI_PROVIDER, providers_ai.ANTHROPIC_API_KEY,
               providers_ai._claude_darija, providers_ai._groq_darija)
    def _casse(question):
        raise ClaudeError('panne (test)')
    providers_ai.AI_PROVIDER = 'claude'
    providers_ai.ANTHROPIC_API_KEY = 'sk-ant-test'
    providers_ai._claude_darija = _casse
    providers_ai._groq_darija = lambda q: 'جواب من غروق'
    try:
        assert providers_ai.get_ai_response('سلام') == 'جواب من غروق'
    finally:
        (providers_ai.AI_PROVIDER, providers_ai.ANTHROPIC_API_KEY,
         providers_ai._claude_darija, providers_ai._groq_darija) = anciens


def test_vision_fallback_message_clair():
    """Claude en panne → message vocal clair d'indisponibilité (YOLO retiré,
    plus de détection locale de secours), jamais d'exception."""
    anciens = (providers_vision.ANTHROPIC_API_KEY,
               providers_vision._claude_scene,
               providers_vision._last_desc, providers_vision._last_time)
    def _casse(image, question, hq):
        raise ClaudeError('panne (test)')
    providers_vision.ANTHROPIC_API_KEY = 'sk-ant-test'
    providers_vision._claude_scene = _casse
    providers_vision._last_desc = ''
    try:
        assert providers_vision.describe_scene(object(), hq=True) == providers_vision._INDISPONIBLE
    finally:
        (providers_vision.ANTHROPIC_API_KEY,
         providers_vision._claude_scene,
         providers_vision._last_desc, providers_vision._last_time) = anciens


def test_vision_sans_cle_message_clair():
    """Pas de ANTHROPIC_API_KEY → message clair immédiat, sans appel Claude."""
    anciens = (providers_vision.ANTHROPIC_API_KEY,
               providers_vision._last_desc, providers_vision._last_time)
    providers_vision.ANTHROPIC_API_KEY = ''
    providers_vision._last_desc = ''
    try:
        assert providers_vision.describe_scene(object(), hq=True) == providers_vision._INDISPONIBLE
    finally:
        (providers_vision.ANTHROPIC_API_KEY,
         providers_vision._last_desc, providers_vision._last_time) = anciens


def test_ocr_fallback_tesseract():
    """OCR_PROVIDER=claude + Claude en panne → lecture Tesseract locale."""
    anciens = (providers_ocr.OCR_PROVIDER, providers_ocr.ANTHROPIC_API_KEY,
               providers_ocr._claude_ocr, providers_ocr._local_ocr)
    def _casse(image):
        raise ClaudeError('panne (test)')
    providers_ocr.OCR_PROVIDER = 'claude'
    providers_ocr.ANTHROPIC_API_KEY = 'sk-ant-test'
    providers_ocr._claude_ocr = _casse
    providers_ocr._local_ocr = lambda image: 'قراءة محلية'
    try:
        assert providers_ocr.read_text(object()) == 'قراءة محلية'
    finally:
        (providers_ocr.OCR_PROVIDER, providers_ocr.ANTHROPIC_API_KEY,
         providers_ocr._claude_ocr, providers_ocr._local_ocr) = anciens


if __name__ == '__main__':
    tests = [
        test_claude_darija_leve_claude_error,
        test_claude_scene_leve_claude_error,
        test_claude_ocr_leve_claude_error,
        test_ai_fallback_groq,
        test_vision_fallback_message_clair,
        test_vision_sans_cle_message_clair,
        test_ocr_fallback_tesseract,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f'  OK {t.__name__}')
            passed += 1
        except AssertionError as e:
            print(f'  FAIL {t.__name__}: {e}')
            failed += 1
    print(f'\n{passed} passés, {failed} échoués')
    sys.exit(1 if failed else 0)
