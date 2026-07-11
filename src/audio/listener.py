"""
Écoute micro — VAD, calibration et transcription Groq Whisper.

Contient aussi les utilitaires liés au micro :
  - suprimer_alsa() : supprime le spam ALSA/JACK au démarrage
  - calibrer_micro() : mesure le bruit ambiant et calcule VOL_SEUIL

Détection de parole : webrtcvad si installé (vrai détecteur voix/bruit),
sinon fallback seuil de volume (comportement historique). Jamais d'exception
si la lib manque.

Ouverture micro ROBUSTE (2026-07-11, micro USB via adaptateur jack→USB) :
  - essaie l'index configuré (MIC_DEVICE_INDEX) puis le micro PAR DÉFAUT du
    système — les index PyAudio changent dès que le matériel audio change
    (Bluetooth, USB) → ne jamais crasher sur un index périmé ;
  - essaie 16 kHz puis le taux NATIF du périphérique — les adaptateurs
    jack→USB ne supportent souvent que 44.1/48 kHz (OSError -9997 Invalid
    sample rate sinon). Toute la chaîne (purge, VAD, timeout, WAV) s'adapte
    au taux réellement obtenu ; Whisper accepte n'importe quel taux.

Timeout automatique après 8s sans voix pour éviter tout blocage infini.
"""
import os
import contextlib
import wave
import time

import numpy as np

try:
    import pyaudio
    _PYAUDIO_OK = True
except ImportError:
    _PYAUDIO_OK = False

try:
    import webrtcvad
    # Mode 2 : agressivité moyenne-haute — bon compromis sur micro bruité
    # (0 = permissif, 3 = très strict, risque de couper la parole douce).
    _vad = webrtcvad.Vad(2)
    _WEBRTC_OK = True
except ImportError:
    _vad = None
    _WEBRTC_OK = False

from config.settings import AUDIO_WAV, TIMEOUT_ECOUTE, MIC_DEVICE_INDEX
from src.core import state

# Taux d'échantillonnage visé (celui de Whisper et de webrtcvad).
_RATE_CIBLE = 16000
# Taux acceptés par webrtcvad — en dehors (ex. 44100), fallback seuil de volume.
_VAD_RATES = (8000, 16000, 32000, 48000)

# webrtcvad exige des trames de 10/20/30 ms en PCM 16-bit mono.
# À 16 kHz : 20 ms = 320 samples = 640 octets.
_FRAME_20MS_OCTETS = int(_RATE_CIBLE * 0.02) * 2
# Plancher de volume quand webrtcvad est actif : évite les déclenchements sur
# le bruit de confort / souffle que le VAD peut classer « voix ».
_VAD_VOL_PLANCHER = 150

_vad_logge = False  # log unique du moteur VAD actif au premier appel


def _frame_octets(rate: int) -> int:
    """Taille (octets) d'une trame webrtcvad de 20 ms au taux donné."""
    return int(rate * 0.02) * 2


def _frames_20ms(data: bytes, rate: int = _RATE_CIBLE) -> list:
    """Découpe un chunk PCM en trames de 20 ms complètes pour webrtcvad."""
    octets = _frame_octets(rate)
    n = len(data) // octets
    return [data[i * octets:(i + 1) * octets] for i in range(n)]


def _est_voix(data: bytes, volume: float, rate: int = _RATE_CIBLE) -> bool:
    """Le chunk contient-il de la parole ?
    webrtcvad (majorité des trames voisées + plancher de volume) si installé ET
    taux supporté (8/16/32/48 kHz), sinon seuil de volume calibré."""
    if _WEBRTC_OK and rate in _VAD_RATES:
        if volume <= _VAD_VOL_PLANCHER:
            return False
        frames = _frames_20ms(data, rate)
        if not frames:
            return volume > state.VOL_SEUIL
        voisees = sum(1 for f in frames if _vad.is_speech(f, rate))
        return voisees * 2 > len(frames)
    return volume > state.VOL_SEUIL


def _device_index():
    """Index micro pour PyAudio. MIC_DEVICE_INDEX=-1 → défaut système (None)."""
    return None if MIC_DEVICE_INDEX < 0 else MIC_DEVICE_INDEX


def _taux_natif(p, device):
    """Taux d'échantillonnage par défaut du périphérique (ou None)."""
    try:
        info = (p.get_default_input_device_info() if device is None
                else p.get_device_info_by_index(device))
        return int(info.get('defaultSampleRate', 0)) or None
    except Exception:
        return None


