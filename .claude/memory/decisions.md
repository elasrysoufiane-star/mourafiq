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

## 2026-07-06 — Capture haute résolution pour OCR / scène à la demande (FAIT)

**Décision** : `src/vision/camera.py` `capturer(hq=)` centralise toutes les
captures (avec `camera_lock`). `hq=True` (OCR + « شنو قدامي ») → still PLEINE
résolution capteur via `switch_mode_and_capture_array` (~0.5-1 s, ponctuel) ;
boucles YOLO/auto → flux 640×480 inchangé. `.env` : `CLAUDE_IMG_MAX_PX=1568`.

**Pourquoi** : 640×480 était LA limite pour lire une lettre/notice — pas le
modèle. Le switch_mode ponctuel évite de ralentir YOLO (un flux haute
résolution permanent aurait tué le FPS sur Pi 4). Le still est réduit à
`CLAUDE_IMG_MAX_PX` avant envoi → la boucle continue (source 640px) ne coûte
pas un token de plus.

**Garde-fous** : `HQ_CAPTURE_ENABLED=0` désactive tout (retour comportement
640×480) ; échec still → fallback silencieux flux vidéo, jamais d'exception.
**À valider sur le Pi** : latence réelle du switch_mode et couleurs du still
(même format RGB888 que le flux — devrait être identique).
