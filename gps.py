import serial
import pynmea2

from config import GPS_PORT, GPS_BAUD
import state
from audio import parler
from groq_service import groq_darija


def init_gps():
    """
    Ouvre la connexion série vers le module GPS.
    Retourne l'objet serial ou None si le GPS n'est pas disponible.
    """
    try:
        ser = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)
        print('GPS connecté')
        return ser
    except Exception as e:
        print(f'GPS non disponible: {e}')
        return None


def get_gps():
    """
    Lit les trames NMEA et retourne (latitude, longitude).
    Retourne (None, None) si le GPS est absent ou sans fix.
    """
    if state.gps_serial is None:
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


def naviguer(destination):
    """
    Récupère la position GPS actuelle et demande à Groq des instructions
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
