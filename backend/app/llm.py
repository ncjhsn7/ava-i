import json
import re
from . import config

PROMPT = """Você é um gerador de avaliações formativas para um Ambiente Virtual de Aprendizagem.
A partir do trecho de material didático abaixo, gere exatamente 1 questão de múltipla escolha em português, com 4 alternativas, ancorada exclusivamente no trecho.

TRECHO-FONTE:
{trecho}
{contexto}
Responda SOMENTE com um JSON válido no formato:
{{"pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "..."}}"""


def _gerar_mock(trecho: str) -> dict:
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", trecho) if len(f.strip()) > 40]
    base = frases[0] if frases else trecho[:160]
    correta = base[:140] + ("…" if len(base) > 140 else "")
    return {
        "pergunta": "De acordo com o trecho lido, qual afirmação está correta?",
        "opcoes": [
            correta,
            "O trecho afirma exatamente o oposto dessa ideia.",
            "O trecho não aborda esse conceito em nenhum momento.",
            "O trecho apresenta o conceito apenas como hipótese refutada.",
        ],
        "correta": 0,
        "justificativa": "Alternativa extraída literalmente do trecho-fonte (modo de demonstração sem LLM).",
    }


def _gerar_anthropic(trecho: str, contexto: str) -> dict:
    import anthropic

    cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    ctx = f"\nCONTEXTO ADICIONAL (cenário expandido):\n{contexto}\n" if contexto else "\n"
    msg = cliente.messages.create(
        model=config.LLM_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": PROMPT.format(trecho=trecho, contexto=ctx)}],
    )
    texto = msg.content[0].text
    bruto = re.search(r"\{.*\}", texto, re.S)
    return json.loads(bruto.group(0)) if bruto else _gerar_mock(trecho)


def gerar_questao(trecho: str, contexto: str = "") -> dict:
    if config.LLM_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        try:
            return _gerar_anthropic(trecho, contexto)
        except Exception:
            return _gerar_mock(trecho)
    return _gerar_mock(trecho)
