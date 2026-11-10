"""Passo 2: gera as questões em todas as condições.

- condição "com": cada gerador recebe o trecho, com o MESMO prompt e as MESMAS
  validações da ferramenta (backend/app/llm.py).   -> QP1
- condição "sem": os geradores principais recebem só o título do material e o
  tema do fragmento.                                  -> QP2

Uma questão por chamada. Pode ser interrompido e rodado de novo: continua de onde parou.
Saída: dados/questoes.jsonl
"""
import argparse
import random
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import comum
import config
import prompts

ARQ = "questoes.jsonl"
FINAIS = {"ok", "pulou", "descartada", "json_invalido"}  # status que não são refeitos
_parar = {"claude_code": threading.Event(), "ollama": threading.Event(), "gemini": threading.Event()}


def itens_planejados(frags: list[dict], modelos: list[str]) -> list[dict]:
    itens = []
    for f in frags:
        for nome in modelos:
            cfg = config.GERADORES[nome]
            itens.append({"gerador": nome, "condicao": "com", "frag": f})
            if cfg["principal"]:
                itens.append({"gerador": nome, "condicao": "sem", "frag": f})
    return itens


def montar_prompt(item: dict) -> str:
    llm = comum.backend()["llm"]
    f = item["frag"]
    if item["condicao"] == "com":  # idêntico a llm.pergunta_llm()
        return llm.PROMPT_PERGUNTA_CONTEUDO.format(diretrizes=llm.DIRETRIZES_QUESTAO,
                                                   conteudo=llm.remover_referencias(f["trecho"])[:6000])
    return prompts.PROMPT_SEM_TRECHO.format(diretrizes=prompts.DIRETRIZES_SEM_TRECHO,
                                            titulo=f["titulo_material"], tema=f["tema"])


def schema_da_condicao(cond: str) -> dict:
    """Na condição sem trecho não existe "pular": o prompt não o pede, e o schema
    obrigatório faria o modelo preenchê-lo à toa."""
    llm = comum.backend()["llm"]
    if cond == "com":
        return llm.SCHEMA_QUESTAO
    campos = [c for c in llm.SCHEMA_QUESTAO["required"] if c != "pular"]
    return {"type": "OBJECT", "properties": {c: llm.SCHEMA_QUESTAO["properties"][c] for c in campos},
            "required": campos, "propertyOrdering": campos}


def validar(reg: dict, dados: dict, trecho: str) -> dict:
    """Aplica as validações da ferramenta e preenche o registro."""
    llm = comum.backend()["llm"]
    if reg["condicao"] == "sem":
        dados.pop("pular", None)  # não faz parte da condição sem trecho
    try:
        q = llm._questao_valida(dados, trecho)  # mesmas validações da ferramenta
    except llm.TrechoSemConteudo as e:
        reg["status"] = "pulou" if "avaliável" in str(e) else "descartada"
        reg["erro"] = str(e)
        reg["pergunta"] = dados.get("pergunta")
        return reg
    except ValueError as e:
        reg["status"] = "json_invalido"
        reg["erro"] = str(e)
        return reg
    if len(q.get("opcoes", [])) != 4:
        reg["status"] = "json_invalido"
        reg["erro"] = f"{len(q.get('opcoes', []))} alternativas"
        return reg
    reg.update(status="ok", erro=None, pergunta=q["pergunta"], opcoes=q["opcoes"], correta=int(q["correta"]),
               justificativa=q.get("justificativa", ""), explicacoes=q.get("explicacoes", []),
               evidencia=q.get("evidencia", ""))
    return reg


def revalidar_sem_trecho(frags: dict) -> int:
    """Corrige questões sem trecho descartadas por "pular" (defeito do schema nas
    primeiras chamadas), reaproveitando a resposta original gravada, sem nova chamada."""
    n = 0
    for reg in comum.ultimos_por_id(comum.ler_jsonl(ARQ)).values():
        if reg.get("condicao") == "sem" and reg.get("status") == "pulou" and reg.get("bruto"):
            try:
                dados = comum.extrair_json(reg["bruto"])
            except (ValueError, TypeError):
                continue
            novo = validar(dict(reg, revalidado=True), dados, frags[reg["fragmento_id"]]["trecho"])
            comum.anexar_jsonl(ARQ, novo)
            n += 1
    return n


