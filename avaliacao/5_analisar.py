"""Passo 5: calcula os resultados da QP1 e da QP2 e gera as tabelas do Cap. 5.

Saídas (em resultados/):
- tabelas.tex           tabelas prontas para o LaTeX (booktabs)
- resumo.md             números principais em texto, para escrever os parágrafos
- questoes_avaliadas.csv  uma linha por questão, com o julgamento (vai para o repositório)

Regras:
- Questão aceitável: c1 = sim, c2 = sim, c4 = sim e c3 >= 2.
- Chamadas que não produziram questão (JSON inválido, pulou, descartada) contam
  como NÃO aceitáveis: é o que o estudante receberia (nenhuma questão útil).
"""
import csv
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations

import comum
import config

FINAIS = {"ok", "pulou", "descartada", "json_invalido"}
STOP = set("a o e de da do das dos para por com sem que se na no nas nos um uma uns umas em ao aos as os ou como "
           "mais menos entre sobre sob ate apos antes cada qual quais este esta estes estas esse essa essas esses "
           "isso aquilo seu sua seus suas pela pelo the and of to in is are be by an as at it this that".split())


# ============================================================ estatística
def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centro - meia), min(1.0, centro + meia)


def mcnemar_exato(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cauda = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * cauda)


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    ordem = sorted(range(m), key=lambda i: ps[i])
    ajust, maior = [0.0] * m, 0.0
    for pos, i in enumerate(ordem):
        maior = max(maior, min(1.0, (m - pos) * ps[i]))
        ajust[i] = maior
    return ajust


def bootstrap_diff(x: list[int], y: list[int], reps: int, semente: int) -> tuple[float, float]:
    rnd = random.Random(semente)
    n = len(x)
    difs = []
    for _ in range(reps):
        idx = [rnd.randrange(n) for _ in range(n)]
        difs.append(sum(x[i] - y[i] for i in idx) / n)
    difs.sort()
    return difs[int(0.025 * reps)], difs[int(0.975 * reps) - 1]


def qui2_sf_3gl(x: float) -> float:
    """P(X > x) para qui-quadrado com 3 graus de liberdade (posições A-D)."""
    return math.erfc(math.sqrt(x / 2)) + math.sqrt(2 * x / math.pi) * math.exp(-x / 2)


def kappa(a: list, b: list) -> float | None:
    pares = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pares) < 2:
        return None
    n = len(pares)
    po = sum(x == y for x, y in pares) / n
    ca, cb = Counter(x for x, _ in pares), Counter(y for _, y in pares)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def faixa_kappa(k: float | None) -> str:
    if k is None:
        return "n/d"
    for lim, nome in [(0, "pobre"), (0.20, "fraca"), (0.40, "razoável"), (0.60, "moderada"), (0.80, "substancial")]:
        if k <= lim:
            return nome
    return "quase perfeita"


def mediana_iqr(vals: list[float]) -> str:
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return "n/d"
    if len(vals) < 4:
        return br(statistics.median(vals), 1)
    q = statistics.quantiles(vals, n=4)
    return f"{br(statistics.median(vals), 1)} [{br(q[0], 1)}--{br(q[2], 1)}]"


# ============================================================ formatação
def br(x: float, casas: int = 1) -> str:
    return "n/d" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{casas}f}".replace(".", ",")


def pct_ic(k: int, n: int) -> str:
    p, lo, hi = wilson(k, n)
    return "n/d" if n == 0 else f"{br(100 * p)} [{br(100 * lo)}; {br(100 * hi)}]"


def p_fmt(p: float) -> str:
    return "$<$0,001" if p < 0.001 else br(p, 3)


def nome_modelo(g: str) -> str:
    return {"gpt-oss-20b": "gpt-oss-20b", "claude-sonnet-5.5": "Claude Sonnet 5.5",
            "claude-haiku-5.5": "Claude Haiku 5.5", "gemini-flash": "Gemini Flash"}.get(g, g)


