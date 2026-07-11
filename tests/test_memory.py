"""
Tests de la mémoire de conversation (src/core/memory.py) et du nettoyage TTS
(src/audio/text_clean.py). Fonctions pures → tournent sur Windows sans matériel.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import CONV_MEMORY_TURNS
from src.core import memory
from src.audio.text_clean import clean_for_speech, couper_phrase_incomplete


# ── Mémoire ───────────────────────────────────────────────────────────────────
def test_empty_initial():
    memory.reset()
    assert memory.get_history() == []

def test_add_turn():
    memory.reset()
    memory.add_turn('سؤال', 'جواب')
    h = memory.get_history()
    if CONV_MEMORY_TURNS <= 0:
        assert h == [], "mémoire désactivée → rien enregistré"
        return
    assert h == [
        {'role': 'user', 'content': 'سؤال'},
        {'role': 'assistant', 'content': 'جواب'},
    ]

def test_pairing_skips_incomplete():
    """Un tour sans réponse (ou sans question) n'est pas enregistré → l'historique
    reste une alternance stricte user→assistant exigée par l'API."""
    memory.reset()
    memory.add_turn('سؤال', '')   # réponse vide
    memory.add_turn('', 'جواب')   # question vide
    assert memory.get_history() == []

def test_starts_with_user_and_alternates():
    memory.reset()
    if CONV_MEMORY_TURNS <= 0:
        return
    for i in range(CONV_MEMORY_TURNS + 5):
        memory.add_turn(f'q{i}', f'a{i}')
    h = memory.get_history()
    assert len(h) == CONV_MEMORY_TURNS * 2, "tronqué aux N derniers tours"
    assert [m['role'] for m in h] == ['user', 'assistant'] * CONV_MEMORY_TURNS
    assert h[-1]['content'] == f'a{CONV_MEMORY_TURNS + 4}', "garde les plus récents"

def test_reset():
    memory.reset()
    memory.add_turn('a', 'b')
    memory.reset()
    assert memory.get_history() == []

def test_get_history_is_copy():
    memory.reset()
    memory.add_turn('a', 'b')
    h = memory.get_history()
    h.append('x')
    assert len(memory.get_history()) == 2, "get_history doit renvoyer une copie"


# ── Dernière image (suivi visuel) ─────────────────────────────────────────────
def test_last_image_absent_initial():
    memory.reset()
    assert memory.get_last_image() is None, "aucune image au départ"

def test_last_image_set_get():
    memory.reset()
    memory.set_last_image('base64-fake')
    assert memory.get_last_image() == 'base64-fake'

def test_last_image_replaced():
    """La dernière vue à la demande remplace la précédente (une seule gardée)."""
    memory.reset()
    memory.set_last_image('img1')
    memory.set_last_image('img2')
    assert memory.get_last_image() == 'img2'

def test_last_image_cleared_by_reset():
    memory.reset()
    memory.set_last_image('img')
    memory.reset()
    assert memory.get_last_image() is None, "reset doit effacer la dernière image"


# ── Nettoyage TTS ─────────────────────────────────────────────────────────────
def test_clean_none_and_empty():
    assert clean_for_speech(None) is None
    assert clean_for_speech('') == ''

def test_clean_plain_unchanged():
    assert clean_for_speech('الطريق سالكة') == 'الطريق سالكة'

def test_clean_bold():
    assert clean_for_speech('عندك! **وقف**') == 'عندك! وقف'

def test_clean_headers():
    assert clean_for_speech('## عنوان') == 'عنوان'

def test_clean_bullets_to_pauses():
    assert clean_for_speech('- واحد\n- جوج') == 'واحد، جوج'

def test_clean_paragraph_break():
    assert clean_for_speech('سطر\n\nسطر') == 'سطر. سطر'

def test_clean_no_residual_markers():
    out = clean_for_speech('**مهم** : `كود` و # و ~tilde~')
    for ch in '*`#~':
        assert ch not in out, f"marqueur '{ch}' non retiré"


# ── Coupe des phrases incomplètes (réponses plafonnées par max_tokens) ────────
def test_coupe_phrase_tronquee():
    """Phrase coupée en plein mot (vu dans les logs) → garder la partie complète."""
    assert couper_phrase_incomplete('قدامك باب كبير. خلفو جدار أ') == 'قدامك باب كبير.'

def test_coupe_phrase_complete_inchangee():
    assert couper_phrase_incomplete('الطريق سالكة.') == 'الطريق سالكة.'

def test_coupe_question_arabe_conservee():
    assert couper_phrase_incomplete('واش كاين شي حد؟') == 'واش كاين شي حد؟'

def test_coupe_sans_ponctuation_inchangee():
    """Aucun signe de fin → texte inchangé (mieux parler que se taire)."""
    assert couper_phrase_incomplete('الطريق سالكة سير نيشان') == 'الطريق سالكة سير نيشان'

def test_coupe_vide_et_none():
    assert couper_phrase_incomplete('') == ''
    assert couper_phrase_incomplete(None) is None


if __name__ == '__main__':
    tests = [
        test_empty_initial,
        test_add_turn,
        test_pairing_skips_incomplete,
        test_starts_with_user_and_alternates,
        test_reset,
        test_get_history_is_copy,
        test_last_image_absent_initial,
        test_last_image_set_get,
        test_last_image_replaced,
        test_last_image_cleared_by_reset,
        test_clean_none_and_empty,
        test_clean_plain_unchanged,
        test_clean_bold,
        test_clean_headers,
        test_clean_bullets_to_pauses,
        test_clean_paragraph_break,
        test_clean_no_residual_markers,
        test_coupe_phrase_tronquee,
        test_coupe_phrase_complete_inchangee,
        test_coupe_question_arabe_conservee,
        test_coupe_sans_ponctuation_inchangee,
        test_coupe_vide_et_none,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f'  OK {t.__name__}')
            passed += 1
        except AssertionError as e:
            print(f'  FAIL {t.__name__}: {e}')
            failed += 1
    print(f'\n{passed} passés, {failed} échoués')
