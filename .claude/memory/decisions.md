# Journal des décisions — Mourafiq

Une entrée par décision structurante. Les sessions Claude Code lisent ce
fichier pour ne pas re-débattre ce qui a déjà été tranché. Format :
date, décision, pourquoi, comment revenir dessus.

---

## 2026-07-06 — Modèles Claude : sonnet-5 partout à la demande, haiku en continu

**Décision** : `CLAUDE_TEXT_MODEL=claude-sonnet-5`,
`CLAUDE_VISION_MODEL_HQ=claude-sonnet-5`, `CLAUDE_VISION_MODEL=claude-haiku-4-5`.

**Pourquoi** : sonnet-5 est meilleur que sonnet-4-6 (qualité proche Opus sur
vision/langage, vision haute résolution) ET moins cher jusqu'au 31/08/2026
($2/$10 vs $3/$15 par 1M). Opus-4-8 écarté pour la conversation : latence
vocale trop pénalisante pour un utilisateur non-voyant qui attend une réponse
parlée. Haiku garde la boucle AutoScene (720 appels/h à 5 s).

**Réversible via** : `.env` uniquement (profils documentés dans
`.claude/skills/tune-claude/SKILL.md`).

## 2026-07-06 — Thinking explicitement désactivé dans claude_client.py

**Décision** : `thinking={'type': 'disabled'}` (`_THINKING_OFF`) sur tous les
`messages.create`.

**Pourquoi** : sur claude-sonnet-5, omettre le paramètre = thinking adaptatif
ACTIF par défaut. Avec `max_tokens=150` (réponse parlée courte), le thinking
consommerait le budget → réponses tronquées ou vides + latence vocale.
`disabled` est accepté par tous les modèles configurables ici (haiku-4-5,
sonnet-4-6, sonnet-5, opus-4-8). Nécessite un SDK anthropic récent sur le Pi
(`pip install -U anthropic`).

**Revenir dessus si** : on voulait du thinking pour une analyse de scène
complexe — dans ce cas l'activer seulement sur l'appel HQ et monter
`CLAUDE_MAX_TOKENS`.

## 2026-07-06 — Amélioration vision identifiée mais NON faite : capture haute résolution pour OCR

La caméra capture en 640×480 (choisi pour la vitesse YOLO sur Pi 4). C'est LA
limite de qualité pour lire une lettre ou une notice de médicament — pas le
modèle. Piste : capture still haute résolution (ex. 2028×1520) déclenchée
uniquement pour `lire_texte()` / appel HQ, en gardant 640×480 pour la boucle
YOLO. À faire dans `src/core/app.py` (config caméra) + `src/ocr/reader.py`.
