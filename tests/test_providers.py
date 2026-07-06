"""
Tests des providers configurables.
Vérifie la lecture des variables depuis config/settings.py et l'importabilité
des modules providers. Fonctionne sur Windows sans matériel ni clé API.
"""
import sys
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    DEMO_MODE,
    AI_PROVIDER, STT_PROVIDER, TTS_PROVIDER, VISION_AI_PROVIDER, OCR_PROVIDER,
    ELEVENLABS_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
)

_VALID_AI     = {'groq', 'openai', 'claude', 'ollama'}
_VALID_STT    = {'groq', 'openai'}
_VALID_TTS    = {'edge', 'gtts', 'elevenlabs'}
_VALID_VISION = {'local', 'claude'}
_VALID_OCR    = {'local', 'claude'}


def test_demo_mode_type():
    assert isinstance(DEMO_MODE, str), "DEMO_MODE doit être une str"

def test_demo_mode_values():
    assert DEMO_MODE in {'free', 'demo'}, f"DEMO_MODE='{DEMO_MODE}' invalide (attendu: free | demo)"

def test_ai_provider_type():
    assert isinstance(AI_PROVIDER, str)

def test_ai_provider_valid():
    assert AI_PROVIDER in _VALID_AI, f"AI_PROVIDER='{AI_PROVIDER}' invalide (options: {_VALID_AI})"

def test_stt_provider_type():
    assert isinstance(STT_PROVIDER, str)

def test_stt_provider_valid():
    assert STT_PROVIDER in _VALID_STT, f"STT_PROVIDER='{STT_PROVIDER}' invalide (options: {_VALID_STT})"

def test_tts_provider_type():
    assert isinstance(TTS_PROVIDER, str)

def test_tts_provider_valid():
    assert TTS_PROVIDER in _VALID_TTS, f"TTS_PROVIDER='{TTS_PROVIDER}' invalide (options: {_VALID_TTS})"

def test_vision_provider_type():
    assert isinstance(VISION_AI_PROVIDER, str)

def test_vision_provider_valid():
    assert VISION_AI_PROVIDER in _VALID_VISION, f"VISION_AI_PROVIDER='{VISION_AI_PROVIDER}' invalide (options: {_VALID_VISION})"

def test_ocr_provider_type():
    assert isinstance(OCR_PROVIDER, str)

def test_ocr_provider_valid():
    assert OCR_PROVIDER in _VALID_OCR, f"OCR_PROVIDER='{OCR_PROVIDER}' invalide (options: {_VALID_OCR})"

def test_default_free_mode():
    """Sans clé payante, les providers par défaut doivent être les gratuits."""
    if not ELEVENLABS_API_KEY and not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
        assert AI_PROVIDER        == 'groq',  "AI_PROVIDER par défaut doit être 'groq'"
        assert STT_PROVIDER       == 'groq',  "STT_PROVIDER par défaut doit être 'groq'"
        assert TTS_PROVIDER       == 'edge',  "TTS_PROVIDER par défaut doit être 'edge'"
        assert VISION_AI_PROVIDER == 'local', "VISION_AI_PROVIDER par défaut doit être 'local'"
        assert OCR_PROVIDER       == 'local', "OCR_PROVIDER par défaut doit être 'local'"

def test_elevenlabs_key_is_string():
    assert isinstance(ELEVENLABS_API_KEY, str)

def test_openai_key_is_string():
    assert isinstance(OPENAI_API_KEY, str)

def test_anthropic_key_is_string():
    assert isinstance(ANTHROPIC_API_KEY, str)

def test_provider_ai_importable():
    m = importlib.import_module('src.providers.ai')
    assert hasattr(m, 'get_ai_response'), "get_ai_response manquant dans providers.ai"

def test_provider_stt_importable():
    m = importlib.import_module('src.providers.stt')
    assert hasattr(m, 'transcribe'), "transcribe manquant dans providers.stt"

def test_provider_tts_importable():
    m = importlib.import_module('src.providers.tts')
    assert hasattr(m, 'synthesize'), "synthesize manquant dans providers.tts"

def test_provider_vision_ai_importable():
    m = importlib.import_module('src.providers.vision_ai')
    assert hasattr(m, 'describe_scene'), "describe_scene manquant dans providers.vision_ai"

def test_provider_ocr_importable():
    m = importlib.import_module('src.providers.ocr')
    assert hasattr(m, 'read_text'), "read_text manquant dans providers.ocr"

def test_claude_client_importable():
    """Import lazy du SDK anthropic — le module doit s'importer sans la lib/clé."""
    m = importlib.import_module('src.ai.claude_client')
    assert hasattr(m, 'claude_darija'), "claude_darija manquant dans ai.claude_client"
    assert hasattr(m, 'claude_describe_scene'), "claude_describe_scene manquant"
    assert hasattr(m, 'claude_read_text'), "claude_read_text manquant dans ai.claude_client"


if __name__ == '__main__':
    tests = [
        test_demo_mode_type,
        test_demo_mode_values,
        test_ai_provider_type,
        test_ai_provider_valid,
        test_stt_provider_type,
        test_stt_provider_valid,
        test_tts_provider_type,
        test_tts_provider_valid,
        test_vision_provider_type,
        test_vision_provider_valid,
        test_ocr_provider_type,
        test_ocr_provider_valid,
        test_default_free_mode,
        test_elevenlabs_key_is_string,
        test_openai_key_is_string,
        test_anthropic_key_is_string,
        test_provider_ai_importable,
        test_provider_stt_importable,
        test_provider_tts_importable,
        test_provider_vision_ai_importable,
        test_provider_ocr_importable,
        test_claude_client_importable,
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
