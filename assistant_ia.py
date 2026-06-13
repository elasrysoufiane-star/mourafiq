# ╔══════════════════════════════════════════════╗
# ║   Assistant IA — Malvoyants Maroc            ║
# ║   YOLO + Groq (Whisper + LLaMA) + GPS + OCR ║
# ║   Raspberry Pi 4 — Master IT TAM UM5 2026    ║
# ╚══════════════════════════════════════════════╝

import os, contextlib
from ultralytics import YOLO
from picamera2 import Picamera2
import pytesseract
import pyaudio, wave
import threading, time
import serial, pynmea2
from gtts import gTTS
import pygame
from groq import Groq
from PIL import Image
import numpy as np

# ══════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GPS_PORT     = '/dev/ttyS0'
GPS_BAUD     = 9600
AUDIO_MP3    = '/tmp/audio.mp3'
AUDIO_WAV    = '/tmp/audio.wav'
CONF_SEUIL   = 0.60
VOL_SEUIL    = 200  # recalibré au démarrage

# ══════════════════════════════════════════════
# DICTIONNAIRE DARIJA
# ══════════════════════════════════════════════
traductions = {
    'person':        'كاين شي واحد قدامك',
    'car':           'انتبه كاينة طوموبيل',
    'truck':         'انتبه كاين شاحنة',
    'bus':           'كاين طوبيس انتبه',
    'motorcycle':    'انتبه كاينة موتو',
    'bicycle':       'كاين بيسيكلي انتبه',
    'train':         'انتبه كاين قطار',
    'chair':         'كاين كرسي',
    'couch':         'كاين كنابي',
    'bed':           'كاين ليطو',
    'dining table':  'كاينة طابلة',
    'toilet':        'كاين الحمام',
    'bottle':        'كاينة قارورة',
    'cup':           'كاين كاس',
    'wine glass':    'كاينة كاس',
    'book':          'كاين كتاب',
    'clock':         'كاينة ساعة',
    'laptop':        'كاين أوردينتور',
    'cell phone':    'كاين تيليفون',
    'tv':            'كاين تيليفيزيون',
    'backpack':      'كاينة شكارة',
    'umbrella':      'كاينة مظلة',
    'handbag':       'كاينة شنطة',
    'suitcase':      'كاينة ولاصة',
    'scissors':      'كاينة مقص',
    'banana':        'كاينة بنانة',
    'apple':         'كاينة تفاحة',
    'orange':        'كاين ليمون',
    'pizza':         'كاينة بيتزا',
    'cake':          'كاين كاطو',
    'sandwich':      'كاين ساندويتش',
    'dog':           'كاين كلب انتبه',
    'cat':           'كاينة مشة',
    'bird':          'كاين طير',
    'horse':         'كاين عود',
    'cow':           'كاينة بقرة',
    'traffic light': 'كاين ضوء انتبه',
    'stop sign':     'كاينة علامة وقف',
    'bench':         'كاين بنكيو',
    'sports ball':   'كاينة كورة',
}

# ══════════════════════════════════════════════
# SUPPRESSION BRUIT ALSA/JACK
# ══════════════════════════════════════════════
@contextlib.contextmanager
def suprimer_alsa():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

# ══════════════════════════════════════════════
# INITIALISATION
# ══════════════════════════════════════════════
print('=' * 50)
print('Chargement Assistant IA Malvoyants...')

print('Chargement YOLO...')
model = YOLO('yolov8n.pt')

print('Chargement caméra...')
camera = Picamera2()
config = camera.create_preview_configuration(
    main={'format': 'RGB888', 'size': (640, 480)}
)
camera.configure(config)
camera.start()
time.sleep(2)

print('Chargement audio...')
pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.mixer.init()

print('Chargement Groq...')
groq = Groq(api_key=GROQ_API_KEY)

# GPS — port ouvert une seule fois au démarrage
print('Connexion GPS...')
gps_serial = None
try:
    gps_serial = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)
    print('GPS connecté')
except Exception as e:
    print(f'GPS non disponible: {e}')

# Vérification micro
print('Vérification micro...')
with suprimer_alsa():
    _p = pyaudio.PyAudio()
try:
    _info = _p.get_default_input_device_info()
    print(f'Micro détecté: {_info["name"]}')
