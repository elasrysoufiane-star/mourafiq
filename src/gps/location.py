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

import json
import time
import urllib.parse
import urllib.request

from config.settings import (
    GPS_PORT, GPS_BAUD, GPS_READ_TIMEOUT,
    GEOCODE_ENABLED, GEOCODE_TIMEOUT,
)
from src.core import state
from src.audio.speaker import parler
from src.providers.ai import get_ai_response

_NOMINATIM_URL = 'https://nominatim.openstreetmap.org/reverse'
# Politique d'usage Nominatim : User-Agent identifiable obligatoire, ~1 req/s.
_GEOCODE_HEADERS = {'User-Agent': 'Mourafiq/1.0 (assistive device for the blind)'}
# Cache des adresses déjà résolues (clé arrondie à ~11 m) — limite les requêtes.
_geocode_cache: dict = {}


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

    - Accepte GGA de n'importe quelle constellation (GPGGA, GNGGA, GLGGA…) :
      les récepteurs multi-constellation modernes émettent GNGGA, pas GPGGA.
    - Vérifie gps_qual (0 = pas de fix) — sinon pynmea2 renvoie 0.0.
    - Lecture bornée dans le temps (GPS_READ_TIMEOUT) pour ne pas bloquer
      le thread conversation ; une trame corrompue n'interrompt pas la lecture.
    """
    if state.gps_serial is None or not _GPS_OK:
        return None, None
    deadline = time.monotonic() + GPS_READ_TIMEOUT
    try:
        while time.monotonic() < deadline:
            ligne = state.gps_serial.readline().decode('ascii', errors='ignore')
            # Position 3:6 = type de trame, indépendant de la constellation.
            if ligne[3:6] != 'GGA':
                continue
            try:
                msg = pynmea2.parse(ligne)
            except pynmea2.ParseError:
                continue  # checksum/trame corrompue → ligne suivante
            # gps_qual vide ou 0 → pas de fix satellite, coordonnées non valides.
            if not msg.gps_qual or int(msg.gps_qual) == 0:
                continue
            return msg.latitude, msg.longitude
    except Exception as e:
        print(f'Erreur GPS: {e}')
    return None, None


def _format_adresse(data: dict) -> str:
    """Construit une adresse courte (rue، quartier، ville) depuis Nominatim."""
    addr = data.get('address', {})

    def first(*cles):
        for c in cles:
            if addr.get(c):
                return addr[c]
        return None

    rue      = first('road', 'pedestrian', 'footway')
    quartier = first('neighbourhood', 'suburb', 'quarter', 'city_district')
    ville    = first('city', 'town', 'village', 'municipality')
    parts = [p for p in (rue, quartier, ville) if p]
    # Fallback : adresse complète brute si aucun composant attendu.
    return '، '.join(parts) if parts else data.get('display_name', '')


def reverse_geocode(lat: float, lon: float):
    """
    Convertit (lat, lon) en adresse lisible via OpenStreetMap Nominatim.
    Retourne une chaîne courte (rue، quartier، ville) ou None si indisponible
    (geocoding désactivé, pas d'Internet, ou erreur réseau → fallback coords).
    """
    if not GEOCODE_ENABLED:
        return None
    key = (round(lat, 4), round(lon, 4))  # ~11 m → réutilise le cache
    if key in _geocode_cache:
        return _geocode_cache[key]
    params = urllib.parse.urlencode({
        'lat': lat, 'lon': lon, 'format': 'jsonv2',
        'accept-language': 'ar', 'zoom': 18,
    })
    req = urllib.request.Request(f'{_NOMINATIM_URL}?{params}', headers=_GEOCODE_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=GEOCODE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        adresse = _format_adresse(data) or None
        _geocode_cache[key] = adresse
        return adresse
    except Exception as e:
        print(f'Reverse geocode échoué (fallback coords): {e}')
        return None


def position_actuelle():
    """
    Position courante prête à être parlée, en darija.
    Retourne None si aucun fix GPS — l'appelant gère le message d'échec.
    Utilise l'adresse réelle (reverse geocoding) si disponible, sinon les
    coordonnées brutes.
    """
    lat, lon = get_gps()
    if not lat or lat == 0:
        return None
    adresse = reverse_geocode(lat, lon)
    if adresse:
        return get_ai_response(f'موقع المستخدم: {adresse} أخبره بإيجاز بالدارجة')
    return get_ai_response(f'موقع المستخدم: {lat:.4f}, {lon:.4f} أخبره بالدارجة')


def naviguer(destination: str) -> None:
    """
    Récupère la position GPS et demande à Groq LLaMA des instructions
    de navigation vers la destination en darija.

    NOTE : sans API de routage, le LLM ne dispose que de la position de départ
    (adresse réelle si geocoding dispo) — il ne peut PAS calculer un vrai
    itinéraire. À remplacer par OSRM/Directions pour du turn-by-turn fiable.
    """
    lat, lon = get_gps()
    if lat and lat != 0:
        depart = reverse_geocode(lat, lon) or f'{lat:.4f}, {lon:.4f}'
        msg = (
            f'المستخدم في {depart} وبغا يمشي إلى {destination}. '
            f'أعطه تعليمات قصيرة وعامة بالدارجة'
        )
        parler(get_ai_response(msg))
    else:
        parler('ماقدرتش نلقى موقعك دابا حاول من برا')
