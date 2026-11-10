"""Passo 4: monta a amostra cega para a avaliação humana (autor e orientador).

Sorteia AMOSTRA_HUMANA questões da condição "com", em número igual por gerador,
entre as já julgadas. Os avaliadores NÃO veem o modelo nem a nota do juiz.

Saídas (em dados/):
- amostra_humana_autor.csv e amostra_humana_orientador.csv: planilhas para preencher
  (abrem no Excel; não são sobrescritas se já existirem)
- amostra_humana_chave.csv: código -> questão (NÃO abra antes de terminar a avaliação)
"""
import csv
import random
import sys

import comum
import config

COLUNAS = ["codigo", "trecho", "enunciado", "A", "B", "C", "D", "gabarito",
           "c1_ancoragem (sim/parcialmente/nao)", "c2_correcao (sim/nao)", "c3_distratores (0-3)",
           "c4_clareza (sim/nao)", "c5_bloom (lembrar/compreender/aplicar)", "observacao"]


def main() -> int:
    chave_arq = config.DADOS / "amostra_humana_chave.csv"
    if chave_arq.exists():
        print("A amostra já foi sorteada (amostra_humana_chave.csv existe). Nada a fazer.")
        return 0
    llm = comum.backend()["llm"]
    frags = comum.ultimos_por_id(comum.ler_jsonl("fragmentos.jsonl"))
    todas = comum.ultimos_por_id(comum.ler_jsonl("questoes.jsonl"))
    esperadas = len(frags) * sum(2 if c["principal"] else 1 for c in config.GERADORES.values())
    finais = sum(1 for q in todas.values() if q["status"] in {"ok", "pulou", "descartada", "json_invalido"})
    nao_julgadas = sum(1 for q in todas.values() if q["status"] == "ok") - sum(
        1 for r in comum.ultimos_por_id(comum.ler_jsonl("julgamentos.jsonl")).values() if r["status"] == "ok")
    if finais < esperadas or nao_julgadas > 0:
        print(f"Coleta incompleta ({finais}/{esperadas} geradas, {nao_julgadas} sem julgamento). "
              "A amostra só é sorteada no fim, para não favorecer os primeiros fragmentos.")
        return 1
    julgadas = {i for i, r in comum.ultimos_por_id(comum.ler_jsonl("julgamentos.jsonl")).items() if r["status"] == "ok"}
    questoes = [q for q in comum.ultimos_por_id(comum.ler_jsonl("questoes.jsonl")).values()
                if q["status"] == "ok" and q["condicao"] == "com" and q["id"] in julgadas]
    rnd = random.Random(config.SEMENTE + 7)
    por_modelo = config.AMOSTRA_HUMANA // len(config.GERADORES)
    amostra = []
    for nome in config.GERADORES:
        candidatas = sorted((q for q in questoes if q["gerador"] == nome), key=lambda q: q["id"])
        if len(candidatas) < por_modelo:
            print(f"Ainda faltam questões julgadas de {nome} ({len(candidatas)}/{por_modelo}). Termine os passos 2 e 3.")
            return 1
        amostra += rnd.sample(candidatas, por_modelo)
    rnd.shuffle(amostra)

    linhas, chave = [], []
    for i, q in enumerate(amostra, 1):
        cod = f"H{i:02d}"
        chave.append({"codigo": cod, "id": q["id"]})
        linhas.append([cod, llm.remover_referencias(frags[q["fragmento_id"]]["trecho"]), q["pergunta"], *q["opcoes"],
                       "ABCD"[q["correta"]], "", "", "", "", "", ""])
    for quem in ("autor", "orientador"):
        arq = config.DADOS / f"amostra_humana_{quem}.csv"
        if arq.exists():
            continue
        with open(arq, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig + ";" abre direto no Excel
            w = csv.writer(f, delimiter=";")
            w.writerow(COLUNAS)
            w.writerows(linhas)
    with open(chave_arq, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["codigo", "id"])
        w.writeheader()
        w.writerows(chave)
    print(f"Amostra de {len(amostra)} questões ({por_modelo} por gerador) criada em dados/:")
    print("  amostra_humana_autor.csv e amostra_humana_orientador.csv -> cada um preenche o seu, sem conversar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
