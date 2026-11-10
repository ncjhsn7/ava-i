"""Passo 1: sorteia os fragmentos (semente fixa) e obtém o tema de cada um.

Saída: dados/fragmentos.jsonl. O sorteio é feito UMA vez; rodar de novo só
completa os temas que faltam. Use --refazer apenas antes de iniciar a geração.
"""
import argparse
import random
import sys
from concurrent.futures import ThreadPoolExecutor

import comum
import config
import prompts

ARQ = "fragmentos.jsonl"


def sortear() -> list[dict]:
    """Disciplinas fora de COMPLETAR entram com todos os fragmentos úteis; COMPLETAR é
    sorteada (semente fixa) até fechar TOTAL_FRAGMENTOS."""
    rag = comum.backend()["rag"]
    titulos = comum.titulos_materiais()
    candidatos = {}
    for rot, ids in config.MATERIAIS.items():
        candidatos[rot] = [
            {"id": f"{rot}-{mid}-{i:03d}", "material_id": mid, "material": rot,
             "titulo_material": titulos.get(mid, rot), "indice": i, "trecho": ch, "tema": None}
            for mid in ids for i, ch in enumerate(rag.bons_chunks(rag.obter_chunks(mid)))]
    frags = [f for rot, fs in candidatos.items() if rot != config.COMPLETAR for f in fs]
    falta = config.TOTAL_FRAGMENTOS - len(frags)
    pool = candidatos[config.COMPLETAR]
    if falta > len(pool):
        raise SystemExit(f"{config.COMPLETAR} tem só {len(pool)} fragmentos úteis; precisa de {falta}.")
    if falta < 0:
        raise SystemExit(f"As disciplinas fixas já somam {len(frags)} fragmentos, mais que {config.TOTAL_FRAGMENTOS}.")
    frags += sorted(random.Random(config.SEMENTE).sample(pool, falta), key=lambda f: f["id"])
    for rot in config.MATERIAIS:
        print(f"  {rot}: {sum(f['material'] == rot for f in frags)} fragmentos")
    return frags


def obter_tema(frag: dict) -> dict:
    with comum.SEMAFOROS[config.MODELO_TEMA["acesso"]]:
        r = comum.chamar(config.MODELO_TEMA, prompts.PROMPT_TEMA.format(trecho=frag["trecho"][:3000]))
    frag = dict(frag)
    frag["tema"] = str(comum.extrair_json(r["texto"]).get("tema", "")).strip()[:80]
    return frag


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refazer", action="store_true", help="apaga e refaz o sorteio (só antes da geração!)")
    args = ap.parse_args()
    caminho = config.DADOS / ARQ
    if args.refazer and caminho.exists():
        if comum.ler_jsonl("questoes.jsonl"):
            print("Já existem questões geradas; refazer o sorteio invalidaria a coleta. Abortado.")
            return 1
        caminho.unlink()
    frags = list(comum.ultimos_por_id(comum.ler_jsonl(ARQ)).values())
    if not frags:
        frags = sortear()
        for f in frags:
            comum.anexar_jsonl(ARQ, f)
        print(f"Selecionados {len(frags)} fragmentos de {len(config.MATERIAIS)} disciplinas (semente {config.SEMENTE}).")

    faltando = [f for f in frags if not f.get("tema")]
    print(f"Temas a obter: {len(faltando)}")
    erros = 0
    with ThreadPoolExecutor(max_workers=config.CLAUDE_PARALELO) as pool:
        for fut in [pool.submit(obter_tema, f) for f in faltando]:
            try:
                f = fut.result()
                comum.anexar_jsonl(ARQ, f)  # a versão com tema substitui a anterior (último registro vale)
            except comum.LimiteAtingido as e:
                print(f"Limite de uso atingido: {e}\nRode este passo de novo mais tarde.")
                return 2
            except Exception as e:  # noqa: BLE001
                erros += 1
                print(f"  erro no tema: {e}")
    total = sum(1 for f in comum.ultimos_por_id(comum.ler_jsonl(ARQ)).values() if f.get("tema"))
    print(f"Fragmentos com tema: {total}/{len(frags)}" + (f" ({erros} erros; rode de novo)" if erros else ""))
    return 0 if total == len(frags) else 1


if __name__ == "__main__":
    sys.exit(main())
