# Journal des décisions — Mourafiq

Une entrée par décision structurante. Les sessions Claude Code lisent ce
fichier pour ne pas re-débattre ce qui a déjà été tranché. Format :
date, décision, pourquoi, comment revenir dessus.

---

## 2026-07-08 — Double clé Anthropic (bascule auto) + Opus à la demande

**Décision** : (a) `ANTHROPIC_API_KEY_FALLBACK` — 2ᵉ clé utilisée
automatiquement si la principale échoue (quota/invalide/panne), via
`claude_client._create` (retries backoff + bascule de clé, centralisés) ;
(b) modèles À LA DEMANDE en `claude-opus-4-8` (`CLAUDE_TEXT_MODEL`,
`CLAUDE_VISION_MODEL_HQ`, `CLAUDE_OCR_MODEL`).

**Pourquoi** : demande explicite — robustesse (une clé de secours pour la
présentation, ne jamais tomber en panne de quota en direct) + qualité MAX
assumée (« use Opus, don't care about tokens »). ⚠️ Opus = +latence vocale
(quelques secondes/réponse) — accepté pour la qualité. La boucle CONTINUE reste
Sonnet 5 (Opus impraticable à ~600 appels/h ; de toute façon OFF en mode démo).
Contredit partiellement 2026-07-06 (« Opus écarté de la conversation pour la
latence ») — l'utilisateur a tranché en faveur de la qualité, latence assumée.

**Réversible via** : `.env` (`CLAUDE_TEXT_MODEL=claude-sonnet-5` etc. pour
revenir à moins de latence).

## 2026-07-08 — GPS désactivé + mode « à la demande » par défaut (présentation samedi)

**Décision** : `GPS_ENABLED=0` (GPS coupé) et `AUTO_DESCRIBE_INTERVAL=0`
(pas de narration automatique — l'assistant répond UNIQUEMENT sur commande
vocale « شنو قدامي » / « قرا ليا »).

**Pourquoi** : présentation le samedi 2026-07-11, l'utilisateur veut une démo
maîtrisée. (1) GPS retiré du produit : matériel Pi non fiable (Permission
denied /dev/ttyS0) + navigation approximative sans API de routage — écarté,
`init()` ne touche plus au port série, « وين أنا » retiré de l'accueil/aide
(code GPS gardé, dormant, réactivable `GPS_ENABLED=1`). (2) Mode à la demande :
sur scène, le contrôle du rythme prime + supprime la boucle d'écho (le micro
n'entend plus l'assistant puisqu'il ne parle que sur commande). Réactiver la
description continue « yeux permanents » = `AUTO_DESCRIBE_INTERVAL=10`.

**Réversible via** : `.env` (`GPS_ENABLED=1`, `AUTO_DESCRIBE_INTERVAL=10`).

## 2026-07-08b — Qualité dialogue/expérience (tokens no-object) : budgets séparés, Sonnet en continu, Opus OCR, suivi visuel

**Décision** : (a) budgets tokens séparés — `CLAUDE_MAX_TOKENS=300` (à la
demande + chat), `CLAUDE_SCENE_AUTO_MAX_TOKENS=80` (boucle de fond) ;
(b) boucle continue AutoScene en `claude-sonnet-5` (au lieu de Haiku) ;
(c) OCR à la demande en `claude-opus-4-8` (`CLAUDE_OCR_MODEL`), OCR de fond
reste Sonnet ; (d) `CONV_MEMORY_TURNS=15` + garde la DERNIÈRE image vue à la
demande, rattachée à la question chat suivante (suivi visuel) ;
(e) `CLAUDE_IMG_QUALITY=90`.

**Pourquoi** : demande « meilleure expérience + dialogue, coût no-object ».
Principe directeur : le VRAI facteur limitant est la LATENCE vocale (utilisateur
non-voyant qui attend une réponse parlée), pas le coût. Donc on met la qualité
là où l'utilisateur attend peu (boucle de fond → Sonnet) ou où la précision
prime et l'attente est acceptable (OCR à la demande → Opus). Opus reste écarté
de la conversation et de la scène (trop lent). Budgets séparés = narration de
fond brève (ne monopolise pas la parole, ↓écho) MAIS réponses riches quand
l'utilisateur pose une vraie question. Le prochain gros levier de latence est
le **streaming Claude→TTS** (parler dès la 1ʳᵉ phrase), gardé en chantier séparé.

**Réversible via** : `.env` (chaque variable surcharge son défaut).

## 2026-07-08 — Défauts = meilleure qualité, .env = clés API uniquement, TTS Azure

**Décision** : les défauts de `config/settings.py` passent en « meilleure
qualité » : `AI_PROVIDER=claude`, `OCR_PROVIDER=claude`, `TTS_PROVIDER=azure`
(nouveau provider Azure Speech officiel — même voix `ar-MA-JamalNeural`
qu'edge-tts, tier F0 gratuit 500K car./mois, REST via stdlib urllib),
`STT_MODEL=whisper-large-v3`, `CLAUDE_TEXT_MODEL` et `CLAUDE_VISION_MODEL_HQ`
= `claude-sonnet-5`, `CLAUDE_IMG_MAX_PX=1568`, `AUTO_DESCRIBE_INTERVAL=6`.
Le `.env` ne contient plus QUE les clés (GROQ / ANTHROPIC / AZURE_SPEECH).

**Pourquoi** : demande explicite (présentation du projet, coût accepté —
« meilleur résultat pour l'assistance d'un malvoyant, sans se soucier des
tokens »). L'ancienne règle « défauts gratuits dans le code » imposait un .env
chargé de config ; inversée : la qualité est le défaut, le gratuit est le
FALLBACK automatique (sans clé : claude→groq, azure→edge, OCR claude→Tesseract
— testé dans test_fallbacks.py, l'app ne crashe jamais). Azure choisi pour le
TTS car c'est la MÊME voix marocaine qu'edge-tts en API officielle stable —
ElevenLabs écarté (pas de voix darija, 10× plus cher). La boucle continue
reste Haiku (600 appels/h à 6 s) : Sonnet en continu ≈ $6/h sans gain vocal
net ; Sonnet reste réservé à la demande.

**Réversible via** : `.env` (toute variable surcharge son défaut) — profils
eco/mixte/max dans `.claude/skills/tune-claude/SKILL.md`.

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
