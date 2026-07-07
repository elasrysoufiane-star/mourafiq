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

## 2026-07-07 — YOLO retiré, vision 100% Claude

**Décision** : suppression complète de YOLO — `mode_vision()` (boucle de
détection continue), `_local_scene()`/`_phraser_objets()` (fallback scène
hors-ligne), `src/vision/translations.py` (dict COCO→darija), `CONF_SEUIL`,
`MODEL_PATH`, `models/yolov8n.pt`, dépendance `ultralytics`. `describe_scene()`
n'appelle plus que Claude ; `VISION_AI_PROVIDER` a disparu (plus qu'un seul
chemin possible). Si Claude échoue ou `ANTHROPIC_API_KEY` est absente :
message vocal clair d'indisponibilité (`_INDISPONIBLE` dans
`src/providers/vision_ai.py`) — jamais de silence, mais plus de détection
locale de secours.

**Pourquoi** : demande explicite du porteur de projet — la détection YOLO en
conditions réelles (rue, faible luminosité, mouvement) était jugée trop faible
comparée à la description riche de Claude, et maintenir deux chemins de
description (YOLO simpliste + Claude détaillé) ajoutait de la complexité pour
un bénéfice net négatif. Conséquence assumée : **la description de scène
n'est plus gratuite** — elle nécessite `ANTHROPIC_API_KEY` (voir README.md,
section « Mode gratuit »). OCR et GPS restent inchangés (Tesseract toujours
disponible en local pour l'OCR).

**Revenir dessus si** : besoin d'un mode 100% gratuit/hors-ligne pour la
vision — il faudrait réintroduire une détection locale (YOLO ou autre) ;
consulter `git log` avant ce commit pour l'implémentation précédente
(`_local_scene`, `traductions`) si on veut repartir de là plutôt que
recommencer de zéro.

## 2026-07-07 — Timeout explicite (15s) + max_retries=0 sur le client anthropic

**Décision** : `anthropic.Anthropic(api_key=..., timeout=15.0, max_retries=0)`
dans `_get_client()` (`src/ai/claude_client.py`).

**Pourquoi** : symptôme rapporté juste après le retrait de YOLO — AutoScene
tournait (thread démarré, log « Mode description auto démarré ») mais ne
décrivait plus rien du tout, ni à l'oral ni dans les logs, pendant un long
moment, sans la moindre erreur affichée. Cause probable : le SDK anthropic
timeout par défaut à ~10 MIN (httpx) ET retry automatiquement en interne
(silencieusement) AVANT même de laisser remonter l'erreur à notre propre
boucle de retry (`claude_darija`/`_vision_call`, 3 tentatives avec backoff
loggé). Sur un réseau Pi dégradé, ces deux couches de retry se cumulent →
silence total pendant potentiellement plusieurs minutes par cycle, avant
qu'une erreur (donc un fallback parlé) ne sorte enfin.

**Effet** : un appel qui traîne échoue maintenant en 15s max, et c'est NOTRE
retry (visible : « Quota Claude, attente Ns... » / « Erreur Claude: ... ») qui
gère la suite → le message vocal d'indisponibilité (`_INDISPONIBLE`) arrive
en quelques dizaines de secondes maximum au lieu de potentiellement plusieurs
minutes silencieuses.

**Revenir dessus si** : 15s s'avère trop court pour de vraies réponses (ex.
`claude-opus-4-8` sur une image HQ) — monter `_TIMEOUT_S` plutôt que
réactiver `max_retries` du SDK (qui recrée le problème de silence).
