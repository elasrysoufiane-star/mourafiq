"""
Nettoyage du texte avant synthèse vocale.

Claude (et parfois Groq) renvoie du Markdown : gras `**...**`, titres `###`,
listes `- ...`. edge-tts/gTTS le lisent LITTÉRALEMENT (« étoile étoile »,
« tiret ») ou marquent des pauses bizarres — insupportable pour un malvoyant
qui n'a que l'audio. On retire ces marqueurs et on transforme les sauts de
ligne en pauses naturelles avant de parler.

Fonction pure (regex seulement) → testable sur Windows sans matériel.
"""
import re

# Puces de liste en début de ligne : « - texte », « * texte », « • texte ».
_BULLET_LINE = re.compile(r'(?m)^[ \t]*[-*•·–—]+[ \t]+')
# Titres Markdown : « ## Titre ».
_HEADER = re.compile(r'(?m)^[ \t]*#{1,6}[ \t]*')
# Marqueurs d'emphase/code restants n'importe où : * _ ` # ~
_EMPHASIS = re.compile(r'[*_`#~]+')
# Plusieurs sauts de ligne → une seule pause forte.
_MULTI_NL = re.compile(r'\n{2,}')
# Espaces multiples (après nettoyage) → un seul.
_MULTI_SPACE = re.compile(r'[ \t]{2,}')


def clean_for_speech(texte: str) -> str:
    """Retire le Markdown et convertit les retours ligne en pauses parlées.
    Renvoie le texte tel quel s'il est vide/None (jamais d'exception)."""
    if not texte:
        return texte
    t = _BULLET_LINE.sub('', texte)   # « - الضوء » → « الضوء »
    t = _HEADER.sub('', t)            # « ## ... » → « ... »
    t = _EMPHASIS.sub('', t)          # « **مهم** » → « مهم »
    t = _MULTI_NL.sub('. ', t)        # paragraphe → pause forte
    t = t.replace('\n', '، ')         # ligne suivante → courte pause
    t = _MULTI_SPACE.sub(' ', t)
    return t.strip(' ،.')


# Fins de phrase (latin + arabe). La virgule n'en fait pas partie : couper à
# une virgule laisserait une idée en suspens.
_FIN_PHRASE = ('.', '!', '؟', '?', '…')


def couper_phrase_incomplete(texte: str) -> str:
    """Coupe la DERNIÈRE phrase si elle est incomplète — les réponses de la
    boucle AutoScene sont plafonnées par max_tokens et tombent souvent en plein
    mot (« خلفو جدار أ ») : le TTS lisait des phrases cassées. On garde jusqu'au
    dernier signe de fin de phrase. S'il n'y en a aucun, texte inchangé
    (mieux vaut une phrase imparfaite que le silence)."""
    if not texte:
        return texte
    t = texte.rstrip()
    if t.endswith(_FIN_PHRASE):
        return t
    coupe = max(t.rfind(c) for c in _FIN_PHRASE)
    return t[:coupe + 1] if coupe > 0 else t
