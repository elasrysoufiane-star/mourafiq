"""
Mémoire de conversation roulante, PARTAGÉE entre le chat et la vision à la
demande. Garde les derniers tours (user/assistant) en TEXTE et les renvoie à
Claude comme contexte → permet une vraie discussion avec questions de suivi :
« وزيد على اليسار؟ », « عاود », « زيدني تفاصيل », sans tout réexpliquer.

Pourquoi en texte seulement :
  • les images ne sont jamais stockées (coût en tokens + une vieille image
    n'est plus valable) ; la description textuelle, elle, reste utile pour
    enchaîner — « زيدني تفاصيل » s'appuie sur ce que Claude vient de décrire.

La boucle auto de fond (describe_scene hq=False) N'alimente PAS la mémoire —
narration continue, pas un tour de dialogue, coût continu — voir remember=
dans claude_client. Elle tourne en permanence, avec ou sans micro.

Pairage strict user→assistant : un tour n'est enregistré que si les DEUX textes
sont présents. L'historique commence donc toujours par 'user' et alterne, comme
l'exige l'API Claude.

Thread-safe : le thread conversation et le thread auto-scene peuvent tous deux
appeler Claude. Importable sur Windows sans matériel (threading + config).
"""
import threading

from config.settings import CONV_MEMORY_TURNS

_lock = threading.Lock()
_history = []  # liste de {'role': 'user'|'assistant', 'content': str}


def get_history() -> list:
    """Copie de l'historique (messages role/content), prête à préfixer le
    message courant dans l'appel Claude. Commence toujours par un tour 'user'."""
    with _lock:
        return list(_history)


def add_turn(user_text: str, assistant_text: str) -> None:
    """Enregistre un échange et tronque aux CONV_MEMORY_TURNS derniers tours.
    Les deux textes doivent être non vides (pairage strict → alternance valide).
    Désactivé si CONV_MEMORY_TURNS <= 0."""
    if CONV_MEMORY_TURNS <= 0 or not user_text or not assistant_text:
        return
    with _lock:
        _history.append({'role': 'user', 'content': user_text})
        _history.append({'role': 'assistant', 'content': assistant_text})
        # 2 messages par tour → surplus toujours pair, l'historique reste
        # aligné (commence par 'user').
        surplus = len(_history) - CONV_MEMORY_TURNS * 2
        if surplus > 0:
            del _history[:surplus]


def reset() -> None:
    """Vide la mémoire (nouvelle session / changement de contexte)."""
    with _lock:
        _history.clear()
