"""
Smoke-test du chemin Claude vision EN ISOLATION (avant de lancer toute l'app).
Teste l'encodage image + l'appel Claude + le log d'usage, sans threads ni YOLO.

Usage :
  # Sur le Pi (capture une frame depuis la PiCamera2) :
  ANTHROPIC_API_KEY=sk-ant-... python3 tests/smoke_claude_vision.py

  # Avec une image fixe (marche aussi sur PC, pas besoin de caméra) :
  ANTHROPIC_API_KEY=sk-ant-... python3 tests/smoke_claude_vision.py photo.jpg

  # Question personnalisée :
  python3 tests/smoke_claude_vision.py photo.jpg "واش كاين شي حد قدامي؟"

Sortie attendue : une phrase darija + une ligne "Claude scene usage: in=.. out=..".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import ANTHROPIC_API_KEY, CLAUDE_VISION_MODEL


def _charger_image(chemin: str):
    """Image fichier -> numpy RGB."""
    import numpy as np
    from PIL import Image
    return np.array(Image.open(chemin).convert('RGB'))


def _capturer_picamera():
    """Capture une frame depuis la PiCamera2 (Raspberry Pi uniquement)."""
    from picamera2 import Picamera2
    cam = Picamera2()
    cam.configure(cam.create_preview_configuration())
    cam.start()
    import time
    time.sleep(2)  # laisse l'auto-exposition se stabiliser
    img = cam.capture_array()
    cam.close()
    # PiCamera2 renvoie souvent du RGBA/BGR -> garder 3 canaux RGB
    return img[:, :, :3]


def main():
    if not ANTHROPIC_API_KEY:
        print('ERREUR: ANTHROPIC_API_KEY non defini. '
              'export ANTHROPIC_API_KEY="sk-ant-..." avant de lancer.')
        sys.exit(1)

    args = sys.argv[1:]
    chemin = args[0] if args and not args[0].startswith(('شنو', 'واش')) else None
    question = next((a for a in args if a.startswith(('شنو', 'واش'))), 'شنو قدامي؟')

    print(f'Modele vision : {CLAUDE_VISION_MODEL}')
    if chemin:
        print(f'Image fichier : {chemin}')
        image = _charger_image(chemin)
    else:
        print('Capture PiCamera2 (2s)...')
        image = _capturer_picamera()
    print(f'Image shape   : {image.shape}')
    print(f'Question      : {question}')
    print('Appel Claude en cours...\n')

    # Import apres la validation -> message clair si la lib manque
    from src.ai.claude_client import claude_describe_scene
    reponse = claude_describe_scene(image, question)

    print('\n=== Reponse darija ===')
    print(reponse)


if __name__ == '__main__':
    main()
