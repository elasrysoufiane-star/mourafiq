"""
Thread conversation — boucle d'écoute micro et dispatch des commandes.

Mot de réveil (« مرافق ») : tant qu'on n'est pas dans la fenêtre de suivi,
l'appareil ignore tout ce qui ne contient pas son nom → évite les fausses
commandes (écho, bruit, hallucinations Whisper). Après une commande exécutée,
une fenêtre de WAKE_FOLLOWUP_WINDOW secondes permet d'enchaîner sans répéter
le mot. WAKE_WORD_ENABLED=0 rétablit l'écoute continue.

Fix 1 : conversation_active n'est PAS géré ici (uniquement dans parler()).
"""
import time

from config.settings import WAKE_WORD_ENABLED, WAKE_FOLLOWUP_WINDOW
from src.core import state
from src.audio.listener import reconnaitre_voix
from src.audio.speaker import parler
from src.conversation.intents import process_command, contient_wake, retirer_wake


def mode_conversation() -> None:
    """
    Boucle principale du thread conversation.
    Écoute → (mot de réveil) → transcription → dispatch → répète.
    S'arrête si process_command() retourne False.
    """
    print('Mode Conversation démarré...')
    active_until = 0.0  # fin de la fenêtre de suivi (timestamp)

    while True:
        try:
            commande = reconnaitre_voix()

            if not commande:
                continue

            # Hors fenêtre de suivi → exiger le mot de réveil.
            if WAKE_WORD_ENABLED and time.time() >= active_until:
                if not contient_wake(commande):
                    print('(ignoré — pas de mot de réveil)')
                    continue
                commande = retirer_wake(commande)
                if not commande:
                    # Juste « مرافق » → accuse réception et ouvre la fenêtre.
                    parler('نعم؟')
                    active_until = time.time() + WAKE_FOLLOWUP_WINDOW
                    continue

            print(f'Commande: {commande}')
            continuer = process_command(commande)

            if not continuer:
                # Arrêt vocal → toute l'app s'arrête (AutoScene compris),
                # pas seulement l'écoute — voir app.main().
                state.stop_event.set()
                break

            # Rouvre la fenêtre de suivi après chaque commande exécutée.
            active_until = time.time() + WAKE_FOLLOWUP_WINDOW

        except Exception as e:
            # Sécurité : libérer l'event si exception pendant parler()
            state.conversation_active.clear()
            print(f'Erreur conversation: {e}')
            time.sleep(1)
