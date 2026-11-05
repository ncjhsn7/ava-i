"""Gamificação do Âncora: XP e níveis, sequência de dias, sequência de acertos,
meta diária e domínio por PDF. Tudo é calculado a partir das respostas salvas."""
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from . import models

XP_ACERTO = 10
XP_ERRO = 2                # esforço também conta
BONUS_SEQUENCIA = 2        # por acerto seguido além do primeiro
BONUS_SEQUENCIA_MAX = 10
XP_META = 50               # bônus ao bater a meta diária
META_PADRAO = 10
JANELA_DOMINIO = 20        # últimas N respostas de cada PDF

TITULOS = ["Iniciante", "Aprendiz", "Estudante", "Dedicado", "Avançado",
           "Especialista", "Mestre", "Sábio", "Lenda"]


def xp_resposta(acertou: bool, sequencia_antes: int) -> tuple[int, int]:
    """Retorna (xp ganho, nova sequência de acertos)."""
    if not acertou:
        return XP_ERRO, 0
    sequencia = sequencia_antes + 1
    return XP_ACERTO + min(BONUS_SEQUENCIA * (sequencia - 1), BONUS_SEQUENCIA_MAX), sequencia


def nivel_por_xp(xp: int) -> dict:
    """Nível L começa em 50·L·(L-1) XP: 0, 100, 300, 600, 1000, 1500…"""
    nivel = 1
    while xp >= 50 * nivel * (nivel + 1):
        nivel += 1
    return {
        "nivel": nivel,
        "titulo": TITULOS[min(nivel - 1, len(TITULOS) - 1)],
        "xp_nivel_inicio": 50 * nivel * (nivel - 1),
        "xp_proximo_nivel": 50 * nivel * (nivel + 1),
    }


def _dia_local(momento_utc: datetime) -> date:
    return (momento_utc + (datetime.now() - datetime.utcnow())).date()


def hoje() -> date:
    return datetime.now().date()


def obter_meta(db: Session) -> int:
    pref = db.get(models.Preferencia, "meta_diaria")
    try:
        return max(1, int(pref.valor)) if pref else META_PADRAO
    except ValueError:
        return META_PADRAO


def definir_meta(db: Session, meta: int) -> int:
    meta = max(1, min(int(meta), 200))
    pref = db.get(models.Preferencia, "meta_diaria")
    if pref:
        pref.valor = str(meta)
    else:
        db.add(models.Preferencia(chave="meta_diaria", valor=str(meta)))
    db.commit()
    return meta


def sequencia_na_sessao(db: Session, sessao_id: int) -> int:
    """Acertos seguidos mais recentes da sessão."""
    seq = 0
    for r in (db.query(models.Resposta).filter(models.Resposta.sessao_id == sessao_id)
              .order_by(models.Resposta.id.desc())):
        if not r.acertou:
            break
        seq += 1
    return seq


def respondidas_no_dia(db: Session, dia: date) -> int:
    inicio_sessoes = {s.id: s.inicio for s in db.query(models.Sessao).all()}
    return sum(
        1 for r in db.query(models.Resposta).all()
        if (m := r.criado_em or inicio_sessoes.get(r.sessao_id)) and _dia_local(m) == dia
    )


def calcular(db: Session) -> dict:
    sessoes = {s.id: s for s in db.query(models.Sessao).all()}
    respostas = db.query(models.Resposta).order_by(models.Resposta.id).all()
    material_da_questao = dict(db.query(models.Questao.id, models.Questao.material_id).all())
    materiais = db.query(models.Material).order_by(models.Material.cadeira_id, models.Material.id).all()
    area_do_material = {m.id: (m.area or "Sem área") for m in materiais}
    meta = obter_meta(db)

    xp = 0
    seq_por_sessao: dict[int, int] = defaultdict(int)
    por_dia: dict[date, int] = defaultdict(int)
    por_material: dict[int, list[bool]] = defaultdict(list)
    por_area: dict[str, dict] = defaultdict(lambda: {"xp": 0, "respostas": 0, "acertos": 0})

    for r in respostas:
        ganho, seq_por_sessao[r.sessao_id] = xp_resposta(r.acertou, seq_por_sessao[r.sessao_id])
        xp += ganho
        momento = r.criado_em or (sessoes[r.sessao_id].inicio if r.sessao_id in sessoes else None)
        if momento:
            por_dia[_dia_local(momento)] += 1
        mid = material_da_questao.get(r.questao_id)
        if mid is not None:
            por_material[mid].append(r.acertou)
            a = por_area[area_do_material.get(mid, "Sem área")]
            a["xp"] += ganho
            a["respostas"] += 1
            a["acertos"] += int(r.acertou)

    xp += XP_META * sum(1 for n in por_dia.values() if n >= meta)

    # Sequência de dias: conta a partir de hoje (ou de ontem, se ainda não estudou hoje).
    dia = hoje()
    estudou_hoje = por_dia.get(dia, 0) > 0
    if not estudou_hoje:
        dia -= timedelta(days=1)
    streak = 0
    while por_dia.get(dia, 0) > 0:
        streak += 1
        dia -= timedelta(days=1)

    dominio = []
    for m in materiais:
        ultimas = por_material.get(m.id, [])[-JANELA_DOMINIO:]
        n = len(ultimas)
        pct = round(100 * sum(ultimas) / n) if n else None
        if n == 0:
            status = "Novo"
        elif n < 5:
            status = "Começando"
        elif pct >= 80 and n >= 10:
            status = "Dominado"
        else:
            status = "Em progresso"
        dominio.append({"material_id": m.id, "titulo": m.titulo, "cadeira_id": m.cadeira_id,
                        "area": m.area or "", "pct": pct, "respostas": n, "status": status})

    areas = sorted(
        ({"area": nome, "xp": v["xp"], "respostas": v["respostas"],
          "acerto": round(100 * v["acertos"] / v["respostas"]) if v["respostas"] else None}
         for nome, v in por_area.items()),
        key=lambda a: (a["respostas"], a["xp"]), reverse=True,
    )

    return {
        "xp": xp,
        **nivel_por_xp(xp),
        "streak_dias": streak,
        "estudou_hoje": estudou_hoje,
        "respondidas_hoje": por_dia.get(hoje(), 0),
        "meta_diaria": meta,
        "dominio": dominio,
        "areas": areas,
        "area_mais_estudada": areas[0]["area"] if areas else None,
    }