except Exception:
    print('AVERTISSEMENT: Aucun micro détecté !')
_p.terminate()

# Calibration automatique du seuil de voix
print('Calibration bruit ambiant (2s)...')
def calibrer_micro():
    with suprimer_alsa():
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1,
                        rate=16000, input=True, frames_per_buffer=1024)
    volumes = []
    for _ in range(30):
        data = stream.read(1024, exception_on_overflow=False)
        vol  = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
        volumes.append(vol)
    stream.stop_stream(); stream.close(); p.terminate()
    bruit = float(np.mean(volumes))
    seuil = max(150, int(bruit * 3))
    print(f'Bruit ambiant: {bruit:.0f} → Seuil voix: {seuil}')
    return seuil

VOL_SEUIL = calibrer_micro()

print('Tout est prêt !')
print('=' * 50)

camera_lock         = threading.Lock()
audio_lock          = threading.Lock()
conversation_active = threading.Event()

# ══════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════

def parler(texte):
    with audio_lock:
        try:
            print(f'Pi dit: {texte}')
            pygame.mixer.music.stop()
            gTTS(text=texte, lang='ar').save(AUDIO_MP3)
            pygame.mixer.music.load(AUDIO_MP3)
            pygame.mixer.music.play()
            time.sleep(0.3)  # laisse le Bluetooth démarrer
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            time.sleep(0.4)  # vide le buffer Bluetooth avant de continuer
        except Exception as e:
            print(f'Erreur audio: {e}')