def _flux_actif(stream, attente_s: float = 1.2) -> bool:
    """True si le flux délivre RÉELLEMENT des données. Certains flux s'ouvrent
    sans erreur mais ne produisent jamais une trame (périphérique décroché par
    une reconfiguration PipeWire — ex. connexion Bluetooth — ou taux non
    supporté par le matériel) : stream.read() y bloquerait pour toujours.
    Poll non-bloquant via get_read_available()."""
    deadline = time.monotonic() + attente_s
    while time.monotonic() < deadline:
        try:
            if stream.get_read_available() >= 1:
                return True
        except Exception:
            return False
        time.sleep(0.05)
    return False


def _lire_chunk(stream, timeout_s: float = 3.0):
    """Lit 1024 samples SANS blocage infini : attend (non-bloquant) que les
    données soient disponibles ; si le flux se tait > timeout_s (périphérique
    décroché en cours de route), retourne None au lieu de geler le thread."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if stream.get_read_available() >= 1024:
                return stream.read(1024, exception_on_overflow=False)
        except Exception:
            return None
        time.sleep(0.01)
    return None


def _fermer(stream, p) -> None:
    """Ferme flux + PyAudio sans jamais lever (flux possiblement déjà mort)."""
    try:
        stream.stop_stream()
        stream.close()
    except Exception:
        pass
    try:
        p.terminate()
    except Exception:
        pass


def _ouvrir_micro(p):
    """Ouvre le flux micro de façon ROBUSTE. Essaie dans l'ordre :
    (index configuré puis micro par défaut) × (16 kHz puis taux natif),
    et VÉRIFIE que des données arrivent vraiment (_flux_actif) — une ouverture
    « réussie » sans données serait un gel garanti au premier read().
    Retourne (stream, rate). RuntimeError si aucun micro utilisable —
    l'appelant gère (pas de crash, règle projet)."""
    idx = _device_index()
    devices = [idx] if idx is None else [idx, None]
    derniere_err = None
    for device in devices:
        rates = [_RATE_CIBLE]
        natif = _taux_natif(p, device)
        if natif and natif not in rates:
            rates.append(natif)
        for rate in rates:
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1,
                                rate=rate, input=True, frames_per_buffer=1024,
                                input_device_index=device)
            except Exception as e:
                derniere_err = e
                continue
            if not _flux_actif(stream):
                # Ouvert mais muet → read() bloquerait à l'infini. Suivant.
                try:
                    stream.close()
                except Exception:
                    pass
                derniere_err = RuntimeError(f'flux muet @ {rate} Hz')
                continue
            if device != idx or rate != _RATE_CIBLE:
                nom = 'défaut système' if device is None else f'index {device}'
                print(f'Micro ouvert: {nom} @ {rate} Hz')
            return stream, rate
    raise RuntimeError(f'aucun micro utilisable ({derniere_err})')


# ── Utilitaires micro ─────────────────────────────────────────────────────────

@contextlib.contextmanager
def suprimer_alsa():
    """Redirige stderr vers /dev/null pour supprimer le spam ALSA/JACK."""
    devnull    = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)


def calibrer_micro() -> int:
    """
    Écoute le bruit ambiant pendant 2 secondes et calcule le seuil de détection vocale.
    Retourne le seuil calculé (minimum 150). Jamais d'exception : micro
    inutilisable → seuil par défaut 200 (l'app démarre quand même).
    """
    if not _PYAUDIO_OK:
        print('PyAudio absent — seuil par défaut: 200')
        return 200

    with suprimer_alsa():
        p = pyaudio.PyAudio()
    try:
        stream, rate = _ouvrir_micro(p)
    except RuntimeError as e:
        print(f'Calibration impossible ({e}) — seuil par défaut: 200')
        p.terminate()
        return 200

    volumes = []
    for _ in range(max(1, int(2 * rate / 1024))):  # ~2 secondes au taux réel
        data = _lire_chunk(stream)
        if data is None:
            print('Micro muet pendant la calibration — seuil par défaut: 200')
            _fermer(stream, p)
            return 200
        vol = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
        volumes.append(vol)
    _fermer(stream, p)

    bruit = float(np.mean(volumes))
    seuil = max(150, int(bruit * 3))
    print(f'Bruit ambiant: {bruit:.0f} → Seuil voix: {seuil}')
    return seuil


# ── Reconnaissance vocale ─────────────────────────────────────────────────────

