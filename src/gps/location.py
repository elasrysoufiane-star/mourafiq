"""
Module GPS — connexion série NMEA et navigation vocale.
Le port GPS est optionnel : si absent, les fonctions GPS retournent None.
"""
try:
    import serial
    import pynmea2
    _GPS_OK = True
except ImportError:
    _GPS_OK = False
    print('AVERTISSEMENT: pyserial/pynmea2 absent — GPS désactivé')

from config.settings import GPS_PORT, GPS_BAUD
from src.core import state
from src.audio.speaker import parler
from src.ai.groq_client import groq_darija


def init_gps():
    """
    Ouvre la connexion série vers le module GPS.
    Retourne l'objet serial.Serial ou None si indisponible.
    """
    if not _GPS_OK:
        return None
    try:
        ser = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)
        print('GPS connecté')
        return ser
    except Exception as e:
        print(f'GPS non disponible: {e}')
        return None


def get_gps() -> tuple:
    """
    Lit les trames NMEA et retourne (latitude, longitude).
    Retourne (None, None) si GPS absent ou sans fix satellite.
    """
    if state.gps_serial is None or not _GPS_OK:
        return None, None
    try:
        for _ in range(30):
            ligne = state.gps_serial.readline().decode('ascii', errors='ignore')
            if ligne.startswith('$GPGGA'):
                msg = pynmea2.parse(ligne)
                return msg.latitude, msg.longitude
    except Exception as e:
        print(f'Erreur GPS: {e}')
    return None, None


def naviguer(destination: str) -> None:
    """
    Récupère la position GPS et demande à Groq LLaMA des instructions
    de navigation vers la destination en darija.
    """
    lat, lon = get_gps()
    if lat and lat != 0:
        msg = (
            f'المستخدم يريد الذهاب إلى {destination} '
            f'موقعه: {lat:.4f}, {lon:.4f} '
            f'أعطه تعليمات قصيرة بالدارجة'
        )
        parler(groq_darija(msg))
    else:
        parler('ماقدرتش نلقى موقعك دابا حاول من برا')
