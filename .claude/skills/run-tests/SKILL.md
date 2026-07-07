---
name: run-tests
description: Lance la suite de tests de Mourafiq sur Windows (sans matériel Pi). Utiliser après toute modification de code, avant un commit, ou quand l'utilisateur demande « lance les tests ».
---

# Lancer les tests Mourafiq (Windows, sans Pi)

Les tests sont conçus pour tourner SANS matériel : les imports lourds
(Picamera2, Groq, anthropic, PIL) sont lazy — ne jamais les rendre
top-level, c'est ce qui garde le projet testable sur Windows.

## Commande

Depuis la racine du projet :

```powershell
python -m pytest tests/ -v
```

Si pytest n'est pas installé, chaque fichier se lance directement :

```powershell
python tests/test_config.py
python tests/test_intents.py
python tests/test_providers.py
python tests/test_memory.py
python tests/test_fallbacks.py
python tests/test_listener.py
```

## Ce que couvre chaque fichier

| Fichier | Couvre |
|---|---|
| test_config.py | Constantes config/settings.py + chargement .env |
| test_intents.py | process_command, mot de réveil (contient_wake/retirer_wake) |
| test_providers.py | Routage AI/STT/TTS/vision/OCR + fallbacks clés absentes |
| test_memory.py | Mémoire conversation (CONV_MEMORY_TURNS) + nettoyage TTS |
| test_fallbacks.py | Bascule (Groq/Tesseract) et message vocal clair si Claude en panne — pas de fallback local pour la scène (YOLO retiré) |
| test_listener.py | VAD webrtcvad/seuil + index micro (sans matériel) |
| smoke_claude_vision.py | ISOLÉ — appel Claude vision réel (clé + image requis), ne pas inclure dans la CI |

## Règles

- Un test qui échoue après ta modification = corriger avant de continuer,
  jamais le skipper.
- Si tu ajoutes une constante config ou un provider : ajouter le test
  correspondant dans test_config.py / test_providers.py dans le même commit.
- `smoke_claude_vision.py` consomme des tokens payants — ne le lancer que
  sur demande explicite.
