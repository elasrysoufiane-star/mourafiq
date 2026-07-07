---
name: tune-claude
description: Choisit et applique un profil coût/qualité pour l'API Anthropic dans .env (eco / mixte / max). Utiliser quand l'utilisateur veut ajuster le coût, la qualité ou la latence de Claude, ou demande quel modèle utiliser.
---

# Régler le profil Claude (coût / qualité / latence)

Tout se règle dans `.env` — ne JAMAIS changer les défauts gratuits dans le code
(règle projet n°1). Tarifs au 2026-07 (par 1M tokens in/out) :

| Modèle | Prix | Rôle idéal ici |
|---|---|---|
| claude-haiku-4-5 | $1 / $5 | Boucle vision continue (AutoScene) |
| claude-sonnet-5 | $2 / $10 (intro jusqu'au 31/08/2026, puis $3/$15) | Conversation + vision/OCR à la demande — LE meilleur rapport qualité/prix |
| claude-opus-4-8 | $5 / $25 | Qualité absolue, mais latence vocale plus élevée — rarement justifié ici |

## Profils

### mixte (RECOMMANDÉ — config actuelle)
```env
CLAUDE_TEXT_MODEL=claude-sonnet-5
CLAUDE_VISION_MODEL=claude-haiku-4-5
CLAUDE_VISION_MODEL_HQ=claude-sonnet-5
AUTO_DESCRIBE_INTERVAL=2
```
≈ $0.002/question vocale, ≈ $0.003/scène HQ. Latence bonne.

### eco (limiter la facture)
```env
CLAUDE_TEXT_MODEL=claude-haiku-4-5
CLAUDE_VISION_MODEL=claude-haiku-4-5
CLAUDE_VISION_MODEL_HQ=claude-haiku-4-5
AUTO_DESCRIBE_INTERVAL=10
```

### max (coût accepté, qualité absolue)
```env
CLAUDE_TEXT_MODEL=claude-sonnet-5
CLAUDE_VISION_MODEL=claude-sonnet-5
CLAUDE_VISION_MODEL_HQ=claude-opus-4-8
AUTO_DESCRIBE_INTERVAL=8
```
⚠️ Opus = +latence sur un assistant vocal ; tester avant d'adopter.

## Pièges connus

- **`thinking`** : sur claude-sonnet-5 le thinking adaptatif est actif par
  défaut si le paramètre est omis → le code le désactive explicitement
  (`_THINKING_OFF` dans `src/ai/claude_client.py`). Ne pas retirer.
- **Le levier de coût n°1 est `AUTO_DESCRIBE_INTERVAL`** (défaut `2`) — la
  boucle AutoScene tourne TOUJOURS (avec ou sans micro) et appelle **scène ET
  OCR** à chaque cycle : 2 s ≈ 1800 appels/h par provider actif (jusqu'à ×2 si
  `VISION_AI_PROVIDER=claude` ET `OCR_PROVIDER=claude` en même temps), en plus
  des appels à la demande si micro. Monter l'intervalle, ou repasser
  `VISION_AI_PROVIDER`/`OCR_PROVIDER` en `local` pour limiter la facture.
- **Image** : l'OCR et la scène à la demande capturent un still PLEINE
  RÉSOLUTION (`HQ_CAPTURE_ENABLED=1`, `src/vision/camera.py`), réduit à
  `CLAUDE_IMG_MAX_PX` avant envoi → régler `CLAUDE_IMG_MAX_PX=1568` (lisible,
  ~2400 tokens ≈ $0.005/lecture en sonnet-5). La boucle continue reste en
  640×480 quelle que soit cette valeur (jamais agrandie → coût inchangé).
- **STT/TTS restent hors Claude** : Whisper via Groq (gratuit) + edge-tts
  (gratuit). `STT_MODEL=whisper-large-v3` = meilleure transcription darija.
- Vérifier le coût réel dans les logs : chaque appel imprime
  `Claude <tag> usage: in=... cache_read=... out=...`.
