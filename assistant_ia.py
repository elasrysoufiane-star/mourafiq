# ╔══════════════════════════════════════════════╗
# ║   Assistant IA — Malvoyants Maroc            ║
# ║   YOLO + Gemini + GPS + OCR                  ║
# ║   Raspberry Pi 4 — Master IT TAM UM5 2026    ║
# ╚══════════════════════════════════════════════╝

import os
from ultralytics import YOLO
from picamera2 import Picamera2
import pytesseract
import pyaudio, wave
import threading, time
import serial, pynmea2
from gtts import gTTS
import pygame
import google.generativeai as genai
from PIL import Image
import numpy as np

# ══════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════
#GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_API_KEY = "AQ.Ab8RN6LjmR_lvoQoSc_yWTexleFenmI-OUWMM74l5PLM7GFkzQ"

GPS_PORT       = '/dev/ttyS0'
GPS_BAUD       = 9600
AUDIO_MP3      = '/tmp/audio.mp3'
AUDIO_WAV      = '/tmp/audio.wav'
CONF_SEUIL     = 0.60
VOL_SEUIL      = 500

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
# INITIALISATION
# ══════════════════════════════════════════════
print('=' * 50)
print('Chargement Assistant IA Malvoyants...')

# YOLO
print('Chargement YOLO...')
model = YOLO('yolov8n.pt')

# Caméra RGB
print('Chargement caméra...')
camera = Picamera2()
config = camera.create_preview_configuration(
    main={'format': 'RGB888', 'size': (640, 480)}
)
camera.configure(config)
camera.start()
time.sleep(2)

# Audio
print('Chargement audio...')
pygame.mixer.init()

# Gemini
print('Chargement Gemini...')
genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel('gemini-2.0-flash')

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
            gTTS(text=texte, lang='ar').save(AUDIO_MP3)
            pygame.mixer.music.load(AUDIO_MP3)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception as e:
            print(f'Erreur audio: {e}')

def gemini_darija(question):
    try:
        prompt = f"""أنت مساعد ذكي للمكفوفين في المغرب.
تتكلم الدارجة المغربية فقط.
ردودك قصيرة جدا — جملة واحدة فقط.
أمثلة على ردودك:
- كاين كرسي قدامك
- سير على اليمين بعد 50 متر
- الطريق واضحة ماكاين والو
- مكتوب صيدلية الأمل

السؤال أو الموقف: {question}"""

        response = gemini.generate_content(prompt)
        reponse  = response.text.strip()
        print(f'Gemini darija: {reponse}')
        return reponse
    except Exception as e:
        print(f'Erreur Gemini: {e}')
        return 'عفوا ماقدرتش نفهم'

def reconnaitre_voix():
    print('En attente de voix...')
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=1024
    )
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

    # Sauvegarder audio
    wf = wave.open(AUDIO_WAV, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(b''.join(frames))
    wf.close()

    # Transcrire avec Gemini
    try:
        audio_file = genai.upload_file(AUDIO_WAV)
        result = gemini.generate_content([
            audio_file,
            'اكتب فقط ما قاله الشخص بالعربية بدون أي تعليق'
        ])
        genai.delete_file(audio_file.name)
        texte = result.text.strip()
        print(f'Compris: {texte}')
        return texte
    except Exception as e:
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
        texte   = pytesseract.image_to_string(
            img_pil, lang='ara+fra'
        )
        if texte.strip():
            print(f'Texte lu: {texte}')
            msg = gemini_darija(
                f'مكتوب في الصورة: {texte} — قل ذلك بالدارجة'
            )
            parler(msg)
        else:
            parler('ماكاين حتى نص')
    except Exception as e:
        print(f'Erreur OCR: {e}')
        parler('ماقدرتش نقرا')

# ══════════════════════════════════════════════
# MODE 3 — NAVIGATION GPS
# ══════════════════════════════════════════════
def get_gps():
    try:
        ser = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)
        for _ in range(30):
            ligne = ser.readline().decode(
                'ascii', errors='ignore'
            )
            if ligne.startswith('$GPGGA'):
                msg = pynmea2.parse(ligne)
                ser.close()
                return msg.latitude, msg.longitude
        ser.close()
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
        parler(gemini_darija(msg))
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

            # Où suis-je ?
            if any(m in commande for m in [
                'وين','فين','أين','موقع','فاين'
            ]):
                lat, lon = get_gps()
                if lat and lat != 0:
                    msg = f'موقع المستخدم: {lat:.4f}, {lon:.4f} أخبره بالدارجة'
                    parler(gemini_darija(msg))
                else:
                    parler('ماقدرتش نلقى موقعك دابا')

            # Quoi devant ?
            elif any(m in commande for m in [
                'شنو','قدامي','واش','شوف','وصف'
            ]):
                with camera_lock:
                    img = camera.capture_array()
                r   = model(img, verbose=False)[0]
                if r.boxes:
                    objets = []
                    for box in r.boxes[:3]:
                        obj  = r.names[int(box.cls)]
                        conf = float(box.conf)
                        if conf > 0.5:
                            objets.append(obj)
                    if objets:
                        msg = f'الأشياء أمام المستخدم: {", ".join(objets)} قل ذلك بالدارجة'
                        parler(gemini_darija(msg))
                    else:
                        parler('الطريق واضحة ماكاين والو')
                else:
                    parler('الطريق واضحة ماكاين والو')

            # Lis
            elif any(m in commande for m in [
                'قرا','اقرأ','قراءة'
            ]):
                lire_texte()

            # Navigation
            elif 'صيدلية' in commande:
                naviguer('الصيدلية')
            elif any(m in commande for m in [
                'سبيطار','مستشفى'
            ]):
                naviguer('السبيطار')
            elif 'جامع' in commande:
                naviguer('الجامع')
            elif 'محطة' in commande:
                naviguer('المحطة')
            elif any(m in commande for m in [
                'ودي','روح','مشي'
            ]):
                naviguer('الوجهة')

            # Aide
            elif any(m in commande for m in [
                'عاون','مساعدة','شنو تقدر'
            ]):
                parler(
                    'نقدر نعاونك بـ: '
                    'شنو قدامي، '
                    'قرا ليا، '
                    'وين أنا، '
                    'ودي للصيدلية'
                )

            # Arrêt
            elif any(m in commande for m in [
                'وقف','بارك','إيقاف','سلام'
            ]):
                parler('مع السلامة بالتوفيق')
                break

            # Commande libre
            else:
                reponse = gemini_darija(commande)
                parler(reponse)

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
    camera.stop()
    pygame.quit()
