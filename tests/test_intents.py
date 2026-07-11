"""
Tests de la logique de détection d'intentions vocales.

Teste uniquement la correspondance mots-clés → intention,
sans déclencher de code matériel (Groq, caméra, micro).
Compatible Windows/Linux sans dépendances matérielles.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import des constantes de mots-clés uniquement
# (pas d'appel aux fonctions matérielles)
from src.conversation.intents import (
    KEYWORDS_VISION,
    KEYWORDS_OCR,
    KEYWORDS_HELP,
    KEYWORDS_STOP,
    KEYWORDS_WAKE,
    contient_wake,
    retirer_wake,
)


# ── Détection d'intention (miroir de la logique process_command) ──────────────
def _detecter_intention(commande: str) -> str:
    """Retourne l'intention détectée sans appeler de fonctions matérielles."""
    if any(m in commande for m in KEYWORDS_VISION):   return 'vision'
    if any(m in commande for m in KEYWORDS_OCR):      return 'ocr'
    if any(m in commande for m in KEYWORDS_HELP):     return 'help'
    if any(m in commande for m in KEYWORDS_STOP):     return 'stop'
    return 'free'


# ── Tests des mots-clés ───────────────────────────────────────────────────────

def test_keywords_vision_non_vides():
    assert len(KEYWORDS_VISION) >= 3

def test_keywords_ocr_non_vides():
    assert len(KEYWORDS_OCR) >= 2

def test_keywords_stop_non_vides():
    assert len(KEYWORDS_STOP) >= 3

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

# ── Tests d'arrêt ─────────────────────────────────────────────────────────────

def test_intention_stop_wqf():
    assert _detecter_intention('وقف') == 'stop'

def test_intention_stop_bsslama():
    assert _detecter_intention('بسلامة سلام') == 'stop'

# ── Test commande libre ───────────────────────────────────────────────────────

def test_intention_free():
    assert _detecter_intention('شكران بزاف') == 'free'

def test_intention_free_unknown():
    assert _detecter_intention('الله يعطيك الصحة') == 'free'

# ── Tests d'aide ──────────────────────────────────────────────────────────────

def test_intention_help():
    assert _detecter_intention('عاونني') == 'help'

def test_intention_msaada():
    assert _detecter_intention('مساعدة') == 'help'

# ── Tests mot de réveil ───────────────────────────────────────────────────────

def test_wake_detecte():
    assert contient_wake('مرافق شنو قدامي')

def test_wake_absent():
    assert not contient_wake('شنو قدامي')

def test_wake_retire_garde_commande():
    assert retirer_wake('مرافق شنو قدامي') == 'شنو قدامي'

def test_wake_seul_donne_vide():
    assert retirer_wake('مرافق') == ''


# ── Intention devinée par Claude (filet de sécurité STT bruitée) ──────────────
# process_command référence ses dépendances via les globals du module →
# on les remplace par des fakes, on appelle, on restaure. Aucun matériel.

def _process_avec_fakes(commande, intention):
    """Exécute process_command avec le classificateur et les actions simulés.
    Retourne la liste des actions déclenchées."""
    from src.conversation import intents
    actions = []
    anciens = (intents._intention_claude, intents.parler, intents.capturer,
               intents.describe_scene, intents.lire_texte, intents.get_ai_response)
    intents._intention_claude = lambda c: intention
    intents.parler            = lambda t: actions.append(('parler', t))
    intents.capturer          = lambda hq=False: 'fake-img'
    intents.describe_scene    = lambda img, q, hq=False: actions.append(('scene', q)) or 'وصف'
    intents.lire_texte        = lambda: actions.append(('lire', None))
    intents.get_ai_response   = lambda c: actions.append(('chat', c)) or 'جواب'
    try:
        intents.process_command(commande)
        return actions
    finally:
        (intents._intention_claude, intents.parler, intents.capturer,
         intents.describe_scene, intents.lire_texte, intents.get_ai_response) = anciens


def test_intention_devinee_scene():
    """Transcription déformée (« كثمانين ») classée SCENE → description."""
    actions = _process_avec_fakes('كثمانين', 'SCENE')
    assert ('scene', 'شنو قدامي؟') in actions, 'doit décrire avec la question par défaut'


def test_intention_devinee_lire():
    actions = _process_avec_fakes('أرليا', 'LIRE')
    assert ('lire', None) in actions, 'doit lancer la lecture OCR'


def test_intention_devinee_chat_fallback():
    """Classification CHAT (ou échec) → question libre, comportement historique."""
    actions = _process_avec_fakes('الله يعطيك الصحة', 'CHAT')
    assert any(a[0] == 'chat' for a in actions), 'doit partir en question libre'


def test_intention_devinee_jamais_arret():
    """SÉCURITÉ : même si le classificateur renvoyait n'importe quoi, l'arrêt
    ne peut PAS être deviné — process_command doit retourner True (continuer)."""
    from src.conversation import intents
    anciens = (intents._intention_claude, intents.parler, intents.capturer,
               intents.describe_scene, intents.lire_texte, intents.get_ai_response)
    intents._intention_claude = lambda c: 'ARRET'   # valeur hors contrat
    intents.parler            = lambda t: None
    intents.get_ai_response   = lambda c: 'جواب'
    try:
        assert intents.process_command('بلا بلا') is True, \
            "une intention inattendue doit retomber en CHAT, jamais arrêter"
    finally:
        (intents._intention_claude, intents.parler, intents.capturer,
         intents.describe_scene, intents.lire_texte, intents.get_ai_response) = anciens


if __name__ == '__main__':
    tests = [
        test_keywords_vision_non_vides,
        test_keywords_ocr_non_vides,
        test_keywords_stop_non_vides,
        test_intention_vision_shnou,
        test_intention_vision_wasf,
        test_intention_vision_shouf,
        test_intention_ocr_qra,
        test_intention_ocr_iqra,
        test_intention_stop_wqf,
        test_intention_stop_bsslama,
        test_intention_free,
        test_intention_free_unknown,
        test_intention_help,
        test_intention_msaada,
        test_wake_detecte,
        test_wake_absent,
        test_wake_retire_garde_commande,
        test_wake_seul_donne_vide,
        test_intention_devinee_scene,
        test_intention_devinee_lire,
        test_intention_devinee_chat_fallback,
        test_intention_devinee_jamais_arret,
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
