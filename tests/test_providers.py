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
    AI_PROVIDER, STT_PROVIDER, TTS_PROVIDER, OCR_PROVIDER,
    ELEVENLABS_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
)

_VALID_AI     = {'groq', 'openai', 'claude', 'ollama'}
_VALID_STT    = {'groq', 'openai'}
_VALID_TTS    = {'azure', 'edge', 'gtts', 'elevenlabs'}
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

def test_ocr_provider_type():
    assert isinstance(OCR_PROVIDER, str)

def test_ocr_provider_valid():
    assert OCR_PROVIDER in _VALID_OCR, f"OCR_PROVIDER='{OCR_PROVIDER}' invalide (options: {_VALID_OCR})"

def test_default_quality_mode():
    """Défauts = MEILLEURE QUALITÉ (2026-07-08) : le .env ne contient que les
    clés API, la config vit dans settings.py. Sans clé, chaque provider retombe
    en gratuit (testé dans test_fallbacks.py). Si ce test échoue, vérifier que
    le .env local ne surcharge plus ces variables (il doit être clés-uniquement)."""
    import os
    import config.settings as settings
    variables = ('AI_PROVIDER', 'STT_PROVIDER', 'TTS_PROVIDER', 'OCR_PROVIDER',
                 'STT_MODEL', 'CLAUDE_TEXT_MODEL', 'CLAUDE_VISION_MODEL',
                 'CLAUDE_VISION_MODEL_HQ', 'CLAUDE_OCR_MODEL', 'AUTO_DESCRIBE_INTERVAL',
                 'CLAUDE_IMG_MAX_PX', 'CLAUDE_IMG_QUALITY', 'CLAUDE_MAX_TOKENS',
                 'CLAUDE_SCENE_AUTO_MAX_TOKENS', 'CONV_MEMORY_TURNS', 'AZURE_SPEECH_REGION')
    sauvegarde = {v: os.environ.pop(v) for v in variables if v in os.environ}
    try:
        importlib.reload(settings)
        assert settings.AI_PROVIDER  == 'claude', "AI_PROVIDER par défaut doit être 'claude'"
        assert settings.STT_PROVIDER == 'groq',   "STT_PROVIDER par défaut doit être 'groq'"
        assert settings.TTS_PROVIDER == 'azure',  "TTS_PROVIDER par défaut doit être 'azure'"
        assert settings.OCR_PROVIDER == 'claude', "OCR_PROVIDER par défaut doit être 'claude'"
        assert settings.STT_MODEL    == 'whisper-large-v3', "STT_MODEL par défaut doit être 'whisper-large-v3'"
        assert settings.CLAUDE_TEXT_MODEL      == 'claude-opus-4-8', "conversation en Opus (qualité max)"
        assert settings.CLAUDE_VISION_MODEL    == 'claude-sonnet-5', "boucle continue en Sonnet 5 (Opus trop lent)"
        assert settings.CLAUDE_VISION_MODEL_HQ == 'claude-opus-4-8', "scène à la demande en Opus"
        assert settings.CLAUDE_OCR_MODEL       == 'claude-opus-4-8', "OCR à la demande en Opus"
        assert settings.AUTO_DESCRIBE_INTERVAL == 0, "mode à la demande (démo)"
        assert settings.CLAUDE_MAX_TOKENS      == 300, "réponses à la demande riches"
        assert settings.CLAUDE_SCENE_AUTO_MAX_TOKENS == 80, "narration de fond courte"
        assert settings.CLAUDE_IMG_MAX_PX      == 1568
        assert settings.CLAUDE_IMG_QUALITY     == 90
        assert settings.CONV_MEMORY_TURNS      == 15
        assert settings.AZURE_SPEECH_REGION    == 'westeurope'
    finally:
        os.environ.update(sauvegarde)
        importlib.reload(settings)

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
        test_ocr_provider_type,
        test_ocr_provider_valid,
        test_default_quality_mode,
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
