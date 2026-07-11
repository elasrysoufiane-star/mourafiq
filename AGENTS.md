# AGENTS.md

**Mourafiq (مرافق)** — assistant IA pour malvoyants au Maroc (Raspberry Pi 4, darija marocaine).

Toute la documentation agent (architecture, providers, configuration, threads,
tests, décisions) vit dans **[CLAUDE.md](CLAUDE.md)** — source unique, tenue à
jour à chaque changement notable. Le journal des décisions (le POURQUOI) est
dans `.claude/memory/decisions.md`.

Points d'entrée rapides :
- Lancer : `python3 main.py` (matériel Pi requis — caméra + micro)
- Tests (sans matériel) : `pytest tests/ -v`
- Config : `config/settings.py` (défauts) + `.env` (clés API uniquement)
