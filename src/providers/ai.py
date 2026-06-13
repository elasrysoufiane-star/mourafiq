"""
Provider IA — NLP et réponses en darija.
Routage selon AI_PROVIDER dans config/settings.py.

Providers supportés :
  groq   — LLaMA 3.1-8b-instant (défaut, gratuit)
  openai — GPT-4o-mini (futur, fallback groq si clé absente)

Ne jamais importer groq_client au niveau module — import lazy
pour rester testable sur Windows sans matériel.
"""
from config.settings import AI_PROVIDER, OPENAI_API_KEY


def get_ai_response(question: str) -> str:
    """Envoie la question au provider AI configuré, retourne la réponse en darija."""
    if AI_PROVIDER == 'openai':
        if not OPENAI_API_KEY:
            print('OPENAI_API_KEY manquant — fallback Groq')
        else:
            return _openai_darija(question)
    return _groq_darija(question)


def _groq_darija(question: str) -> str:
    from src.ai.groq_client import groq_darija
    return groq_darija(question)


def _openai_darija(question: str) -> str:
    print('OpenAI AI provider: non encore implémenté — fallback Groq')
    from src.ai.groq_client import groq_darija
    return groq_darija(question)