def tabela(label: str, legenda: str, colunas: str, cabecalho: list[str], linhas: list[list[str]], nota: str,
           largo: bool = False) -> str:
    """largo=True: reduz a tabela à largura do texto (\\resizebox, pacote graphicx)."""
    corpo = "\n".join(" & ".join(c.replace("×", "$\\times$") for c in l) + r" \\" for l in linhas)
    tab = (f"\\begin{{tabular}}{{{colunas}}}\n\\toprule\n{' & '.join(cabecalho)} \\\\\n\\midrule\n{corpo}\n"
           f"\\bottomrule\n\\end{{tabular}}")
    if largo:
        tab = f"\\resizebox{{\\textwidth}}{{!}}{{%\n{tab}}}"
    return (f"\\begin{{table}}[htbp]\n\\centering\n\\caption{{{legenda}}}\n\\label{{{label}}}\n\\small\n"
            f"{tab}\n\\par\\smallskip\\footnotesize {nota}\n\\end{{table}}\n")


# ============================================================ dados
def aceitavel(c: dict) -> bool:
    return c.get("c1") == "sim" and c.get("c2") == "sim" and c.get("c4") == "sim" and (c.get("c3") or 0) >= 2


def carregar():
    frags = comum.ultimos_por_id(comum.ler_jsonl("fragmentos.jsonl"))
    questoes = comum.ultimos_por_id(comum.ler_jsonl("questoes.jsonl"))
    julg = {i: r for i, r in comum.ultimos_por_id(comum.ler_jsonl("julgamentos.jsonl")).items() if r["status"] == "ok"}
    linhas, faltando = [], Counter()
    for f in frags.values():
        for g, cfg in config.GERADORES.items():
            for cond in (["com", "sem"] if cfg["principal"] else ["com"]):
                qid = f"{g}|{cond}|{f['id']}"
                q = questoes.get(qid)
                if not q or q["status"] not in FINAIS:
                    faltando["nao gerada"] += 1
                    continue
                if q["status"] == "ok" and qid not in julg:
                    faltando["nao julgada"] += 1
                    continue
                j = julg.get(qid, {})
                linhas.append({**q, "trecho": f["trecho"], "provedor": cfg["provedor"],
                               "c1": j.get("c1"), "c2": j.get("c2"), "c3": j.get("c3"), "c4": j.get("c4"),
                               "c5": j.get("c5"), "justificativa_juiz": j.get("justificativa"),
                               "aceitavel": q["status"] == "ok" and aceitavel(j)})
    return frags, linhas, faltando


def ler_humanos() -> dict[str, dict[str, dict]]:
    chave_arq = config.DADOS / "amostra_humana_chave.csv"
    if not chave_arq.exists():
        return {}
    with open(chave_arq, encoding="utf-8") as f:
        chave = {r["codigo"]: r["id"] for r in csv.DictReader(f)}
    resultado = {}
    for quem in ("autor", "orientador"):
        arq = config.DADOS / f"amostra_humana_{quem}.csv"
        if not arq.exists():
            continue
        avals = {}
        with open(arq, encoding="utf-8-sig") as f:
            leitor = csv.reader(f, delimiter=";")
            next(leitor, None)
            for lin in leitor:
                if len(lin) < 13 or not lin[0].strip() or not lin[8].strip():
                    continue
                norm = lambda s: s.strip().lower().replace("não", "nao").replace("ã", "a")  # noqa: E731
                c5 = norm(lin[12])
                avals[chave[lin[0].strip()]] = {
                    "c1": norm(lin[8]), "c2": norm(lin[9]), "c3": int(lin[10]) if lin[10].strip().isdigit() else None,
                    "c4": norm(lin[11]), "c5": "aplicar_ou_superior" if c5.startswith("aplicar") else c5}
        if avals:
            resultado[quem] = avals
    return resultado


def termos(texto: str) -> list[str]:
    return [t for t in re.findall(r"[a-zà-ÿ0-9]{3,}", (texto or "").lower()) if t not in STOP]


