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
AUTO_DESCRIBE_INTERVAL=5
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
- **Le levier de coût n°1 est `AUTO_DESCRIBE_INTERVAL`** (mode sans micro) :
  5 s ≈ 720 appels/h. Le mode avec micro ne paie qu'à la demande.
- **Image** : caméra 640×480 → `CLAUDE_IMG_MAX_PX=768` ne réduit jamais rien ;
  monter cette valeur ne sert à rien sans monter la résolution caméra.
- **STT/TTS restent hors Claude** : Whisper via Groq (gratuit) + edge-tts
  (gratuit). `STT_MODEL=whisper-large-v3` = meilleure transcription darija.
- Vérifier le coût réel dans les logs : chaque appel imprime
  `Claude <tag> usage: in=... cache_read=... out=...`.
