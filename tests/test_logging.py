"""
Tests du système de logs runtime (src/core/logging_setup.py).
Vérifie que le tee stdout→fichier capture bien les print(), horodate, reste
thread-safe et se restaure proprement. Fonctionne sur Windows sans matériel.
"""
import sys
import threading
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import logging_setup


def _avec_logging(fonction, **kwargs):
    """Installe le logging dans un dossier temporaire, exécute, puis restaure."""
    with tempfile.TemporaryDirectory() as tmp:
        chemin = logging_setup.setup_logging(tmp, **kwargs)
        try:
            return fonction(chemin)
        finally:
            logging_setup.teardown_logging()


def test_setup_cree_fichier():
    def verifier(chemin):
        assert chemin is not None, 'setup_logging doit retourner un chemin'
        assert chemin.exists(), 'le fichier log doit être créé'
        assert chemin.name.startswith('mourafiq_'), 'nom horodaté attendu'
        assert chemin.suffix == '.log'
    _avec_logging(verifier)


def test_capture_print_dans_fichier():
    def verifier(chemin):
        print('SALAM_TEST_123')
        contenu = chemin.read_text(encoding='utf-8')
        assert 'SALAM_TEST_123' in contenu, 'le print() doit être écrit dans le log'
    _avec_logging(verifier)


def test_horodatage_et_thread():
    def verifier(chemin):
        print('ligne_horodatee')
        contenu = chemin.read_text(encoding='utf-8')
        # Préfixe attendu : [HH:MM:SS MainThread]
        assert 'MainThread' in contenu, 'le nom du thread doit préfixer la ligne'
        assert ':' in contenu.split('ligne_horodatee')[0], 'heure attendue dans le préfixe'
    _avec_logging(verifier)


def test_console_recoit_toujours():
    """L'écran (stdout d'origine) doit continuer de recevoir la sortie."""
    def verifier(chemin):
        # Après setup, sys.stdout est un _Tee qui délègue au flux d'origine
        assert isinstance(sys.stdout, logging_setup._Tee)
    _avec_logging(verifier)


def test_teardown_restaure_stdout():
    original = sys.stdout
    _avec_logging(lambda chemin: None)
    assert sys.stdout is original, 'teardown doit restaurer stdout'


def test_desactive_si_to_file_false():
    with tempfile.TemporaryDirectory() as tmp:
        chemin = logging_setup.setup_logging(tmp, to_file=False)
        try:
            assert chemin is None, 'to_file=False → pas de fichier, pas de tee'
        finally:
            logging_setup.teardown_logging()


def test_thread_safe_lignes_completes():
    """Plusieurs threads qui écrivent en même temps → aucune ligne tronquée
    (chaque ligne écrite doit se retrouver entière dans le fichier)."""
    def verifier(chemin):
        def travailleur(n):
            for i in range(50):
                print(f'THREAD_{n}_LIGNE_{i}')
        threads = [threading.Thread(target=travailleur, args=(n,), name=f'W{n}')
                   for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        contenu = chemin.read_text(encoding='utf-8')
        for n in range(4):
            for i in range(50):
                assert f'THREAD_{n}_LIGNE_{i}' in contenu, \
                    f'ligne THREAD_{n}_LIGNE_{i} perdue ou tronquée'
    _avec_logging(verifier)


def test_nettoyage_anciens_logs():
    """LOG_KEEP_FILES limite le nombre de fichiers gardés."""
    with tempfile.TemporaryDirectory() as tmp:
        dossier = Path(tmp) / 'logs'
        dossier.mkdir()
        # Créer 5 faux logs avec des mtimes croissants
        import os
        import time
        for i in range(5):
            f = dossier / f'mourafiq_2026010{i}_000000.log'
            f.write_text('x', encoding='utf-8')
            os.utime(f, (time.time() + i, time.time() + i))
        logging_setup._nettoyer_anciens_logs(dossier, garder=2)
        restants = list(dossier.glob('mourafiq_*.log'))
        assert len(restants) == 2, f'doit garder 2 fichiers, trouvé {len(restants)}'


if __name__ == '__main__':
    tests = [
        test_setup_cree_fichier,
        test_capture_print_dans_fichier,
        test_horodatage_et_thread,
        test_console_recoit_toujours,
        test_teardown_restaure_stdout,
        test_desactive_si_to_file_false,
        test_thread_safe_lignes_completes,
        test_nettoyage_anciens_logs,
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
