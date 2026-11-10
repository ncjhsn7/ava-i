"""Configuração da coleta do Cap. 5 (QP1 e QP2).

Tudo que define o experimento fica aqui: materiais, semente, modelos e caminhos.
Mude só antes de começar a coleta; depois disso, mudar invalida a comparação.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"
DADOS = Path(__file__).resolve().parent / "dados"
RESULTADOS = Path(__file__).resolve().parent / "resultados"

SEMENTE = 2026
TOTAL_FRAGMENTOS = 90

# Materiais agrupados por disciplina: rótulo -> ids dos PDFs no Âncora.
# As disciplinas com poucos fragmentos úteis entram com TODOS os seus fragmentos;
# a disciplina em COMPLETAR é sorteada até fechar TOTAL_FRAGMENTOS.
MATERIAIS = {
    "IA": [1, 2],          # Inteligência Artificial: Redes Neurais 2 e 3
    "CP": [7, 8],          # Computação Paralela: openmp-nicolas, Modelagem de Programas Paralelos v2
    "SD": [6, 5, 4, 3],    # Sistemas Distribuídos: Broadcast partes 1 a 4
}
COMPLETAR = "SD"

# Geradores. "principal": também gera sem o trecho (QP2).
# acesso: "ollama" (local), "claude_code" (assinatura, `claude -p`) ou "gemini" (API).
GERADORES = {
    "gpt-oss-20b":       {"acesso": "ollama",      "modelo": "gpt-oss:20b",       "provedor": "OpenAI",    "principal": True},
    # No Claude Code, use os apelidos (sonnet/haiku/opus); o nome exato de cada resposta fica registrado.
    "claude-sonnet-5.5": {"acesso": "claude_code", "modelo": "sonnet", "provedor": "Anthropic", "principal": True},
    "claude-haiku-5.5":  {"acesso": "claude_code", "modelo": "haiku",  "provedor": "Anthropic", "principal": False},
    # Desligado (cota gratuita lenta). Para reativar, descomente ANTES da coleta:
    # "gemini-flash":    {"acesso": "gemini",      "modelo": "gemini-2.5-flash",  "provedor": "Google",    "principal": True},
}

# Avaliador único (LLM-as-a-judge), maior que todos os geradores.
JUIZ = {"acesso": "claude_code", "modelo": "opus"}

# Modelo que dá o "tema" do fragmento para a condição sem trecho.
# Não pode ser um dos modelos comparados na QP2.
MODELO_TEMA = {"acesso": "claude_code", "modelo": "haiku"}

TEMPERATURA = 0.8            # a mesma da ferramenta (o Claude Code não permite fixar)
OLLAMA_URL = "http://localhost:11434"
OLLAMA_TIMEOUT_S = 900       # o gpt-oss-20b pode levar minutos por chamada em CPU
CLAUDE_TIMEOUT_S = 300
CLAUDE_PARALELO = 3          # chamadas simultâneas ao Claude Code

AMOSTRA_HUMANA = 30          # dividida igualmente entre os geradores
BOOTSTRAP_REAMOSTRAGENS = 10000
