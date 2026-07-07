"""
Thread vision — boucle YOLO continue.
Détecte les objets avec YOLOv8n et annonce chaque nouveau objet en darija.
Se met en pause uniquement pendant la sortie audio (conversation_active).
"""
import time

from config.settings import CONF_SEUIL, AUTO_DESCRIBE_INTERVAL
from src.core import state
from src.audio.speaker import parler
from src.vision.camera import capturer
from src.vision.translations import traductions

# Phrases « rien à lire » communes aux deux providers OCR — Tesseract renvoie
# l'une des deux exactement, Claude une variante qui commence pareil (voir
# _local_ocr et _OCR_SYSTEM_PROMPT dans claude_client.py). Sert à ne PAS
# annoncer ces phrases creuses à chaque cycle de la boucle auto (bruyant).
_OCR_SANS_RESULTAT = ('ماكاين حتى نص', 'ماقدرتش نقرا')


def mode_vision() -> None:
    """
    Boucle principale du thread vision.
    Capture → YOLO → annonce si objet nouveau avec confiance > CONF_SEUIL.
    Pause de 3s entre deux annonces pour ne pas saturer l'utilisateur.
    """
    dernier = ''
    print('Mode Vision démarré...')

    while True:
        try:
            # Pause seulement pendant la sortie audio
            if state.conversation_active.is_set():
                time.sleep(0.5)
                continue

            img = capturer()  # flux 640×480 — rapide, suffisant pour YOLO

            results = state.model(img, verbose=False)
            for r in results:
                for box in r.boxes:
                    obj  = r.names[int(box.cls)]
                    conf = float(box.conf)

                    if conf > CONF_SEUIL and obj in traductions and obj != dernier:
                        print(f'Vision: {obj} {conf:.0%}')
                        parler(traductions[obj])
                        dernier = obj
                        time.sleep(3)

            time.sleep(0.1)  # limite le CPU entre les frames

        except Exception as e:
            print(f'Erreur vision: {e}')
            time.sleep(1)


def mode_auto_scene() -> None:
    """
    Boucle de description automatique — TOUJOURS active (avec ou sans micro,
    que l'utilisateur parle ou non). Toutes les AUTO_DESCRIBE_INTERVAL
    secondes : capture → describe_scene() + read_text() → parle. Tourne en
    parallèle du thread Conversation ; une commande vocale (« شنو قدامي؟ »
    ou « قرا ليا ») déclenche en plus une réponse immédiate à la demande,
    sans jamais couper cette boucle de fond (mêmes verrous `camera_lock` /
    `audio_lock`).

    Deux appels par cycle, sur la MÊME capture (pas de second accès caméra) :
      • describe_scene() — scène/obstacles, routé par VISION_AI_PROVIDER
        ('claude' + ANTHROPIC_API_KEY → VLM riche, sinon YOLO+Groq gratuit)
      • read_text()      — texte visible (panneau, étiquette...), routé par
        OCR_PROVIDER ('claude' → VLM, sinon Tesseract local) ; les réponses
        creuses (_OCR_SANS_RESULTAT : aucun texte / Tesseract indisponible)
        sont tues pour ne pas les répéter toutes les AUTO_DESCRIBE_INTERVAL s ;
        remember=False (pas un tour de dialogue, voir src/core/memory.py)
    Capture en 640×480 (pas de still HQ ici → pas de stall caméra périodique) ;
    le cooldown VISION_COOLDOWN est respecté côté describe_scene().
    """
    from src.providers.vision_ai import describe_scene
    from src.providers.ocr import read_text
    print(f'Mode description auto démarré (chaque {AUTO_DESCRIBE_INTERVAL:.0f}s)...')

    while True:
        try:
            time.sleep(AUTO_DESCRIBE_INTERVAL)

            # Ne pas capturer/parler par-dessus une sortie audio en cours.
            if state.conversation_active.is_set():
                continue

            img = capturer()  # flux 640×480 — boucle éco, pas de still HQ ici

            desc = describe_scene(img)
            if desc:
                parler(desc)

            texte = read_text(img, remember=False)
            if texte and not any(s in texte for s in _OCR_SANS_RESULTAT):
                parler(texte)

        except Exception as e:
            print(f'Erreur description auto: {e}')
            time.sleep(1)