def groq_darija(question):
    for tentative in range(3):
        try:
            response = groq.chat.completions.create(
                model='llama-3.1-8b-instant',
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'أنت مساعد ذكي للمكفوفين في المغرب. '
                            'تتكلم الدارجة المغربية فقط. '
                            'ردودك قصيرة جدا — جملة واحدة فقط. '
                            'أمثلة: كاين كرسي قدامك / سير على اليمين بعد 50 متر / مكتوب صيدلية الأمل'
                        )
                    },
                    {'role': 'user', 'content': question}
                ],
                max_tokens=80,
                temperature=0.3
            )
            reponse = response.choices[0].message.content.strip()
            print(f'Groq darija: {reponse}')
            return reponse
        except Exception as e:
            if '429' in str(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota dépassé, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur Groq: {e}')
                return 'عفوا ماقدرتش نفهم'

def reconnaitre_voix():
    print('En attente de voix...')
    with suprimer_alsa():
        p      = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1,
                        rate=16000, input=True, frames_per_buffer=1024)
    frames  = []
    silence = 0
    parole  = False

    while True:
        data   = stream.read(1024, exception_on_overflow=False)
        chunk  = np.frombuffer(data, dtype=np.int16)
        volume = np.abs(chunk).mean()

        if volume > VOL_SEUIL:
            parole  = True
            silence = 0
            frames.append(data)
        elif parole:
            silence += 1
            frames.append(data)
            if silence > 16:
                break

    stream.stop_stream()
    stream.close()
    p.terminate()

    if not frames:
        return ''

    wf = wave.open(AUDIO_WAV, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(b''.join(frames))
    wf.close()

    for tentative in range(3):
        try:
            with open(AUDIO_WAV, 'rb') as f:
                transcription = groq.audio.transcriptions.create(
                    model='whisper-large-v3-turbo',
                    file=f,
                    language='ar'
                )
            texte = transcription.text.strip()
            print(f'Compris: {texte}')
            return texte
        except Exception as e:
            if '429' in str(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota transcription, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur transcription: {e}')
                return ''

# ══════════════════════════════════════════════
# MODE 1 — VISION AUTOMATIQUE
# ══════════════════════════════════════════════
def mode_vision():
    dernier = ''
    print('Mode Vision démarré...')
    while True:
        try:
            if conversation_active.is_set():
                time.sleep(0.5)
                continue

            with camera_lock:
                img = camera.capture_array()

            results = model(img, verbose=False)
            for r in results:
                for box in r.boxes:
                    obj  = r.names[int(box.cls)]
                    conf = float(box.conf)
                    if conf > CONF_SEUIL and obj in traductions:
                        if obj != dernier:
                            print(f'Vision: {obj} {conf:.0%}')
                            parler(traductions[obj])
                            dernier = obj
                            time.sleep(3)

            time.sleep(0.1)
        except Exception as e:
            print(f'Erreur vision: {e}')
            time.sleep(1)

# ══════════════════════════════════════════════
# MODE 2 — LECTURE OCR
# ══════════════════════════════════════════════
def lire_texte():
    try:
        parler('انتظر كنقرا')
        with camera_lock:
            img = camera.capture_array()
        img_pil = Image.fromarray(img)
        texte   = pytesseract.image_to_string(img_pil, lang='ara+fra')
        if texte.strip():
            print(f'Texte lu: {texte}')
            parler(groq_darija(f'مكتوب في الصورة: {texte} — قل ذلك بالدارجة'))
        else:
            parler('ماكاين حتى نص')
    except Exception as e:
        print(f'Erreur OCR: {e}')
        parler('ماقدرتش نقرا')

# ══════════════════════════════════════════════
# MODE 3 — NAVIGATION GPS
# ══════════════════════════════════════════════
def get_gps():
    if gps_serial is None:
        return None, None
    try:
        for _ in range(30):
            ligne = gps_serial.readline().decode('ascii', errors='ignore')
            if ligne.startswith('$GPGGA'):
                msg = pynmea2.parse(ligne)
                return msg.latitude, msg.longitude
    except Exception as e:
        print(f'Erreur GPS: {e}')
    return None, None

def naviguer(destination):
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

# ══════════════════════════════════════════════
# MODE 4 — CONVERSATION
# ══════════════════════════════════════════════
def mode_conversation():
    print('Mode Conversation démarré...')
    while True:
        try:
            conversation_active.set()
            commande = reconnaitre_voix()
            conversation_active.clear()

            if not commande:
                continue

            print(f'Commande: {commande}')

            if any(m in commande for m in ['وين','فين','أين','موقع','فاين']):
                lat, lon = get_gps()
                if lat and lat != 0:
                    parler(groq_darija(f'موقع المستخدم: {lat:.4f}, {lon:.4f} أخبره بالدارجة'))
                else:
                    parler('ماقدرتش نلقى موقعك دابا')

            elif any(m in commande for m in ['شنو','قدامي','واش','شوف','وصف']):
                with camera_lock:
                    img = camera.capture_array()
                r = model(img, verbose=False)[0]
                objets = [
                    r.names[int(box.cls)]
                    for box in r.boxes[:3]
                    if float(box.conf) > 0.5
                ]
                if objets:
                    parler(groq_darija(f'الأشياء أمام المستخدم: {", ".join(objets)} قل ذلك بالدارجة'))
                else:
                    parler('الطريق واضحة ماكاين والو')

            elif any(m in commande for m in ['قرا','اقرأ','قراءة']):
                lire_texte()

            elif 'صيدلية' in commande:
                naviguer('الصيدلية')
            elif any(m in commande for m in ['سبيطار','مستشفى']):
                naviguer('السبيطار')
            elif 'جامع' in commande:
                naviguer('الجامع')
            elif 'محطة' in commande:
                naviguer('المحطة')
            elif any(m in commande for m in ['ودي','روح','مشي']):
                naviguer('الوجهة')

            elif any(m in commande for m in ['عاون','مساعدة','شنو تقدر']):
                parler('نقدر نعاونك بـ: شنو قدامي، قرا ليا، وين أنا، ودي للصيدلية')

            elif any(m in commande for m in ['وقف','بارك','إيقاف','سلام']):
                parler('مع السلامة بالتوفيق')
                break

            else:
                parler(groq_darija(commande))

        except Exception as e:
            conversation_active.clear()
            print(f'Erreur conversation: {e}')
            time.sleep(1)

# ══════════════════════════════════════════════
# LANCEMENT
# ══════════════════════════════════════════════
print('Démarrage Assistant IA...')
parler('مرحبا أنا مساعدك الذكي ديال المكفوفين كيفاش نعاونك')

t1 = threading.Thread(target=mode_vision, name='Vision')
t2 = threading.Thread(target=mode_conversation, name='Conversation')
t1.daemon = True
t2.daemon = True
t1.start()
t2.start()

print('Vision + Conversation actifs !')

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('Arrêt...')
    if gps_serial:
        gps_serial.close()
    camera.stop()
    pygame.quit()
