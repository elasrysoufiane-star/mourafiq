"""
Interface Groq LLaMA — génère des réponses courtes en darija marocaine.
Modèle : llama-3.1-8b-instant
3 tentatives avec backoff exponentiel en cas de quota dépassé (HTTP 429).
"""
import time

from src.core import state

# Prompt système fixe — assure des réponses en darija marocaine, phrase unique
_SYSTEM_PROMPT = (
    'أنت مساعد ذكي للمكفوفين في المغرب. '
    'تتكلم الدارجة المغربية فقط. '
    'ردودك قصيرة جدا — جملة واحدة فقط. '
    'أمثلة: كاين كرسي قدامك / سير على اليمين بعد 50 متر / مكتوب صيدلية الأمل'
)


def groq_darija(question: str) -> str:
    """
    Envoie une question à LLaMA et retourne une réponse en darija (≤ 80 tokens).
    Retourne un message d'erreur en darija si toutes les tentatives échouent.
    """
    for tentative in range(3):
        try:
            response = state.groq_client.chat.completions.create(
                model='llama-3.1-8b-instant',
                messages=[
                    {'role': 'system', 'content': _SYSTEM_PROMPT},
                    {'role': 'user',   'content': question},
                ],
                max_tokens=80,
                temperature=0.3,
            )
            reponse = response.choices[0].message.content.strip()
            print(f'Groq darija: {reponse}')
            return reponse

        except Exception as e:
            if '429' in str(e) and tentative < 2:
                attente = 5 * (2 ** tentative)
                print(f'Quota LLaMA, attente {attente}s...')
                time.sleep(attente)
            else:
                print(f'Erreur Groq: {e}')
                return 'عفوا ماقدرتش نفهم'

    return 'عفوا ماقدرتش نفهم'