def gerar(item: dict) -> dict:
    llm = comum.backend()["llm"]
    nome, cond, f = item["gerador"], item["condicao"], item["frag"]
    cfg = config.GERADORES[nome]
    reg = {"id": f"{nome}|{cond}|{f['id']}", "fragmento_id": f["id"], "material": f["material"],
           "gerador": nome, "provedor": cfg["provedor"], "acesso": cfg["acesso"], "condicao": cond,
           "data_hora": comum.agora(), "tentativas": 0, "tokens_in": 0, "tokens_out": 0,
           "latencia_s": 0.0, "latencia_api_s": None, "status": "erro", "erro": None, "bruto": None}
    prompt = montar_prompt(item)
    dados = None
    for _ in range(2):  # como a ferramenta: até 2 tentativas se o JSON vier inválido
        if _parar[cfg["acesso"]].is_set():
            raise comum.LimiteAtingido("parado")
        with comum.SEMAFOROS[cfg["acesso"]]:
            r = comum.chamar(cfg, prompt, schema_da_condicao(cond))
        reg["tentativas"] += 1
        reg["tokens_in"] = (reg["tokens_in"] or 0) + (r["tokens_in"] or 0)
        reg["tokens_out"] = (reg["tokens_out"] or 0) + (r["tokens_out"] or 0)
        reg["latencia_s"] += r["latencia_s"]
        reg["latencia_api_s"] = r["latencia_api_s"]
        reg["modelo_exato"] = r["modelo_exato"]
        reg["bruto"] = r["texto"]
        try:
            dados = comum.extrair_json(r["texto"])
            break
        except (ValueError, TypeError):
            dados = None
    if dados is None:
        reg["status"] = "json_invalido"
        return reg
    return validar(reg, dados, f["trecho"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", nargs="*", default=list(config.GERADORES), help="gera só para estes geradores")
    ap.add_argument("--limite", type=int, default=0, help="no máximo N itens nesta execução (teste)")
    args = ap.parse_args()
    random.seed(config.SEMENTE)

    frags = [f for f in comum.ultimos_por_id(comum.ler_jsonl("fragmentos.jsonl")).values() if f.get("tema")]
    if not frags:
        print("Rode antes o passo 1 (1_sortear_fragmentos.py).")
        return 1
    corrigidas = revalidar_sem_trecho({f["id"]: f for f in frags})
    if corrigidas:
        print(f"Questões sem trecho reavaliadas (campo 'pular' indevido): {corrigidas}")
    feitos = {i for i, r in comum.ultimos_por_id(comum.ler_jsonl(ARQ)).items() if r["status"] in FINAIS}
    pendentes = [it for it in itens_planejados(frags, args.modelos)
                 if f"{it['gerador']}|{it['condicao']}|{it['frag']['id']}" not in feitos]
    if args.limite:
        pendentes = pendentes[:args.limite]
    total = len(itens_planejados(frags, list(config.GERADORES)))
    print(f"Questões planejadas: {total} | já feitas: {len(feitos)} | nesta execução: {len(pendentes)}")

    feitos_agora = 0
    workers = 1 + config.CLAUDE_PARALELO + 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futuros = {pool.submit(gerar, it): it for it in pendentes}
        for fut in as_completed(futuros):
            it = futuros[fut]
            acesso = config.GERADORES[it["gerador"]]["acesso"]
            try:
                reg = fut.result()
            except comum.LimiteAtingido as e:
                if not _parar[acesso].is_set():
                    print(f"\n*** Limite de uso em {acesso}: {e}\n*** As chamadas desse acesso param; rode de novo mais tarde.")
                _parar[acesso].set()
                continue
            except Exception as e:  # noqa: BLE001  (registra e segue; será refeito na próxima execução)
                reg = {"id": f"{it['gerador']}|{it['condicao']}|{it['frag']['id']}", "status": "erro",
                       "erro": f"{type(e).__name__}: {e}", "gerador": it["gerador"], "condicao": it["condicao"],
                       "fragmento_id": it["frag"]["id"], "data_hora": comum.agora()}
                if "Ollama indisponível" in str(e):
                    _parar["ollama"].set()
                traceback.print_exc(limit=1)
            comum.anexar_jsonl(ARQ, reg)
            feitos_agora += 1
            print(f"[{len(feitos) + feitos_agora}/{total}] {reg['id']}: {reg['status']}"
                  + (f" ({reg.get('latencia_s', 0):.0f} s)" if reg.get("latencia_s") else ""), flush=True)

    finais = sum(1 for r in comum.ultimos_por_id(comum.ler_jsonl(ARQ)).values() if r["status"] in FINAIS)
    print(f"\nConcluídas: {finais}/{total}." + ("" if finais == total else " Rode de novo para continuar."))
    return 0 if finais == total else 2


if __name__ == "__main__":
    sys.exit(main())