# ============================================================ análises
def main() -> int:
    frags, linhas, faltando = carregar()
    if not linhas:
        print("Sem dados. Rode os passos 1 a 3.")
        return 1
    config.RESULTADOS.mkdir(parents=True, exist_ok=True)
    tex, md = [], ["# Resultados da coleta (gerado por 5_analisar.py)\n"]
    if faltando:
        md.append(f"**ATENÇÃO: coleta incompleta** ({dict(faltando)}). Os números abaixo são parciais.\n")
        print(f"ATENÇÃO: coleta incompleta: {dict(faltando)}")

    por = defaultdict(list)
    for l in linhas:
        por[(l["gerador"], l["condicao"])].append(l)
    geradores = list(config.GERADORES)
    principais = [g for g in geradores if config.GERADORES[g]["principal"]]

    # ---------- QP1: qualidade por modelo
    linhas_t = []
    md.append("## QP1 — questões aceitáveis por modelo (condição com trecho)\n")
    for g in geradores:
        ls = por[(g, "com")]
        n = len(ls)
        cont = {
            "c1": sum(l["c1"] == "sim" for l in ls), "c2": sum(l["c2"] == "sim" for l in ls),
            "c3": sum((l["c3"] or 0) >= 2 for l in ls), "c4": sum(l["c4"] == "sim" for l in ls),
            "ac": sum(l["aceitavel"] for l in ls)}
        linhas_t.append([nome_modelo(g), str(n)] + [pct_ic(cont[k], n) for k in ("c1", "c2", "c3", "c4", "ac")])
        p, lo, hi = wilson(cont["ac"], n)
        md.append(f"- {nome_modelo(g)}: {br(100 * p)}% aceitáveis [{br(100 * lo)}; {br(100 * hi)}] (n={n}) — "
                  f"critério de 80%: {'ATINGIDO' if p >= 0.8 else 'não atingido'}")
    tex.append(tabela("tab:qp1-principal",
                      "Qualidade das questões geradas com o trecho, por modelo, segundo o avaliador automático",
                      "lcccccc", ["Modelo", "$n$", "C1 Ancor.", "C2 Correção", "C3 $\\geq$ 2", "C4 Clareza", "Aceitável"],
                      linhas_t, "Valores em porcentagem, com IC de 95\\% de Wilson entre colchetes. Chamadas que não "
                      "produziram questão válida contam como não atendendo a nenhum critério. Fonte: elaborada pelo autor.", largo=True))

    # ---------- QP1: comparações pareadas entre modelos
    def pareado(ga, ca, gb, cb, campo="aceitavel"):
        a = {l["fragmento_id"]: int(bool(l[campo] if campo == "aceitavel" else l[campo] == "sim")) for l in por[(ga, ca)]}
        b = {l["fragmento_id"]: int(bool(l[campo] if campo == "aceitavel" else l[campo] == "sim")) for l in por[(gb, cb)]}
        comuns = sorted(set(a) & set(b))
        x, y = [a[i] for i in comuns], [b[i] for i in comuns]
        bb = sum(1 for i, j in zip(x, y) if i and not j)
        cc = sum(1 for i, j in zip(x, y) if j and not i)
        dif = (sum(x) - sum(y)) / len(x) if x else float("nan")
        ic = bootstrap_diff(x, y, config.BOOTSTRAP_REAMOSTRAGENS, config.SEMENTE) if x else (float("nan"),) * 2
        return dif, ic, bb, cc, mcnemar_exato(bb, cc), len(x)

    pares = list(combinations(geradores, 2))
    res = [pareado(a, "com", b, "com") for a, b in pares]
    ps = holm([r[4] for r in res])
    linhas_t = []
    md.append("\n## QP1 — comparações entre modelos (aceitável; McNemar exato + Holm)\n")
    for (a, b), r, p in zip(pares, res, ps):
        dif, ic, bb, cc, _, n = r
        linhas_t.append([f"{nome_modelo(a)} $-$ {nome_modelo(b)}", br(100 * dif), f"[{br(100 * ic[0])}; {br(100 * ic[1])}]",
                         f"{bb} / {cc}", p_fmt(p)])
        md.append(f"- {nome_modelo(a)} − {nome_modelo(b)}: {br(100 * dif)} p.p. [{br(100 * ic[0])}; {br(100 * ic[1])}], "
                  f"b/c={bb}/{cc}, p(Holm)={p_fmt(p)} (n={n} pares)")
    tex.append(tabela("tab:qp1-comparacoes", "Comparações pareadas da proporção de questões aceitáveis entre os modelos",
                      "lcccc", ["Comparação", "Diferença (p.p.)", "IC 95\\%", "$b$ / $c$", "$p$ (Holm)"], linhas_t,
                      f"IC por \\textit{{bootstrap}} pareado ({config.BOOTSTRAP_REAMOSTRAGENS} reamostragens). $b$: aceitável "
                      "só no primeiro modelo; $c$: só no segundo. Teste de McNemar exato com correção de Holm. "
                      "Fonte: elaborada pelo autor.", largo=True))

    # ---------- QP2: com vs sem trecho
    linhas_t, md2 = [], ["\n## QP2 — com trecho vs. sem trecho (mesmo modelo)\n"]
    for campo, rotulo in (("aceitavel", "Aceitável"), ("c1", "C1 Ancoragem")):
        res = [pareado(g, "com", g, "sem", campo) for g in principais]
        ps = holm([r[4] for r in res])
        for g, r, p in zip(principais, res, ps):
            dif, ic, bb, cc, _, n = r
            k_com = sum(1 for l in por[(g, "com")] if (l["aceitavel"] if campo == "aceitavel" else l["c1"] == "sim"))
            k_sem = sum(1 for l in por[(g, "sem")] if (l["aceitavel"] if campo == "aceitavel" else l["c1"] == "sim"))
            linhas_t.append([nome_modelo(g), rotulo, br(100 * k_com / max(1, len(por[(g, 'com')]))),
                             br(100 * k_sem / max(1, len(por[(g, 'sem')]))), br(100 * dif),
                             f"[{br(100 * ic[0])}; {br(100 * ic[1])}]", f"{bb} / {cc}", p_fmt(p)])
            md2.append(f"- {nome_modelo(g)} / {rotulo}: com {br(100 * k_com / max(1, len(por[(g, 'com')])))}% × sem "
                       f"{br(100 * k_sem / max(1, len(por[(g, 'sem')])))}% → diferença {br(100 * dif)} p.p. "
                       f"[{br(100 * ic[0])}; {br(100 * ic[1])}], p(Holm)={p_fmt(p)} → "
                       f"{'SIGNIFICATIVA' if p < 0.05 else 'não significativa'} (α=0,05)")
    md += md2
    tex.append(tabela("tab:qp2", "Efeito do trecho: questões geradas com e sem o trecho pelo mesmo modelo",
                      "llcccccc", ["Modelo", "Medida", "Com trecho (\\%)", "Sem trecho (\\%)", "Dif. (p.p.)", "IC 95\\%", "$b$ / $c$", "$p$ (Holm)"],
                      linhas_t, "Condição: com trecho, o modelo recebeu o fragmento do material; sem trecho, recebeu apenas o título do material e o tema do fragmento. Na condição sem o trecho, a ancoragem (C1) é avaliada em relação ao fragmento sorteado. "
                      "Holm aplicado separadamente a cada medida. Fonte: elaborada pelo autor.", largo=True))

    # ---------- por material
    linhas_t = []
    for g in geradores:
        linha = [nome_modelo(g)]
        for rot in config.MATERIAIS:
            ls = [l for l in por[(g, "com")] if l["material"] == rot]
            linha.append(pct_ic(sum(l["aceitavel"] for l in ls), len(ls)))
        linhas_t.append(linha)
    tex.append(tabela("tab:qp1-material", "Proporção de questões aceitáveis por modelo e por disciplina",
                      "l" + "c" * len(config.MATERIAIS), ["Modelo"] + [f"{r} ($n$={sum(1 for f in frags.values() if f['material'] == r)})" for r in config.MATERIAIS], linhas_t,
                      "Valores em porcentagem, com IC de 95\\% de Wilson. Fonte: elaborada pelo autor."))

    # ---------- Bloom
    linhas_t = []
    for g in geradores:
        for cond in (["com", "sem"] if g in principais else ["com"]):
            ls = [l for l in por[(g, cond)] if l["c5"]]
            n = len(ls)
            cnt = Counter(l["c5"] for l in ls)
            linhas_t.append([nome_modelo(g), f"{cond} trecho", str(n)] +
                            [br(100 * cnt[k] / n) if n else "n/d" for k in ("lembrar", "compreender", "aplicar_ou_superior")])
    tex.append(tabela("tab:bloom", "Nível cognitivo das questões (taxonomia revisada de Bloom), por modelo e condição",
                      "llcccc", ["Modelo", "Condição", "$n$", "Lembrar", "Compreender", "Aplicar ou sup."], linhas_t,
                      "Porcentagem das questões válidas. Condição: com trecho, o modelo recebeu o fragmento do material; sem trecho, recebeu apenas o título do material e o tema do fragmento. Fonte: elaborada pelo autor."))

    # ---------- métricas automáticas
    embed = None
    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        embed = DefaultEmbeddingFunction()
    except Exception:  # noqa: BLE001
        pass
    linhas_t, linhas_custo = [], []
    md.append("\n## Métricas automáticas\n")
    for g in geradores:
        for cond in (["com", "sem"] if g in principais else ["com"]):
            ls = por[(g, cond)]
            ok = [l for l in ls if l["status"] == "ok"]
            falhas = Counter(l["status"] for l in ls if l["status"] != "ok")
            pos = Counter(l["correta"] for l in ok)
            n_ok = len(ok)
            qui = sum((pos[i] - n_ok / 4) ** 2 / (n_ok / 4) for i in range(4)) if n_ok else 0
            mais_longa = sum(1 for l in ok if len(l["opcoes"][l["correta"]]) > max(len(o) for i, o in enumerate(l["opcoes"]) if i != l["correta"]))
            ancor = [sum(t in set(termos(l["trecho"])) for t in termos(l["opcoes"][l["correta"]])) / max(1, len(termos(l["opcoes"][l["correta"]])))
                     for l in ok]
            dup = "n/d"
            if embed and cond == "com" and n_ok > 1:
                dup = 0
                for rot in config.MATERIAIS:
                    grupo = [l["pergunta"] for l in ok if l["material"] == rot]
                    if len(grupo) < 2:
                        continue
                    vs = [list(map(float, v)) for v in embed(grupo)]
                    norm = [math.sqrt(sum(x * x for x in v)) or 1 for v in vs]
                    dup += sum(1 for i, j in combinations(range(len(vs)), 2)
                               if sum(a * b for a, b in zip(vs[i], vs[j])) / (norm[i] * norm[j]) > 0.9)
            linhas_t.append([
                nome_modelo(g), f"{cond} trecho", f"{len(ls) - n_ok}/{len(ls)}",
                "/".join(str(pos[i]) for i in range(4)) + f" ({p_fmt(qui2_sf_3gl(qui)) if n_ok else 'n/d'})",
                br(100 * mais_longa / n_ok) if n_ok else "n/d",
                br(statistics.mean(ancor), 2) if ancor else "n/d", str(dup)])
            linhas_custo.append([nome_modelo(g), f"{cond} trecho", mediana_iqr([l.get("tokens_in") for l in ls]),
                                 mediana_iqr([l.get("tokens_out") for l in ls]), mediana_iqr([l.get("latencia_s") for l in ls])])
            md.append(f"- {nome_modelo(g)} ({cond}): falhas {dict(falhas) or 0}; posição A/B/C/D {[pos[i] for i in range(4)]}; "
                      f"correta mais longa {br(100 * mais_longa / n_ok) if n_ok else 'n/d'}% (esperado ≈25%); "
                      f"ancoragem lexical média {br(statistics.mean(ancor), 2) if ancor else 'n/d'}; duplicatas {dup}; "
                      f"latência {mediana_iqr([l.get('latencia_s') for l in ls])} s")
    tex.append(tabela("tab:qp1-auto", "Falhas e vieses das questões, por modelo e condição",
                      "llccccc", ["Modelo", "Condição", "Falhas", "Posição A/B/C/D ($p$)", "Mais longa (\\%)", "Ancor. lex.",
                                  "Dupl."], linhas_t,
                      "Falhas: chamadas sem questão válida (JSON inválido, recusa ou enunciado descartado). $p$: qui-quadrado "
                      "de aderência à distribuição uniforme. Mais longa: correta estritamente mais longa (esperado $\\approx$ 25\\%). "
                      "Ancor. lex.: fração média dos termos da alternativa correta presentes no trecho. Dupl.: pares de "
                      "enunciados do mesmo material com similaridade de cosseno acima de 0,9. Fonte: elaborada pelo autor.",
                      largo=True))
    tex.append(tabela("tab:qp1-custo", "Tokens e latência por questão, por modelo e condição",
                      "llccc", ["Modelo", "Condição", "Tokens de entrada", "Tokens de saída", "Latência (s)"], linhas_custo,
                      "Mediana [intervalo interquartil]. As latências do Claude Code incluem o tempo da própria ferramenta, e a do "
                      "gpt-oss-20b depende do computador do autor; por isso só são comparáveis entre modelos com a mesma forma "
                      "de acesso. Fonte: elaborada pelo autor."))

    # ---------- concordância (amostra humana)
    humanos = ler_humanos()
    juiz = {l["id"]: l for l in linhas if l["status"] == "ok"}
    if humanos:
        md.append("\n## Concordância (kappa de Cohen) na amostra humana\n")
        medidas = {
            "Aceitável": lambda c: aceitavel(c) if c.get("c1") else None,
            "C1": lambda c: c.get("c1"), "C2": lambda c: c.get("c2"),
            "C3 $\\geq$ 2": lambda c: (c["c3"] >= 2) if c.get("c3") is not None else None, "C4": lambda c: c.get("c4")}
        fontes = [(q, humanos[q]) for q in ("autor", "orientador") if q in humanos]
        comparacoes = [(f"{q} × juiz", av, {i: juiz[i] for i in av if i in juiz}) for q, av in fontes]
        if len(fontes) == 2:
            comparacoes.insert(0, ("autor × orientador", fontes[0][1], fontes[1][1]))
        linhas_t = []
        for rotulo, a, b in comparacoes:
            ids = sorted(set(a) & set(b))
            linha = [rotulo, str(len(ids))]
            for nome, f in medidas.items():
                k = kappa([f(a[i]) for i in ids], [f(b[i]) for i in ids])
                linha.append("n/d" if k is None else br(k, 2))
                nome_md = nome.replace("$\\geq$", "≥")
                md.append(f"- {rotulo} / {nome_md}: κ={'n/d' if k is None else br(k, 2)} ({faixa_kappa(k)}), n={len(ids)}")
            linhas_t.append(linha)
        # viés de família: concordância humano × juiz separada por provedor do gerador
        for q, av in fontes:
            for fam, filtro in (("Anthropic", lambda p: p == "Anthropic"), ("outros", lambda p: p != "Anthropic")):
                ids = sorted(i for i in av if i in juiz and filtro(juiz[i]["provedor"]))
                k = kappa([medidas["Aceitável"](av[i]) for i in ids], [medidas["Aceitável"](juiz[i]) for i in ids])
                ac_h = sum(bool(medidas["Aceitável"](av[i])) for i in ids)
                ac_j = sum(bool(medidas["Aceitável"](juiz[i])) for i in ids)
                linhas_t.append([f"{q} × juiz ({fam})", str(len(ids)), "n/d" if k is None else br(k, 2),
                                 "", "", "", ""])
                md.append(f"- Viés de família — {q} × juiz, questões {fam}: κ(aceitável)={'n/d' if k is None else br(k, 2)}; "
                          f"aceitáveis segundo {q}: {ac_h}/{len(ids)}, segundo o juiz: {ac_j}/{len(ids)}")
        tex.append(tabela("tab:concordancia", "Concordância (kappa de Cohen) entre avaliadores na amostra humana",
                          "lcccccc", ["Comparação", "$n$"] + list(medidas), linhas_t,
                          "C1 com três categorias; demais binários. As linhas por família repetem o kappa de \\textit{aceitável} "
                          "separando as questões dos modelos da Anthropic, da mesma família do avaliador. Fonte: elaborada pelo autor."))
    else:
        md.append("\n## Concordância\n\nAinda sem avaliação humana (rode o passo 4 e preencha as planilhas).\n")

    # ---------- saídas
    (config.RESULTADOS / "tabelas.tex").write_text(
        "\n".join(tex), encoding="utf-8")
    (config.RESULTADOS / "resumo.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    campos = ["id", "gerador", "provedor", "condicao", "material", "fragmento_id", "status", "pergunta", "opcoes",
              "correta", "c1", "c2", "c3", "c4", "c5", "aceitavel", "justificativa_juiz", "tokens_in", "tokens_out", "latencia_s"]
    with open(config.RESULTADOS / "questoes_avaliadas.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for l in sorted(linhas, key=lambda l: l["id"]):
            w.writerow({**l, "opcoes": " | ".join(l.get("opcoes") or [])})
    print("\n".join(md))
    print(f"\nTabelas em {config.RESULTADOS / 'tabelas.tex'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