def reconnaitre_voix() -> str:
    """
    Écoute le micro jusqu'à détection d'une phrase, puis transcrit avec Whisper.
    Retourne la transcription (str) ou '' si timeout / erreur.
    Timeout : 8s sans voix → retour automatique.
    """
    if not _PYAUDIO_OK:
        print('PyAudio absent — écoute désactivée')
        time.sleep(5)
        return ''

    global _vad_logge

    print('En attente de voix...')

    # Anti-écho : ne pas écouter pendant que l'assistant parle, puis laisser
    # retomber la queue audio (latence Bluetooth) avant d'ouvrir le micro.
    while state.conversation_active.is_set():
        time.sleep(0.05)

    with suprimer_alsa():
        p = pyaudio.PyAudio()
    try:
        stream, rate = _ouvrir_micro(p)
    except RuntimeError as e:
        print(f'Micro indisponible ({e}) — nouvelle tentative dans 5s')
        p.terminate()
        time.sleep(5)
        return ''

    if not _vad_logge:
        vad_actif = _WEBRTC_OK and rate in _VAD_RATES
        print(f'VAD: {"webrtcvad (mode 2)" if vad_actif else "seuil de volume"} @ {rate} Hz')
        _vad_logge = True

    # Cadences dépendantes du taux réel (les valeurs historiques supposaient 16 kHz).
    purge_chunks    = int(0.4 * rate / 1024)          # ~0.4s d'écho résiduel jeté
    min_voix_chunks = int(0.4 * rate / 1024)          # ~0.4s de parole minimum
    silence_max     = max(1, int(16 * rate / _RATE_CIBLE))   # ~1s pour clore la phrase
    timeout_max     = max(1, int(TIMEOUT_ECOUTE * rate / _RATE_CIBLE))  # ~8s sans voix

    # Purge le tampon micro (écho résiduel du haut-parleur capté au démarrage).
    for _ in range(purge_chunks):
        if _lire_chunk(stream) is None:
            print('Micro muet (aucune donnée) — nouvelle tentative dans 5s')
            _fermer(stream, p)
            time.sleep(5)
            return ''

    frames  = []
    silence = 0
    parole  = False
    voix    = 0  # nombre de chunks réellement vocaux (pour le filtre anti-bruit)
    timeout = 0  # chunks sans voix (reset à chaque détection vocale)

    while True:
        # Anti-écho : si l'assistant s'est mis à parler PENDANT qu'on enregistre,
        # tout ce qu'on capte est l'écho du haut-parleur repris par le micro
        # (le système s'entend lui-même) → on jette la capture. Le verrou au
        # début (while conversation_active) ne couvre que l'ouverture du micro ;
        # ce test protège la durée de l'enregistrement (AutoScene parle souvent).
        if state.conversation_active.is_set():
            print("Capture annulée — l'assistant parle (anti-écho)")
            _fermer(stream, p)
            return ''

        data = _lire_chunk(stream)
        if data is None:
            # Le flux s'est tu en cours de route (reconfiguration PipeWire /
            # Bluetooth) → on ferme et on réessaie au prochain cycle, au lieu
            # de geler le thread pour toujours (ancien comportement).
            print('Micro muet (plus aucune donnée) — réouverture au prochain cycle')
            _fermer(stream, p)
            return ''
        chunk  = np.frombuffer(data, dtype=np.int16)
        volume = np.abs(chunk).mean()

        if _est_voix(data, volume, rate):
            # Voix active
            parole  = True
            voix   += 1
            silence = 0
            timeout = 0
            frames.append(data)
        elif parole:
            # Fin de phrase — attente silence pour confirmer
            silence += 1
            frames.append(data)
            if silence > silence_max:
                break
        else:
            # Pas encore de parole — incrémenter le timeout
            timeout += 1
            if timeout >= timeout_max:
                print('Timeout écoute (8s sans voix)')
                break

    _fermer(stream, p)

    if not frames:
        return ''

    # Filtre anti-bruit : capture trop courte → bruit / écho / hallucination.
    if voix < min_voix_chunks:
        print('Capture trop courte — ignorée (bruit/écho)')
        return ''

    # Sauvegarde WAV au taux réel du micro (Whisper accepte tous les taux).
    wf = wave.open(AUDIO_WAV, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()

    return _transcrire()


def _transcrire() -> str:
    """Délègue la transcription au provider STT configuré (voir src/providers/stt.py)."""
    from src.providers.stt import transcribe
    return transcribe()
