import time

import state
from groq_service import reconnaitre_voix
from intents import process_command


def mode_conversation():
    """
    Thread conversation — écoute le micro en boucle et route chaque commande.
    Fix 1 : conversation_active n'est PAS activé ici.
    La vision tourne librement pendant l'écoute micro.
    conversation_active est géré uniquement par parler() pendant la sortie audio.
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
            # Sécurité : libérer l'event si une exception survient pendant parler()
            state.conversation_active.clear()
            print(f'Erreur conversation: {e}')
            time.sleep(1)
