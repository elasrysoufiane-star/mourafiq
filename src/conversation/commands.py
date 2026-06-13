"""
Thread conversation — boucle d'écoute micro et dispatch des commandes.

Fix 1 : conversation_active n'est PAS géré ici.
La vision tourne librement pendant l'écoute micro.
conversation_active est uniquement activé/désactivé dans parler() (speaker.py).
"""
import time

from src.core import state
from src.audio.listener import reconnaitre_voix
from src.conversation.intents import process_command


def mode_conversation() -> None:
    """
    Boucle principale du thread conversation.
    Écoute → transcription → dispatch → répète.
    S'arrête si process_command() retourne False.
    """
    print('Mode Conversation démarré...')

    while True:
        try:
            commande = reconnaitre_voix()

            if not commande:
                continue

            print(f'Commande: {commande}')
            continuer = process_command(commande)

            if not continuer:
                break

        except Exception as e:
            # Sécurité : libérer l'event si exception pendant parler()
            state.conversation_active.clear()
            print(f'Erreur conversation: {e}')
            time.sleep(1)
