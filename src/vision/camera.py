"""
Capture caméra centralisée — deux qualités :

  capturer()          → frame 640×480 du flux vidéo (rapide — boucle
                        AutoScene, description auto continue)
  capturer(hq=True)   → still pleine résolution capteur via switch_mode
                        (~0.5-1s), réservé à l'OCR et à la scène à la demande :
                        lire une lettre ou une notice exige plus de pixels
                        que 640×480, quel que soit le modèle VLM.

Le still repasse ensuite par _encode_image (claude_client) qui le réduit à
CLAUDE_IMG_MAX_PX avant envoi — c'est CLAUDE_IMG_MAX_PX (.env) qui fixe le
compromis lisibilité/tokens du still. Sans effet sur la boucle continue,
dont la source reste 640px (thumbnail ne fait que réduire).

Tous les accès caméra passent par state.camera_lock, y compris le
switch_mode : la boucle vision attend simplement la fin du still.
Si la config still est absente (HQ_CAPTURE_ENABLED=0 ou échec à l'init)
ou si le switch échoue, repli silencieux sur le flux 640×480 — jamais
d'exception vers l'appelant pour un problème de qualité.
"""
from src.core import state


def capturer(hq: bool = False):
    """Retourne une image RGB (numpy array). hq=True → still haute résolution
    si disponible, sinon repli sur le flux vidéo 640×480."""
    with state.camera_lock:
        if hq and state.camera_still_cfg is not None:
            try:
                return state.camera.switch_mode_and_capture_array(
                    state.camera_still_cfg, 'main'
                )
            except Exception as e:
                print(f'Capture HQ échouée ({e}) → capture 640×480')
        return state.camera.capture_array()
