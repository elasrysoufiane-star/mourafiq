"""
Tests du dictionnaire de traductions YOLO → Darija.
Vérifie la complétude, le format et la cohérence des traductions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision.translations import traductions

# Classes YOLO critiques pour la sécurité d'un malvoyant
CLASSES_DANGEREUSES = ['car', 'truck', 'bus', 'motorcycle', 'train', 'dog']
MOT_AVERTISSEMENT   = 'انتبه'

# Classes minimales attendues
CLASSES_REQUISES = [
    'person', 'car', 'chair', 'cell phone',
    'traffic light', 'stop sign', 'dog',
]


def test_dictionnaire_non_vide():
    """Le dictionnaire ne doit pas être vide."""
    assert len(traductions) > 0, "Le dictionnaire traductions est vide"


def test_taille_minimale():
    """Au moins 30 classes traduites."""
    assert len(traductions) >= 30, f"Seulement {len(traductions)} classes (min 30)"


def test_cles_sont_strings():
    """Toutes les clés sont des chaînes."""
    for k in traductions:
        assert isinstance(k, str), f"Clé non-str: {k!r}"


def test_valeurs_sont_strings_non_vides():
    """Toutes les valeurs sont des chaînes non vides."""
    for k, v in traductions.items():
        assert isinstance(v, str), f"Valeur non-str pour '{k}': {v!r}"
        assert len(v.strip()) > 0, f"Traduction vide pour '{k}'"


def test_classes_requises_presentes():
    """Les classes critiques doivent être présentes."""
    for cls in CLASSES_REQUISES:
        assert cls in traductions, f"Classe requise manquante: '{cls}'"


def test_objets_dangereux_ont_avertissement():
    """Les véhicules et animaux dangereux doivent contenir 'انتبه'."""
    for cls in CLASSES_DANGEREUSES:
        if cls in traductions:
            assert MOT_AVERTISSEMENT in traductions[cls], (
                f"'{cls}' devrait contenir '{MOT_AVERTISSEMENT}' "
                f"(actuel: '{traductions[cls]}')"
            )


def test_pas_de_traduction_en_latin():
    """Les traductions ne doivent pas être en latin (doivent être en arabe)."""
    ascii_letters = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    for k, v in traductions.items():
        ratio_latin = sum(1 for c in v if c in ascii_letters) / max(len(v), 1)
        assert ratio_latin < 0.5, f"Traduction de '{k}' semble en latin: '{v}'"


def test_person_traduit():
    assert 'person' in traductions
    assert len(traductions['person']) > 0


def test_cell_phone_traduit():
    assert 'cell phone' in traductions


if __name__ == '__main__':
    tests = [
        test_dictionnaire_non_vide,
        test_taille_minimale,
        test_cles_sont_strings,
        test_valeurs_sont_strings_non_vides,
        test_classes_requises_presentes,
        test_objets_dangereux_ont_avertissement,
        test_pas_de_traduction_en_latin,
        test_person_traduit,
        test_cell_phone_traduit,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f'  ✓ {t.__name__}')
            passed += 1
        except AssertionError as e:
            print(f'  ✗ {t.__name__}: {e}')
            failed += 1
    print(f'\n{passed} passés, {failed} échoués')
