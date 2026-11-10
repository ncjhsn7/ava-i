"""Passo 3: o avaliador único (Claude Opus 5.5) julga cada questão gerada.

O juiz recebe só o trecho, a questão e o gabarito; não sabe qual modelo gerou
nem a condição. As questões são julgadas em ordem aleatória (semente fixa).
Pode ser interrompido e rodado de novo. Saída: dados/julgamentos.jsonl
"""
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import comum
import config
import prompts

ARQ = "julgamentos.jsonl"
LETRAS = "ABCD"
VALIDOS = {
    "c1": {"sim", "parcialmente", "nao"},
    "c2": {"sim", "nao"},
    "c4": {"sim", "nao"},
    "c5": {"lembrar", "compreender", "aplicar_ou_superior"},
}


def normalizar(v) -> str:
    return (str(v).strip().lower().replace("não", "nao").replace("ã", "a")
            .replace(" ", "_").replace("aplicar_ou_superior", "aplicar_ou_superior"))


def validar(d: dict) -> dict:
    out = {}
    for c, ok in VALIDOS.items():
        v = normalizar(d.get(c, ""))
        if c == "c5" and v.startswith("aplicar"):
            v = "aplicar_ou_superior"
        if v not in ok:
            raise ValueError(f"{c} inválido: {d.get(c)!r}")
        out[c] = v
    c3 = int(d.get("c3"))
    if not 0 <= c3 <= 3:
        raise ValueError(f"c3 fora de 0..3: {c3}")
    out["c3"] = c3
    out["justificativa"] = str(d.get("justificativa", ""))[:600]
    return out


def montar_prompt(q: dict, frag: dict) -> str:
    llm = comum.backend()["llm"]
    alternativas = "\n".join(f"{LETRAS[i]}) {op}" for i, op in enumerate(q["opcoes"]))
    return prompts.PROMPT_JUIZ.format(trecho=llm.remover_referencias(frag["trecho"])[:6000],
                                      enunciado=q["pergunta"], alternativas=alternativas,
                                      gabarito=LETRAS[q["correta"]])


def julgar(q: dict, frag: dict) -> dict:
    prompt = montar_prompt(q, frag)
    reg = {"id": q["id"], "juiz": config.JUIZ["modelo"], "data_hora": comum.agora(),
           "tentativas": 0, "status": "erro"}
    for _ in range(2):
        with comum.SEMAFOROS[config.JUIZ["acesso"]]:
            r = comum.chamar(config.JUIZ, prompt)
        reg["tentativas"] += 1
        reg.update(tokens_in=r["tokens_in"], tokens_out=r["tokens_out"], latencia_s=r["latencia_s"], bruto=r["texto"])
        try:
            reg.update(validar(comum.extrair_json(r["texto"])))
            reg["status"] = "ok"
            return reg
        except (ValueError, TypeError) as e:
            reg["erro"] = str(e)
    return reg


def main() -> int:
    frags = comum.ultimos_por_id(comum.ler_jsonl("fragmentos.jsonl"))
    questoes = [q for q in comum.ultimos_por_id(comum.ler_jsonl("questoes.jsonl")).values() if q["status"] == "ok"]
    feitos = {i for i, r in comum.ultimos_por_id(comum.ler_jsonl(ARQ)).items() if r["status"] == "ok"}
    pendentes = [q for q in questoes if q["id"] not in feitos]
    random.Random(config.SEMENTE).shuffle(pendentes)  # ordem aleatória: o juiz não vê blocos por modelo
    print(f"Questões válidas: {len(questoes)} | já julgadas: {len(feitos)} | nesta execução: {len(pendentes)}")

    parar = False
    n = 0
    with ThreadPoolExecutor(max_workers=config.CLAUDE_PARALELO) as pool:
        futuros = {pool.submit(julgar, q, frags[q["fragmento_id"]]): q for q in pendentes}
        for fut in as_completed(futuros):
            if parar:
                continue
            try:
                reg = fut.result()
            except comum.LimiteAtingido as e:
                print(f"\n*** Limite de uso do Claude: {e}\n*** Rode este passo de novo mais tarde.")
                parar = True
                for f in futuros:
                    f.cancel()
                continue
            except Exception as e:  # noqa: BLE001
                reg = {"id": futuros[fut]["id"], "status": "erro", "erro": f"{type(e).__name__}: {e}"}
            comum.anexar_jsonl(ARQ, reg)
            n += 1
            print(f"[{len(feitos) + n}/{len(questoes)}] {reg['id']}: {reg['status']}"
                  + (f" c1={reg['c1']} c2={reg['c2']} c3={reg['c3']} c4={reg['c4']}" if reg["status"] == "ok" else f" {reg.get('erro', '')}"),
                  flush=True)

    ok = sum(1 for r in comum.ultimos_por_id(comum.ler_jsonl(ARQ)).values() if r["status"] == "ok")
    print(f"\nJulgadas: {ok}/{len(questoes)}." + ("" if ok == len(questoes) else " Rode de novo para continuar."))
    return 0 if ok == len(questoes) else 2


if __name__ == "__main__":
    sys.exit(main())
