"""
Provider IA — NLP et réponses en darija.
Routage selon AI_PROVIDER dans config/settings.py.

Providers supportés :
  groq   — LLaMA 3.1-8b-instant (défaut, gratuit)
  claude — Claude (Anthropic), réponses darija. Tenté en premier si la clé est
           présente ; ne bascule vers Groq qu'en cas d'erreur réseau/connexion
           (pas Internet) — pas pour une autre raison (quota, clé invalide…
           ces erreurs remontent normalement).
  openai — GPT-4o-mini, réponses darija. Même logique que claude : tenté en
           premier si clé présente, fallback Groq uniquement sur erreur réseau.

Ne jamais importer groq_client/claude_client au niveau module — import lazy
pour rester testable sur Windows sans matériel.
"""
import socket
import urllib.error

from config.settings import AI_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY

# Erreurs réseau/connexion uniquement — pas d'Internet ou hôte injoignable.
# anthropic.APIConnectionError hérite de ces causes mais on capte large ici
# via le type de base pour rester sans dépendance dure à anthropic.
_NETWORK_ERRORS = (socket.gaierror, ConnectionError, TimeoutError, OSError,
                    urllib.error.URLError)


def get_ai_response(question: str) -> str:
    """Envoie la question au provider AI configuré, retourne la réponse en darija."""
    if AI_PROVIDER == 'claude':
        if not ANTHROPIC_API_KEY:
            print('ANTHROPIC_API_KEY manquant — fallback Groq')
        else:
            try:
                return _claude_darija(question)
            except _NETWORK_ERRORS as e:
                print(f'Claude inaccessible (pas d\'Internet ?) — fallback Groq: {e}')
            except Exception as e:
                # anthropic lève ses propres exceptions (APIConnectionError, etc.)
                # qui ne sont pas forcément des sous-classes des types réseau
                # stdlib ci-dessus — on filtre sur le nom pour rester sans
                # dépendance dure au SDK anthropic.
                if 'Connection' in type(e).__name__ or 'Timeout' in type(e).__name__:
                    print(f'Claude inaccessible (pas d\'Internet ?) — fallback Groq: {e}')
                else:
                    raise
        return _groq_darija(question)
    if AI_PROVIDER == 'openai':
        if not OPENAI_API_KEY:
            print('OPENAI_API_KEY manquant — fallback Groq')
        else:
            try:
                return _openai_darija(question)
            except _NETWORK_ERRORS as e:
                print(f'GPT-4o inaccessible (pas d\'Internet ?) — fallback Groq: {e}')
            except Exception as e:
                if 'Connection' in type(e).__name__ or 'Timeout' in type(e).__name__:
                    print(f'GPT-4o inaccessible (pas d\'Internet ?) — fallback Groq: {e}')
                else:
                    raise
        return _groq_darija(question)
    return _groq_darija(question)


def _groq_darija(question: str) -> str:
    from src.ai.groq_client import groq_darija
    return groq_darija(question)


def _claude_darija(question: str) -> str:
    from src.ai.claude_client import claude_darija
    return claude_darija(question)


def _openai_darija(question: str) -> str:
    from src.ai.openai_client import gpt4o_darija
    return gpt4o_darija(question)
