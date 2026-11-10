"""Funções comuns da coleta: acesso ao backend do Âncora, chamadas aos modelos
(Ollama, Claude Code, Gemini), leitura/escrita de JSONL com retomada."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime

import config
import prompts


class LimiteAtingido(RuntimeError):
    """Limite de uso do provedor (ex.: limite da assinatura do Claude). Rode de novo mais tarde."""


# ---------------------------------------------------------------- backend
_app = None


def backend():
    """Importa os módulos do backend (rag, llm) usando o mesmo ChromaDB da ferramenta."""
    global _app
    if _app is None:
        sys.path.insert(0, str(config.BACKEND))
        os.chdir(config.BACKEND)  # o backend usa caminhos relativos (./chroma_data, ./ava.db)
        from app import llm, rag  # noqa: E402
        _app = {"llm": llm, "rag": rag}
    return _app


def titulos_materiais() -> dict[int, str]:
    import sqlite3

    con = sqlite3.connect(f"file:{config.BACKEND / 'ava.db'}?mode=ro", uri=True)
    return dict(con.execute("select id, titulo from materiais").fetchall())


# ---------------------------------------------------------------- JSONL
_trava_arquivo = threading.Lock()


def ler_jsonl(nome: str) -> list[dict]:
    caminho = config.DADOS / nome
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def anexar_jsonl(nome: str, registro: dict) -> None:
    config.DADOS.mkdir(parents=True, exist_ok=True)
    with _trava_arquivo, open(config.DADOS / nome, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def ultimos_por_id(registros: list[dict]) -> dict[str, dict]:
    """Se um item foi registrado mais de uma vez (nova tentativa), vale o último."""
    return {r["id"]: r for r in registros}


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def extrair_json(texto: str) -> dict:
    texto = re.sub(r"^```(?:json)?|```$", "", (texto or "").strip(), flags=re.M).strip()
    bruto = re.search(r"\{.*\}", texto, re.S)
    if not bruto:
        raise ValueError("resposta sem JSON")
    return json.loads(bruto.group(0))


# ---------------------------------------------------------------- modelos
def chamar_ollama(modelo: str, prompt: str, schema: dict | None = None) -> dict:
    corpo = {
        "model": modelo,
        "messages": [{"role": "system", "content": prompts.SISTEMA}, {"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": config.TEMPERATURA},
    }
    if schema:
        corpo["format"] = _schema_json(schema)
    req = urllib.request.Request(
        f"{config.OLLAMA_URL}/api/chat", data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=config.OLLAMA_TIMEOUT_S) as r:
            dados = json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama indisponível em {config.OLLAMA_URL}: {e}") from None
    return {
        "texto": dados.get("message", {}).get("content", ""),
        "tokens_in": dados.get("prompt_eval_count"),
        "tokens_out": dados.get("eval_count"),
        "latencia_s": round(time.perf_counter() - inicio, 3),
        "latencia_api_s": round((dados.get("total_duration") or 0) / 1e9, 3) or None,
        "modelo_exato": dados.get("model", modelo),
    }


def _schema_json(schema: dict) -> dict:
    """Converte o schema no formato do Gemini (OBJECT, STRING...) para JSON Schema (Ollama)."""
    tipos = {"OBJECT": "object", "STRING": "string", "INTEGER": "integer", "BOOLEAN": "boolean", "ARRAY": "array"}
    saida = {}
    for chave, valor in schema.items():
        if chave == "type":
            saida["type"] = tipos.get(valor, valor)
        elif chave == "properties":
            saida["properties"] = {k: _schema_json(v) for k, v in valor.items()}
        elif chave == "items":
            saida["items"] = _schema_json(valor)
        elif chave == "required":
            saida["required"] = valor
    return saida


_SINAIS_LIMITE = re.compile(r"usage limit|limit reached|rate limit|limite de uso|hit your limit|5-hour limit|weekly limit|overloaded", re.I)
_dir_vazio = tempfile.mkdtemp(prefix="ancora_coleta_")  # sem CLAUDE.md nem arquivos do projeto
_suporta_system_prompt = [True]


def chamar_claude(modelo: str, prompt: str) -> dict:
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("comando `claude` não encontrado no PATH (instale/abra o Claude Code)")
    base = [exe, "-p", "--model", modelo, "--output-format", "json", "--max-turns", "1"]
    args = base + (["--system-prompt", prompts.SISTEMA] if _suporta_system_prompt[0] else [])
    # Sem chaves de API no ambiente: o Claude Code usa o login da assinatura.
    # (O .env do backend pode ter ANTHROPIC_API_KEY, que faria o Claude Code cobrar pela API.)
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")}
    inicio = time.perf_counter()
    proc = subprocess.run(args, input=prompt, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=config.CLAUDE_TIMEOUT_S, cwd=_dir_vazio, env=env)
    if proc.returncode != 0 and _suporta_system_prompt[0] and "system-prompt" in (proc.stderr + proc.stdout):
        _suporta_system_prompt[0] = False  # versão antiga do Claude Code: segue sem o parâmetro
        return chamar_claude(modelo, prompt)
    latencia = round(time.perf_counter() - inicio, 3)
    saida = proc.stdout.strip()
    try:
        dados = json.loads(saida)
    except json.JSONDecodeError:
        dados = {"result": saida, "is_error": proc.returncode != 0}
    texto = dados.get("result") or ""
    if dados.get("is_error") or proc.returncode != 0:
        erro = f"{texto} {proc.stderr}".strip()
        if _SINAIS_LIMITE.search(erro):
            raise LimiteAtingido(erro[:300])
        raise RuntimeError(f"Claude Code falhou: {erro[:300]}")
    uso = dados.get("usage") or {}
    tokens_in = sum(uso.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return {
        "texto": texto,
        "tokens_in": tokens_in or None,
        "tokens_out": uso.get("output_tokens"),
        "latencia_s": latencia,
        "latencia_api_s": round((dados.get("duration_api_ms") or 0) / 1000, 3) or None,
        # nome completo do modelo que respondeu (o apelido "sonnet" etc. aponta para a versão atual)
        "modelo_exato": ",".join(dados.get("modelUsage") or {}) or modelo,
    }


def chamar_gemini(modelo: str, prompt: str, schema: dict | None = None) -> dict:
    llm = backend()["llm"]
    inicio = time.perf_counter()
    try:
        texto = llm._gemini(prompt, 2000, True, schema, modelo=modelo)
    except llm.LimiteLLM as e:
        raise LimiteAtingido(str(e)) from None
    return {"texto": texto, "tokens_in": None, "tokens_out": None,
            "latencia_s": round(time.perf_counter() - inicio, 3), "latencia_api_s": None, "modelo_exato": modelo}


def chamar(cfg: dict, prompt: str, schema: dict | None = None) -> dict:
    if cfg["acesso"] == "ollama":
        return chamar_ollama(cfg["modelo"], prompt, schema)
    if cfg["acesso"] == "claude_code":
        return chamar_claude(cfg["modelo"], prompt)
    if cfg["acesso"] == "gemini":
        return chamar_gemini(cfg["modelo"], prompt, schema)
    raise ValueError(f"acesso desconhecido: {cfg['acesso']}")


# Quantas chamadas simultâneas por forma de acesso (o Ollama roda uma por vez).
SEMAFOROS = {
    "ollama": threading.Semaphore(1),
    "claude_code": threading.Semaphore(config.CLAUDE_PARALELO),
    "gemini": threading.Semaphore(1),
}
