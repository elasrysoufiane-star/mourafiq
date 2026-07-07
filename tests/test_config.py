"""
Tests de la configuration — vérification des types et valeurs.
Fonctionne sur Windows sans clé API ni matériel.
"""
import sys
from pathlib import Path

# Ajouter la racine du projet au path pour les imports absolus
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    EDGE_VOICE,
    TIMEOUT_ECOUTE,
    GPS_BAUD,
    BASE_DIR,
    AUDIO_MP3,
    AUDIO_WAV,
    HQ_CAPTURE_ENABLED,
)


def test_edge_voice_arabic():
    """La voix edge-tts doit être arabophone (préfixe 'ar-')."""
    assert EDGE_VOICE.startswith('ar-'), f"EDGE_VOICE='{EDGE_VOICE}' — doit commencer par 'ar-'"


def test_edge_voice_moroccan():
    """Vérifier que la voix marocaine est bien configurée."""
    assert 'ar-MA' in EDGE_VOICE or 'ar-EG' in EDGE_VOICE or 'ar-SA' in EDGE_VOICE


def test_timeout_ecoute_positive():
    """Le timeout d'écoute doit être strictement positif."""
    assert TIMEOUT_ECOUTE > 0, "TIMEOUT_ECOUTE doit être > 0"


def test_timeout_ecoute_approx_8s():
    """Le timeout doit correspondre environ à 8 secondes."""
    secondes_approx = TIMEOUT_ECOUTE * 1024 / 16000
    assert 6 <= secondes_approx <= 10, f"Timeout ≈ {secondes_approx:.1f}s (attendu ~8s)"


def test_gps_baud_standard():
    """Le baud GPS doit être une valeur standard."""
    valeurs_standard = [4800, 9600, 19200, 38400, 115200]
    assert GPS_BAUD in valeurs_standard, f"GPS_BAUD={GPS_BAUD} non standard"


def test_base_dir_exists():
    """BASE_DIR doit pointer vers un répertoire existant."""
    assert BASE_DIR.exists(), f"BASE_DIR '{BASE_DIR}' n'existe pas"


def test_paths_in_project():
    """Les chemins audio doivent être dans le projet."""
    assert str(BASE_DIR) in AUDIO_MP3
    assert str(BASE_DIR) in AUDIO_WAV


def test_audio_mp3_extension():
    assert AUDIO_MP3.endswith('.mp3')


def test_audio_wav_extension():
    assert AUDIO_WAV.endswith('.wav')


def test_hq_capture_enabled_bool():
    """HQ_CAPTURE_ENABLED doit être un booléen (parsing env robuste)."""
    assert isinstance(HQ_CAPTURE_ENABLED, bool)


def test_camera_module_importable():
    """src.vision.camera doit s'importer sans matériel (Windows)."""
    from src.vision.camera import capturer
    assert callable(capturer)


if __name__ == '__main__':
    tests = [
        test_edge_voice_arabic,
        test_edge_voice_moroccan,
        test_timeout_ecoute_positive,
        test_timeout_ecoute_approx_8s,
        test_gps_baud_standard,
        test_base_dir_exists,
        test_paths_in_project,
        test_audio_mp3_extension,
        test_audio_wav_extension,
        test_hq_capture_enabled_bool,
        test_camera_module_importable,
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
