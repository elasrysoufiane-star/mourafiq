"""
Tests de la détection vocale (src/audio/listener.py) — logique pure, sans
micro ni matériel. Fonctionne sur Windows, avec ou sans webrtcvad installé :
  - découpe des chunks PCM en trames 20 ms pour webrtcvad
  - fallback seuil de volume quand webrtcvad est absent
  - plancher de volume anti bruit-de-confort quand webrtcvad est actif
  - résolution de l'index micro (MIC_DEVICE_INDEX, -1 = défaut système)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio import listener
from src.core import state


def _avec(webrtc_ok, fonction):
    """Exécute `fonction` avec _WEBRTC_OK forcé, puis restaure."""
    ancien = listener._WEBRTC_OK
    listener._WEBRTC_OK = webrtc_ok
    try:
        return fonction()
    finally:
        listener._WEBRTC_OK = ancien


def test_frames_20ms_decoupe():
    """2048 octets (chunk 1024 samples) → 3 trames complètes de 640 octets."""
    frames = listener._frames_20ms(b'\x00' * 2048)
    assert len(frames) == 3
    assert all(len(f) == listener._FRAME_20MS_OCTETS for f in frames)


def test_frames_20ms_trop_court():
    """Moins d'une trame complète → liste vide (pas d'exception webrtcvad)."""
    assert listener._frames_20ms(b'\x00' * 100) == []
    assert listener._frames_20ms(b'') == []


def test_est_voix_fallback_seuil():
    """Sans webrtcvad → comportement historique : volume vs VOL_SEUIL."""
    ancien_seuil = state.VOL_SEUIL
    state.VOL_SEUIL = 200
    try:
        assert _avec(False, lambda: listener._est_voix(b'\x00' * 2048, 300)) is True
        assert _avec(False, lambda: listener._est_voix(b'\x00' * 2048, 100)) is False
    finally:
        state.VOL_SEUIL = ancien_seuil


def test_est_voix_plancher_webrtc():
    """webrtcvad actif : volume sous le plancher → jamais de la voix
    (bloque le bruit de confort HFP sans même consulter le VAD)."""
    volume_bas = listener._VAD_VOL_PLANCHER  # <= plancher
    assert _avec(True, lambda: listener._est_voix(b'\x00' * 2048, volume_bas)) is False


def test_est_voix_chunk_court_webrtc():
    """webrtcvad actif mais chunk sans trame complète → fallback seuil."""
    ancien_seuil = state.VOL_SEUIL
    state.VOL_SEUIL = 200
    try:
        assert _avec(True, lambda: listener._est_voix(b'\x00' * 100, 300)) is True
        assert _avec(True, lambda: listener._est_voix(b'\x00' * 100, 180)) is False
    finally:
        state.VOL_SEUIL = ancien_seuil


def test_est_voix_silence_webrtc():
    """webrtcvad réellement installé : du silence pur n'est pas de la voix.
    (Sauté silencieusement si la lib n'est pas installée — ex. Windows.)"""
    if not listener._WEBRTC_OK:
        return
    assert listener._est_voix(b'\x00' * 2048, 500) is False


def test_device_index_defaut_systeme():
    """MIC_DEVICE_INDEX=-1 → None (PyAudio choisit le micro par défaut)."""
    ancien = listener.MIC_DEVICE_INDEX
    listener.MIC_DEVICE_INDEX = -1
    try:
        assert listener._device_index() is None
    finally:
        listener.MIC_DEVICE_INDEX = ancien


def test_device_index_explicite():
    ancien = listener.MIC_DEVICE_INDEX
    listener.MIC_DEVICE_INDEX = 2
    try:
        assert listener._device_index() == 2
    finally:
        listener.MIC_DEVICE_INDEX = ancien


def test_mic_device_index_config():
    from config.settings import MIC_DEVICE_INDEX
    assert isinstance(MIC_DEVICE_INDEX, int)


def test_frames_20ms_48k():
    """À 48 kHz (adaptateur USB) : trame 20 ms = 1920 octets → 1 trame par
    chunk de 2048 octets."""
    frames = listener._frames_20ms(b'\x00' * 2048, rate=48000)
    assert len(frames) == 1
    assert len(frames[0]) == listener._frame_octets(48000) == 1920


def test_est_voix_taux_non_supporte_fallback_seuil():
    """44.1 kHz (adaptateur jack→USB courant) : webrtcvad ne supporte pas ce
    taux → fallback seuil de volume, jamais d'exception."""
    ancien_seuil = state.VOL_SEUIL
    state.VOL_SEUIL = 200
    try:
        assert _avec(True, lambda: listener._est_voix(b'\x00' * 2048, 300, rate=44100)) is True
        assert _avec(True, lambda: listener._est_voix(b'\x00' * 2048, 100, rate=44100)) is False
    finally:
        state.VOL_SEUIL = ancien_seuil


# ── Anti-gel : flux qui s'ouvre mais ne délivre rien ──────────────────────────
class _FauxFlux:
    """Simule un flux PyAudio : `dispo` = nb de samples disponibles à la lecture."""
    def __init__(self, dispo):
        self._dispo = dispo
    def get_read_available(self):
        return self._dispo
    def read(self, n, exception_on_overflow=False):
        return b'\x00' * (n * 2)


def test_flux_actif_avec_donnees():
    assert listener._flux_actif(_FauxFlux(dispo=1024), attente_s=0.2) is True


def test_flux_actif_muet():
    """Flux ouvert mais qui ne délivre JAMAIS de trame (périphérique décroché
    par PipeWire/Bluetooth) → détecté muet au lieu de geler au premier read()."""
    assert listener._flux_actif(_FauxFlux(dispo=0), attente_s=0.2) is False


def test_lire_chunk_ok():
    data = listener._lire_chunk(_FauxFlux(dispo=2048), timeout_s=0.2)
    assert data is not None and len(data) == 2048


def test_lire_chunk_muet_retourne_none():
    """Flux qui se tait en cours de route → None (l'appelant ferme et réessaie)
    au lieu d'un stream.read() bloqué pour toujours."""
    assert listener._lire_chunk(_FauxFlux(dispo=0), timeout_s=0.2) is None


# ── Annonce vocale des pannes micro (utilisateur non-voyant) ──────────────────
def test_annonce_panne_micro_une_fois_puis_retour():
    """3 échecs consécutifs → UNE annonce vocale de panne (pas de spam) ;
    une écoute réussie ensuite → annonce du retour + compteurs remis à zéro."""
    annonces = []
    anciens = (listener._parler_securise, listener._echecs_micro,
               listener._panne_annoncee)
    listener._parler_securise = lambda texte: annonces.append(texte)
    listener._echecs_micro = 0
    listener._panne_annoncee = False
    try:
        listener._signaler_echec_micro()
        listener._signaler_echec_micro()
        assert annonces == [], 'pas d\'annonce avant le 3e échec'
        listener._signaler_echec_micro()
        assert annonces == [listener._MSG_PANNE_MICRO], 'annonce au 3e échec'
        listener._signaler_echec_micro()
        assert len(annonces) == 1, 'une seule annonce par panne (anti-spam)'
        listener._signaler_micro_ok()
        assert annonces[-1] == listener._MSG_MICRO_RETOUR, 'annonce du retour'
        assert listener._panne_annoncee is False
        assert listener._echecs_micro == 0
    finally:
        (listener._parler_securise, listener._echecs_micro,
         listener._panne_annoncee) = anciens


def test_user_speaking_event_existe():
    """state.user_speaking (priorité voix utilisateur sur la narration) doit
    être un Event, initialement non levé."""
    import threading
    assert isinstance(state.user_speaking, threading.Event)
    assert not state.user_speaking.is_set(), 'non levé au repos'


def test_micro_ok_sans_panne_silencieux():
    """Écoute réussie SANS panne préalable → aucune annonce (pas de bavardage)."""
    annonces = []
    anciens = (listener._parler_securise, listener._echecs_micro,
               listener._panne_annoncee)
    listener._parler_securise = lambda texte: annonces.append(texte)
    listener._echecs_micro = 1   # un raté isolé, jamais annoncé
    listener._panne_annoncee = False
    try:
        listener._signaler_micro_ok()
        assert annonces == [], 'pas d\'annonce de retour sans panne annoncée'
        assert listener._echecs_micro == 0, 'compteur remis à zéro'
    finally:
        (listener._parler_securise, listener._echecs_micro,
         listener._panne_annoncee) = anciens


if __name__ == '__main__':
    tests = [
        test_frames_20ms_decoupe,
        test_frames_20ms_trop_court,
        test_est_voix_fallback_seuil,
        test_est_voix_plancher_webrtc,
        test_est_voix_chunk_court_webrtc,
        test_est_voix_silence_webrtc,
        test_device_index_defaut_systeme,
        test_device_index_explicite,
        test_mic_device_index_config,
        test_frames_20ms_48k,
        test_est_voix_taux_non_supporte_fallback_seuil,
        test_flux_actif_avec_donnees,
        test_flux_actif_muet,
        test_lire_chunk_ok,
        test_lire_chunk_muet_retourne_none,
        test_annonce_panne_micro_une_fois_puis_retour,
        test_user_speaking_event_existe,
        test_micro_ok_sans_panne_silencieux,
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
