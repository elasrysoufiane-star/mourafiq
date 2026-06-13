"""
Tests de la logique de détection d'intentions vocales.

Teste uniquement la correspondance mots-clés → intention,
sans déclencher de code matériel (Groq, caméra, micro, GPS).
Compatible Windows/Linux sans dépendances matérielles.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import des constantes de mots-clés uniquement
# (pas d'appel aux fonctions matérielles)
from src.conversation.intents import (
    KEYWORDS_GPS,
    KEYWORDS_VISION,
    KEYWORDS_OCR,
    KEYWORDS_HELP,
    KEYWORDS_STOP,
    KEYWORDS_NAVIGATE,
)


# ── Détection d'intention (miroir de la logique process_command) ──────────────
def _detecter_intention(commande: str) -> str:
    """Retourne l'intention détectée sans appeler de fonctions matérielles."""
    if any(m in commande for m in KEYWORDS_GPS):      return 'gps'
    if any(m in commande for m in KEYWORDS_VISION):   return 'vision'
    if any(m in commande for m in KEYWORDS_OCR):      return 'ocr'
    if 'صيدلية' in commande:                          return 'pharmacy'
    if any(m in commande for m in ['سبيطار', 'مستشفى']): return 'hospital'
    if 'جامع' in commande:                            return 'mosque'
    if 'محطة' in commande:                            return 'station'
    if any(m in commande for m in KEYWORDS_NAVIGATE): return 'navigate'
    if any(m in commande for m in KEYWORDS_HELP):     return 'help'
    if any(m in commande for m in KEYWORDS_STOP):     return 'stop'
    return 'free'


# ── Tests des mots-clés ───────────────────────────────────────────────────────

def test_keywords_gps_non_vides():
    assert len(KEYWORDS_GPS) >= 3, "Doit avoir au moins 3 mots-clés GPS"

def test_keywords_vision_non_vides():
    assert len(KEYWORDS_VISION) >= 3

def test_keywords_ocr_non_vides():
    assert len(KEYWORDS_OCR) >= 2

def test_keywords_stop_non_vides():
    assert len(KEYWORDS_STOP) >= 3

def test_keywords_navigate_non_vides():
    assert len(KEYWORDS_NAVIGATE) >= 2

# ── Tests d'intention GPS ─────────────────────────────────────────────────────

def test_intention_gps_wain():
    assert _detecter_intention('وين أنا') == 'gps'

def test_intention_gps_fain():
    assert _detecter_intention('فاين كنت') == 'gps'

def test_intention_gps_ayn():
    assert _detecter_intention('أين أنا الآن') == 'gps'

def test_intention_gps_mawqi3():
    assert _detecter_intention('موقعي فاين') == 'gps'

# ── Tests d'intention Vision ──────────────────────────────────────────────────

def test_intention_vision_shnou():
    assert _detecter_intention('شنو قدامي') == 'vision'

def test_intention_vision_wasf():
    assert _detecter_intention('وصف ليا ما شايفو') == 'vision'

def test_intention_vision_shouf():
    assert _detecter_intention('شوف واش كاين') == 'vision'

# ── Tests d'intention OCR ─────────────────────────────────────────────────────

def test_intention_ocr_qra():
    assert _detecter_intention('قرا ليا') == 'ocr'

def test_intention_ocr_iqra():
    assert _detecter_intention('اقرأ ليا') == 'ocr'

# ── Tests de navigation ───────────────────────────────────────────────────────

def test_intention_pharmacie():
    assert _detecter_intention('ودي للصيدلية') == 'pharmacy'

def test_intention_hopital():
    assert _detecter_intention('ودي للسبيطار') == 'hospital'

def test_intention_mosque():
    assert _detecter_intention('روح للجامع') == 'mosque'

def test_intention_gare():
    assert _detecter_intention('ودي للمحطة') == 'station'

def test_intention_navigate_generic():
    assert _detecter_intention('مشي للدار') == 'navigate'

# ── Tests d'arrêt ─────────────────────────────────────────────────────────────

def test_intention_stop_wqf():
    assert _detecter_intention('وقف') == 'stop'

def test_intention_stop_bsslama():
    assert _detecter_intention('بسلامة سلام') == 'stop'

# ── Test commande libre ───────────────────────────────────────────────────────

def test_intention_free():
    assert _detecter_intention('شكران بزاف') == 'free'

def test_intention_free_unknown():
    assert _detecter_intention('الجو زوين اليوم') == 'free'

# ── Tests d'aide ──────────────────────────────────────────────────────────────

def test_intention_help():
    assert _detecter_intention('عاونني') == 'help'

def test_intention_msaada():
    assert _detecter_intention('مساعدة') == 'help'


if __name__ == '__main__':
    tests = [
        test_keywords_gps_non_vides,
        test_keywords_vision_non_vides,
        test_keywords_ocr_non_vides,
        test_keywords_stop_non_vides,
        test_keywords_navigate_non_vides,
        test_intention_gps_wain,
        test_intention_gps_fain,
        test_intention_gps_ayn,
        test_intention_gps_mawqi3,
        test_intention_vision_shnou,
        test_intention_vision_wasf,
        test_intention_vision_shouf,
        test_intention_ocr_qra,
        test_intention_ocr_iqra,
        test_intention_pharmacie,
        test_intention_hopital,
        test_intention_mosque,
        test_intention_gare,
        test_intention_navigate_generic,
        test_intention_stop_wqf,
        test_intention_stop_bsslama,
        test_intention_free,
        test_intention_free_unknown,
        test_intention_help,
        test_intention_msaada,
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
