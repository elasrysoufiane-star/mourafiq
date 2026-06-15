"""
Chat interactif en Darija — test manuel de l'IA.

Usage (Windows, depuis la racine du projet) :
    $env:GROQ_API_KEY = "gsk_..."
    python tests/chat_darija.py

Options :
    python tests/chat_darija.py --voix     # active edge-tts (nécessite pip install edge-tts)
    python tests/chat_darija.py --ollama   # utilise Ollama local au lieu de Groq
"""
import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _init_groq():
    from groq import Groq
    from src.core import state
    from config.settings import GROQ_API_KEY
    state.groq_client = Groq(api_key=GROQ_API_KEY)


def _get_reponse(question: str, provider: str) -> str:
    if provider == 'ollama':
        os.environ.setdefault('AI_PROVIDER', 'ollama')
        from src.providers.ai import get_ai_response
        return get_ai_response(question)
    # Groq direct
    from src.ai.groq_client import groq_darija
    return groq_darija(question)


def _jouer_voix(texte: str) -> None:
    try:
        import asyncio
        import edge_tts
        import tempfile
        import subprocess

        voice = 'ar-MA-JamalNeural'

        async def _synth():
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                path = f.name
            c = edge_tts.Communicate(texte, voice)
            await c.save(path)
            return path

        path = asyncio.run(_synth())
        if sys.platform == 'win32':
            os.startfile(path)
        else:
            subprocess.Popen(['mpg123', '-q', path])
    except ImportError:
        print('  [voix désactivée — pip install edge-tts]')
    except Exception as e:
        print(f'  [erreur voix: {e}]')


def main():
    parser = argparse.ArgumentParser(description='Chat Darija interactif')
    parser.add_argument('--voix',   action='store_true', help='Activer edge-tts')
    parser.add_argument('--ollama', action='store_true', help='Utiliser Ollama local')
    args = parser.parse_args()

    # --ollama flag OU variable d'environnement AI_PROVIDER=ollama
    provider = 'ollama' if (args.ollama or os.environ.get('AI_PROVIDER') == 'ollama') else 'groq'

    if provider == 'groq' and not os.environ.get('GROQ_API_KEY'):
        print('ERREUR: GROQ_API_KEY manquant.')
        print('  $env:GROQ_API_KEY = "gsk_..."')
        sys.exit(1)

    if provider == 'groq':
        _init_groq()
    elif os.environ.get('GROQ_API_KEY'):
        _init_groq()  # init Groq quand même pour le fallback Ollama → Groq

    print(f'=== Chat Darija [{provider.upper()}{"  +voix" if args.voix else ""}] ===')
    print('Ctrl+C pour quitter\n')

    while True:
        try:
            question = input('Anta  : ').strip()
        except (KeyboardInterrupt, EOFError):
            print('\nBslama!')
            break

        if not question:
            continue

        try:
            reponse = _get_reponse(question, provider)
            print(f'Mourafiq: {reponse}\n')
            if args.voix:
                _jouer_voix(reponse)
        except Exception as e:
            print(f'Erreur: {e}\n')


if __name__ == '__main__':
    main()
