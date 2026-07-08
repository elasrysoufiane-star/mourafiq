---
name: deploy-pi
description: Checklist de déploiement de Mourafiq vers le Raspberry Pi (commit → push → pull sur le Pi → dépendances → test réel). Utiliser quand l'utilisateur veut envoyer les changements sur le Pi ou demande « déploie ».
---

# Déployer sur le Raspberry Pi

Le développement se fait sur Windows (sans matériel), l'exécution réelle sur
le Pi 4 (`/home/som/mourafiq`, venv `/home/som/projet_ia`).

## 1. Avant de pousser (sur Windows)

```powershell
python -m pytest tests/ -v          # tout doit passer
git status                          # rien d'inattendu (surtout pas .env !)
git add <fichiers> ; git commit ; git push
```

`.env` n'est JAMAIS commité — la config du Pi vit sur le Pi.

## 2. Sur le Pi (SSH)

```bash
cd ~/mourafiq
git pull
source /home/som/projet_ia/bin/activate
pip install -r requirements.txt --upgrade   # si requirements.txt a changé
git lfs pull                                # si models/ a changé
```

⚠️ Si `src/ai/claude_client.py` a changé (paramètres API comme `thinking=`),
mettre à jour le SDK : `pip install -U anthropic`.

## 3. Synchroniser la config

Depuis 2026-07-08, le `.env` ne contient que les CLÉS API — toute la config
(providers, modèles, intervalles) vit dans `config/settings.py` avec des
défauts « meilleure qualité ». Sur le Pi, réduire l'ancien `.env` à trois
lignes (sinon ses vieilles valeurs `TTS_PROVIDER=edge`, `AUTO_DESCRIBE_INTERVAL=5`…
écraseraient les nouveaux défauts) : `GROQ_API_KEY`, `ANTHROPIC_API_KEY`,
`AZURE_SPEECH_KEY` (optionnel — vide = fallback edge-tts). Comparer avec
`.env.example`.

## 4. Test réel

```bash
python3 main.py
```

Toute la sortie est aussi enregistrée dans `logs/mourafiq_AAAAMMJJ_HHMMSS.log`
(horodatée + nom du thread) — la première ligne affiche `Logs → logs/...`.
Pour copier un log au debug : `ls -t logs/` puis `cat logs/<le plus récent>`,
ou depuis Windows : `scp som@<ip-pi>:~/mourafiq/logs/mourafiq_*.log .`.
(`LOG_TO_FILE=0` dans `.env` = console seule si besoin.)

Vérifier dans l'ordre :
1. Message de bienvenue audible (TTS OK, sink Bluetooth OK)
2. Log `Claude texte usage:` ou `TTS engine:` cohérent avec les providers .env
3. Mot de réveil « مرافق » reconnu → réponse
4. « شنو قدامي » → description Claude (log `Claude scene usage:`) — la capture
   HQ ajoute ~0.5-1 s (switch_mode), c'est normal ; si le log montre
   `Capture HQ échouée`, vérifier la config still (ou `HQ_CAPTURE_ENABLED=0`)
5. « قرا ليا » → lecture OCR : tester avec une vraie lettre/notice — c'est le
   cas qui profite du still haute résolution
6. Coût : les lignes `usage: in=... out=...` restent dans les ordres de
   grandeur attendus (~1-2k in la scène 640px, ~2-3k in le still 1568px,
   ~150 out par scène)

## Rappels matériels

- Écouteurs : `bluetoothctl connect 28:52:E0:23:61:6F` puis
  `pactl set-default-sink $(pactl list sinks short | grep bluez | awk '{print $2}')`
- FreeBuds SE 3 (`70:40:FF:6E:21:7E`) : ne pas utiliser (échec PipeWire).
