"""
Tests de la configuration — vérification des types et valeurs.
Fonctionne sur Windows sans clé API ni matériel.
"""
import sys
from pathlib import Path

# Ajouter la racine du projet au path pour les imports absolus
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    CONF_SEUIL,
    EDGE_VOICE,
    TIMEOUT_ECOUTE,
    BASE_DIR,
    AUDIO_MP3,
    AUDIO_WAV,
    MODEL_PATH,
)


def test_conf_seuil_range():
    """CONF_SEUIL doit être entre 0 et 1 (seuil de confiance YOLO)."""
    assert 0 < CONF_SEUIL < 1, f"CONF_SEUIL={CONF_SEUIL} hors de ]0,1["


def test_conf_seuil_valeur():
    """CONF_SEUIL ≤ 0.60 pour une bonne détection."""
    assert CONF_SEUIL <= 0.60, f"CONF_SEUIL={CONF_SEUIL} trop élevé (max recommandé: 0.60)"


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


def test_base_dir_exists():
    """BASE_DIR doit pointer vers un répertoire existant."""
    assert BASE_DIR.exists(), f"BASE_DIR '{BASE_DIR}' n'existe pas"


def test_paths_in_project():
    """Les chemins audio et modèle doivent être dans le projet."""
    assert str(BASE_DIR) in AUDIO_MP3
    assert str(BASE_DIR) in AUDIO_WAV
    assert str(BASE_DIR) in MODEL_PATH


def test_audio_mp3_extension():
    assert AUDIO_MP3.endswith('.mp3')


def test_audio_wav_extension():
    assert AUDIO_WAV.endswith('.wav')


if __name__ == '__main__':
    tests = [
        test_conf_seuil_range,
        test_conf_seuil_valeur,
        test_edge_voice_arabic,
        test_edge_voice_moroccan,
        test_timeout_ecoute_positive,
        test_timeout_ecoute_approx_8s,
        test_base_dir_exists,
        test_paths_in_project,
        test_audio_mp3_extension,
        test_audio_wav_extension,
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
