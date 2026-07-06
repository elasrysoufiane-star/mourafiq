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

Si de nouvelles variables `.env` ont été ajoutées côté dev, les reporter à la
main dans le `.env` du Pi (comparer avec `.env.example`). Vérifier que les
vraies clés (`GROQ_API_KEY`, `ANTHROPIC_API_KEY`) sont bien présentes.

## 4. Test réel

```bash
python3 main.py
```

Vérifier dans l'ordre :
1. Message de bienvenue audible (TTS OK, sink Bluetooth OK)
2. Log `Claude texte usage:` ou `TTS engine:` cohérent avec les providers .env
3. Mot de réveil « مرافق » reconnu → réponse
4. « شنو قدامي » → description Claude (log `Claude scene usage:`)
5. « قرا ليا » → lecture OCR
6. Coût : les lignes `usage: in=... out=...` restent dans les ordres de
   grandeur attendus (~1-2k in / ~150 out par scène)

## Rappels matériels

- Écouteurs : `bluetoothctl connect 28:52:E0:23:61:6F` puis
  `pactl set-default-sink $(pactl list sinks short | grep bluez | awk '{print $2}')`
- FreeBuds SE 3 (`70:40:FF:6E:21:7E`) : ne pas utiliser (échec PipeWire).
