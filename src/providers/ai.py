"""
Provider IA — NLP et réponses en darija.
Routage selon AI_PROVIDER dans config/settings.py.

Providers supportés :
  groq   — LLaMA 3.1-8b-instant (défaut, gratuit)
  claude — Claude (Anthropic), réponses darija (payant, fallback groq si clé absente)
  openai — GPT-4o-mini (futur, fallback groq si clé absente)
  ollama — service local Ollama via API HTTP

Ne jamais importer groq_client/claude_client au niveau module — import lazy
pour rester testable sur Windows sans matériel.
"""
from config.settings import (
    AI_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY, OLLAMA_URL, OLLAMA_MODEL,
)


def get_ai_response(question: str) -> str:
    """Envoie la question au provider AI configuré, retourne la réponse en darija.
    Claude indisponible (clé absente OU échec après retries) → fallback Groq :
    l'assistant garde toujours la parole."""
    if AI_PROVIDER == 'claude':
        if not ANTHROPIC_API_KEY:
            print('ANTHROPIC_API_KEY manquant — fallback Groq')
        else:
            try:
                return _claude_darija(question)
            except Exception as e:
                print(f'Claude indisponible ({e}) — fallback Groq')
    if AI_PROVIDER == 'openai':
        if not OPENAI_API_KEY:
            print('OPENAI_API_KEY manquant — fallback Groq')
        else:
            return _openai_darija(question)
    if AI_PROVIDER == 'ollama':
        return _ollama_darija(question)
    return _groq_darija(question)


def _groq_darija(question: str) -> str:
    from src.ai.groq_client import groq_darija
    return groq_darija(question)


def _ollama_darija(question: str) -> str:
    import json
    import urllib.request
    import urllib.error

    payload = json.dumps({
        'model': OLLAMA_MODEL,
        'prompt': question,
        'stream': False,
    }).encode('utf-8')

    request = urllib.request.Request(
        f'{OLLAMA_URL}/api/generate',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode('utf-8')
            result = json.loads(body)
            answer = result.get('response', '').strip()
            if answer:
                print(f'Ollama darija: {answer}')
                return answer
            print('Ollama: réponse vide, fallback Groq')
    except urllib.error.HTTPError as e:
        print(f'Erreur Ollama HTTP: {e.code} {e.reason}')
    except urllib.error.URLError as e:
        print(f'Erreur Ollama URL: {e.reason}')
    except Exception as e:
        print(f'Erreur Ollama: {e}')

    return _groq_darija(question)


def _claude_darija(question: str) -> str:
    from src.ai.claude_client import claude_darija
    return claude_darija(question)


def _openai_darija(question: str) -> str:
    print('OpenAI AI provider: non encore implémenté — fallback Groq')
    from src.ai.groq_client import groq_darija
    return groq_darija(question)
