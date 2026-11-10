import random
from collections import defaultdict
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool
from . import models, schemas, rag, llm, config, gamificacao, ingestao
from sqlalchemy import inspect, text
import threading
from .database import Base, SessionLocal, engine, get_db

Base.metadata.create_all(bind=engine)
_colunas = {c["name"] for c in inspect(engine).get_columns("questoes")}
with engine.begin() as conn:
    if "evidencia" not in _colunas:
        conn.execute(text("ALTER TABLE questoes ADD COLUMN evidencia TEXT DEFAULT ''"))
    if "explicacoes" not in _colunas:
        conn.execute(text("ALTER TABLE questoes ADD COLUMN explicacoes JSON DEFAULT '[]'"))
    if "pagina" not in _colunas:
        conn.execute(text("ALTER TABLE questoes ADD COLUMN pagina INTEGER"))
    if "criado_em" not in {c["name"] for c in inspect(engine).get_columns("respostas")}:
        conn.execute(text("ALTER TABLE respostas ADD COLUMN criado_em DATETIME"))
    if "area" not in {c["name"] for c in inspect(engine).get_columns("materiais")}:
        conn.execute(text("ALTER TABLE materiais ADD COLUMN area VARCHAR(80) DEFAULT ''"))


def _areas_existentes(db: Session) -> list[str]:
    return sorted({m.area for m in db.query(models.Material).all() if m.area})


def _classificar_material(db: Session, material: models.Material, conteudo: str) -> bool:
    """Preenche a área do material via LLM; se falhar, deixa vazia para tentar depois."""
    area = ""
    if llm.disponivel():
        try:
            area = llm.classificar_area(material.titulo, conteudo, _areas_existentes(db))
        except Exception as e:
            llm._registrar_falha(f"classificação de área falhou (material {material.id})", f"{type(e).__name__}: {e}")
    if not area:
        # Sem LLM (ou cota esgotada): usa o nome da cadeira, que o estudante pode editar em Materiais.
        area = material.cadeira.nome if material.cadeira else ""
    if not area:
        return False
    try:
        material.area = area
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def _gerar_com_retentativa(candidatos: list, tentativas: int = 3):
    """Sorteia trechos até o LLM devolver uma questão (pula capa, referências etc.)."""
    pool = list(candidatos)
    random.shuffle(pool)
    ultimo_erro = None
    for item in pool[:tentativas]:
        try:
            return item, llm.pergunta_llm(item[1])
        except llm.TrechoSemConteudo as e:
            ultimo_erro = e
    raise ultimo_erro or ValueError("sem trechos avaliáveis")

app = FastAPI(title="AVA-I API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/saude")
def saude():
    return {"status": "ok", "llm": config.LLM_PROVIDER, "llm_ativo": llm.disponivel()}


@app.post("/cadeiras", response_model=schemas.CadeiraOut)
def criar_cadeira(dados: schemas.CadeiraIn, db: Session = Depends(get_db)):
    cadeira = models.Cadeira(nome=dados.nome)
    db.add(cadeira)
    db.commit()
    db.refresh(cadeira)
    return cadeira


@app.get("/cadeiras", response_model=list[schemas.CadeiraOut])
def listar_cadeiras(db: Session = Depends(get_db)):
    return db.query(models.Cadeira).order_by(models.Cadeira.id.desc()).all()


@app.delete("/cadeiras/{cadeira_id}")
def remover_cadeira(cadeira_id: int, db: Session = Depends(get_db)):
    cadeira = db.get(models.Cadeira, cadeira_id)
    if not cadeira:
        raise HTTPException(404, "Cadeira não encontrada")
    sessoes = db.query(models.Sessao).filter(models.Sessao.cadeira_id == cadeira_id).all()
    ids_sessoes = [s.id for s in sessoes]
    if ids_sessoes:
        db.query(models.Telemetria).filter(models.Telemetria.sessao_id.in_(ids_sessoes)).delete(synchronize_session=False)
        db.query(models.Resposta).filter(models.Resposta.sessao_id.in_(ids_sessoes)).delete(synchronize_session=False)
    for s in sessoes:
        db.delete(s)
    for material in list(cadeira.materiais):
        rag.remover_indice(material.id)
        rag.remover_pdf(material.id)
    db.delete(cadeira)
    db.commit()
    return {"removido": True}


@app.post("/cadeiras/{cadeira_id}/materiais", response_model=schemas.MaterialOut)
async def criar_material(
    cadeira_id: int,
    titulo: str = Form(...),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    cadeira = db.get(models.Cadeira, cadeira_id)
    if not cadeira:
        raise HTTPException(404, "Cadeira não encontrada")
    conteudo = await arquivo.read()
    # Pode chamar o LLM de visão para páginas que são só imagem: roda fora do event loop.
    paginas, chunks, _ = await run_in_threadpool(ingestao.processar_pdf, conteudo)
    if not chunks:
        raise HTTPException(422, ingestao.mensagem_sem_conteudo())
    material = models.Material(cadeira_id=cadeira_id, titulo=titulo, status="pronto")
    db.add(material)
    db.commit()
    db.refresh(material)
    rag.indexar(material.id, chunks)
    rag.salvar_pdf(material.id, conteudo)
    rag.salvar_paginas(material.id, paginas)
    # A área é classificada em segundo plano para o envio não ficar esperando o LLM.
    if llm.disponivel():
        threading.Thread(target=_classificar_pendentes, daemon=True).start()
    return material


@app.put("/materiais/{material_id}/area", response_model=schemas.MaterialOut)
def alterar_area(material_id: int, dados: schemas.AreaIn, db: Session = Depends(get_db)):
    material = db.get(models.Material, material_id)
    if not material:
        raise HTTPException(404, "Material não encontrado")
    area = " ".join(dados.area.split())[:60]
    for e in _areas_existentes(db):
        if e.lower() == area.lower():
            area = e
            break
    material.area = area
    db.commit()
    db.refresh(material)
    return material


@app.get("/materiais/{material_id}/pdf")
def baixar_pdf(material_id: int):
    caminho = rag.caminho_pdf(material_id)
    if not os.path.exists(caminho):
        raise HTTPException(404, "PDF original não disponível; reenvie o material")
    return FileResponse(caminho, media_type="application/pdf", headers={"Content-Disposition": "inline"})


@app.get("/cadeiras/{cadeira_id}/materiais", response_model=list[schemas.MaterialOut])
def listar_materiais(cadeira_id: int, db: Session = Depends(get_db)):
    return db.query(models.Material).filter(models.Material.cadeira_id == cadeira_id).order_by(models.Material.id).all()


@app.delete("/materiais/{material_id}")
def remover_material(material_id: int, db: Session = Depends(get_db)):
    material = db.get(models.Material, material_id)
    if not material:
        raise HTTPException(404, "Material não encontrado")
    db.delete(material)
    db.commit()
    rag.remover_indice(material_id)
    rag.remover_pdf(material_id)
    return {"removido": True}


@app.post("/materiais/{material_id}/reprocessar", response_model=schemas.MaterialOut)
def reprocessar_material(material_id: int, db: Session = Depends(get_db)):
    """Refaz a extração e o índice de um PDF já enviado (ex.: PDF de imagens enviado
    antes da leitura por visão), sem perder o histórico de questões e respostas."""
    material = db.get(models.Material, material_id)
    if not material:
        raise HTTPException(404, "Material não encontrado")
    caminho = rag.caminho_pdf(material_id)
    if not os.path.exists(caminho):
        raise HTTPException(404, "O PDF original não está salvo; envie o arquivo de novo")
    with open(caminho, "rb") as f:
        conteudo = f.read()
    paginas, chunks, _ = ingestao.processar_pdf(conteudo)
    if not chunks:
        raise HTTPException(422, ingestao.mensagem_sem_conteudo())
    rag.remover_indice(material_id)
    rag.indexar(material_id, chunks)
    rag.salvar_paginas(material_id, paginas)
    return material


@app.post("/materiais/{material_id}/preview", response_model=schemas.PerguntaOut)
def preview_material(material_id: int, db: Session = Depends(get_db)):
    if not llm.disponivel():
        raise HTTPException(503, "Configure um LLM (ex.: Gemini) no .env para gerar questões")
    chunks = rag.chunks_avaliaveis(rag.obter_chunks(material_id))
    if not chunks:
        raise HTTPException(422, "Material sem conteúdo indexado; reenvie o PDF")
    try:
        (_, chunk), q = _gerar_com_retentativa([(material_id, c) for c in chunks])
    except Exception as e:
        raise HTTPException(502, f"Falha no LLM ({config.LLM_PROVIDER}): {e}. Verifique a chave e o modelo no .env.")
    return schemas.PerguntaOut(
        pergunta=q["pergunta"],
        opcoes=q["opcoes"],
        correta=int(q["correta"]),
        justificativa=q.get("justificativa", ""),
        fonte=chunk[:400],
        evidencia=q.get("evidencia", ""),
    )


@app.post("/sessoes")
def iniciar_sessao(dados: schemas.SessaoIn, db: Session = Depends(get_db)):
    cadeira = db.get(models.Cadeira, dados.cadeira_id)
    if not cadeira:
        raise HTTPException(404, "Cadeira não encontrada")
    if not dados.material_ids:
        raise HTTPException(422, "Selecione ao menos um PDF")
    sessao = models.Sessao(cadeira_id=dados.cadeira_id, modo=dados.modo)
    db.add(sessao)
    db.commit()
    db.refresh(sessao)
    return {"sessao_id": sessao.id}


@app.post("/sessoes/{sessao_id}/questao", response_model=schemas.QuestaoOut)
def proxima_questao(sessao_id: int, dados: schemas.ProximaIn, db: Session = Depends(get_db)):
    sessao = db.get(models.Sessao, sessao_id)
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada")
    if not llm.disponivel():
        raise HTTPException(503, "Configure um LLM (ex.: Gemini) no .env para gerar questões")
    candidatos = []
    for mid in dados.material_ids:
        for chunk in rag.chunks_avaliaveis(rag.obter_chunks(mid)):
            candidatos.append((mid, chunk))
    if not candidatos:
        raise HTTPException(422, "Sem conteúdo para gerar questões")
    try:
        (material_id, chunk), q = _gerar_com_retentativa(candidatos)
    except Exception as e:
        raise HTTPException(502, f"Falha no LLM ({config.LLM_PROVIDER}): {e}")
    questao = models.Questao(
        material_id=material_id,
        ordem=0,
        topico="",
        pergunta=q["pergunta"],
        opcoes=q["opcoes"],
        correta=int(q["correta"]),
        justificativa=q.get("justificativa", ""),
        chunk_fonte=chunk,
        evidencia=q.get("evidencia", ""),
        explicacoes=q.get("explicacoes", []),
        pagina=rag.localizar_pagina(material_id, q.get("evidencia", ""), chunk),
        status="sessao",
    )
    db.add(questao)
    db.commit()
    db.refresh(questao)
    _ = questao.material  # carrega o título antes de a sessão fechar
    return questao


@app.post("/sessoes/{sessao_id}/lote", response_model=list[schemas.QuestaoOut])
def lote_questoes(sessao_id: int, dados: schemas.ProximaIn, db: Session = Depends(get_db)):
    sessao = db.get(models.Sessao, sessao_id)
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada")
    if not llm.disponivel():
        raise HTTPException(503, "Configure um LLM (ex.: Gemini) no .env para gerar questões")
    candidatos = []
    for mid in dados.material_ids:
        for chunk in rag.chunks_avaliaveis(rag.obter_chunks(mid)):
            candidatos.append((mid, chunk))
    if not candidatos:
        raise HTTPException(422, "Sem conteúdo para gerar questões")
    n = max(1, min(dados.n, 8, len(candidatos)))
    escolhidos = random.sample(candidatos, n)
    try:
        questoes = llm.perguntas_lote([c for _, c in escolhidos])
    except llm.LimiteLLM as e:
        raise HTTPException(429, f"Falha no LLM ({config.LLM_PROVIDER}): {e}")
    except Exception as e_lote:
        # Plano B: se o lote vier vazio/inválido, gera uma questão avulsa.
        try:
            item, q = _gerar_com_retentativa(candidatos)
        except Exception:
            raise HTTPException(502, f"Falha no LLM ({config.LLM_PROVIDER}): {e_lote}")
        escolhidos = [item]
        questoes = [(0, q)]
    criadas = []
    for idx, q in questoes:
        material_id, chunk = escolhidos[idx]
        questao = models.Questao(
            material_id=material_id,
            ordem=0,
            topico="",
            pergunta=q["pergunta"],
            opcoes=q["opcoes"],
            correta=int(q["correta"]),
            justificativa=q.get("justificativa", ""),
            chunk_fonte=chunk,
            evidencia=q.get("evidencia", ""),
            explicacoes=q.get("explicacoes", []),
            pagina=rag.localizar_pagina(material_id, q.get("evidencia", ""), chunk),
            status="sessao",
        )
        db.add(questao)
        criadas.append(questao)
    db.commit()
    for c in criadas:
        db.refresh(c)
        _ = c.material
    return criadas


@app.post("/cadeiras/{cadeira_id}/estudo")
def gerar_estudo(cadeira_id: int, dados: schemas.EstudoIn, db: Session = Depends(get_db)):
    cadeira = db.get(models.Cadeira, cadeira_id)
    if not cadeira:
        raise HTTPException(404, "Cadeira não encontrada")
    if not dados.material_ids:
        raise HTTPException(422, "Selecione ao menos um PDF")
    if not llm.disponivel():
        raise HTTPException(503, "Configure um LLM (ex.: Gemini) no .env para gerar o material de estudo")
    partes = []
    for mid in dados.material_ids:
        partes.extend(rag.chunks_avaliaveis(rag.obter_chunks(mid)))
    if not partes:
        raise HTTPException(422, "Sem conteúdo nos PDFs selecionados")
    conteudo = "\n\n".join(partes)
    try:
        texto = llm.gerar_material_estudo(conteudo, dados.nivel, dados.objetivo, dados.tempo)
    except Exception as e:
        raise HTTPException(502, f"Falha no LLM ({config.LLM_PROVIDER}): {e}")
    return {"texto": texto}


@app.post("/sessoes/{sessao_id}/telemetria")
def receber_telemetria(sessao_id: int, lote: schemas.TelemetriaLote, db: Session = Depends(get_db)):
    for item in lote.itens:
        db.add(models.Telemetria(sessao_id=sessao_id, **item.model_dump()))
    db.commit()
    return {"recebidos": len(lote.itens)}


@app.post("/sessoes/{sessao_id}/respostas")
def registrar_resposta(sessao_id: int, dados: schemas.RespostaIn, db: Session = Depends(get_db)):
    questao = db.get(models.Questao, dados.questao_id)
    if not questao:
        raise HTTPException(404, "Questão não encontrada")
    acertou = dados.escolhida == questao.correta
    sequencia_antes = gamificacao.sequencia_na_sessao(db, sessao_id)
    xp_ganho, sequencia = gamificacao.xp_resposta(acertou, sequencia_antes)
    db.add(models.Resposta(sessao_id=sessao_id, questao_id=dados.questao_id, escolhida=dados.escolhida, acertou=acertou))
    db.commit()
    meta = gamificacao.obter_meta(db)
    hoje = gamificacao.respondidas_no_dia(db, gamificacao.hoje())
    meta_batida = hoje == meta
    if meta_batida:
        xp_ganho += gamificacao.XP_META
    explicacoes = questao.explicacoes or []
    explicacao = explicacoes[dados.escolhida] if not acertou and 0 <= dados.escolhida < len(explicacoes) else ""
    return {
        "acertou": acertou,
        "correta": questao.correta,
        "justificativa": questao.justificativa,
        "explicacao_escolhida": explicacao,
        "xp_ganho": xp_ganho,
        "sequencia": sequencia,
        "respondidas_hoje": hoje,
        "meta_batida": meta_batida,
    }


_classificando = threading.Lock()


def _classificar_pendentes() -> None:
    """Classifica, em segundo plano, PDFs enviados antes de existir a área."""
    if not _classificando.acquire(blocking=False):
        return  # já tem uma classificação rodando
    db = SessionLocal()
    try:
        sem_area = db.query(models.Material).filter(
            (models.Material.area == "") | (models.Material.area.is_(None))).limit(10).all()
        for material in sem_area:
            try:
                conteudo = "\n".join(rag.obter_chunks(material.id)[:6])
            except Exception as e:
                llm._registrar_falha(f"chunks indisponíveis para classificar (material {material.id})", repr(e))
                conteudo = ""
            _classificar_material(db, material, conteudo or material.titulo)
    finally:
        db.close()
        _classificando.release()


@app.get("/progresso")
def progresso(db: Session = Depends(get_db)):
    if llm.disponivel():
        threading.Thread(target=_classificar_pendentes, daemon=True).start()
    return gamificacao.calcular(db)


@app.put("/progresso/meta")
def alterar_meta(dados: schemas.MetaIn, db: Session = Depends(get_db)):
    return {"meta_diaria": gamificacao.definir_meta(db, dados.meta)}


@app.post("/sessoes/{sessao_id}/encerrar")
def encerrar_sessao(sessao_id: int, db: Session = Depends(get_db)):
    sessao = db.get(models.Sessao, sessao_id)
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada")
    sessao.encerrada = True
    db.commit()
    return {"encerrada": True}


@app.get("/cadeiras/{cadeira_id}/erros", response_model=list[schemas.QuestaoOut])
def listar_erros(cadeira_id: int, limit: int = 20, db: Session = Depends(get_db)):
    sessoes = db.query(models.Sessao).filter(models.Sessao.cadeira_id == cadeira_id).all()
    ids = [s.id for s in sessoes]
    if not ids:
        return []
    respostas = (
        db.query(models.Resposta)
        .filter(models.Resposta.sessao_id.in_(ids))
        .order_by(models.Resposta.id.desc())
        .all()
    )
    vistos: set[int] = set()
    questoes = []
    for r in respostas:
        if r.questao_id in vistos:
            continue
        vistos.add(r.questao_id)
        if r.acertou:
            continue
        questao = db.get(models.Questao, r.questao_id)
        if questao:
            _ = questao.material
            questoes.append(questao)
        if len(questoes) >= limit:
            break
    return questoes


@app.get("/cadeiras/{cadeira_id}/dashboard")
def dashboard(cadeira_id: int, db: Session = Depends(get_db)):
    sessoes = db.query(models.Sessao).filter(models.Sessao.cadeira_id == cadeira_id).all()
    ids = [s.id for s in sessoes]
    telemetria = db.query(models.Telemetria).filter(models.Telemetria.sessao_id.in_(ids)).all() if ids else []
    respostas = db.query(models.Resposta).filter(models.Resposta.sessao_id.in_(ids)).all() if ids else []

    focos = [t.focus for t in telemetria if t.focus > 0]
    certas = sum(1 for r in respostas if r.acertou)
    total = len(respostas)

    duracao_por_sessao = defaultdict(int)
    for t in telemetria:
        duracao_por_sessao[t.sessao_id] = max(duracao_por_sessao[t.sessao_id], t.t_offset)
    tempo_estudo_s = sum(duracao_por_sessao.values())
    tempo_focado_s = sum(5 for t in telemetria if t.focus >= 60)
    eventos_celular = sum(t.phone_eventos for t in telemetria)

    por_minuto = defaultdict(list)
    for t in telemetria:
        if t.focus > 0:
            por_minuto[t.t_offset // 60].append(t.focus)
    minutos = sorted(por_minuto)
    serie_foco = [round(sum(por_minuto[m]) / len(por_minuto[m]), 1) for m in minutos]

    por_material = defaultdict(lambda: [0, 0])
    for r in respostas:
        questao = db.get(models.Questao, r.questao_id)
        material = db.get(models.Material, questao.material_id) if questao else None
        rotulo = material.titulo if material else "—"
        por_material[rotulo][0] += int(r.acertou)
        por_material[rotulo][1] += 1
    barras = [
        {"topico": rotulo, "acerto": round(100 * c / n, 1) if n else None, "respostas": n}
        for rotulo, (c, n) in por_material.items()
    ]

    return {
        "kpis": {
            "sessoes": len(sessoes),
            "respostas": total,
            "acerto_medio": round(100 * certas / total, 1) if total else 0,
            "foco_medio": round(sum(focos) / len(focos), 1) if focos else None,
            "tempo_estudo_min": round(tempo_estudo_s / 60, 1),
            "tempo_focado_min": round(tempo_focado_s / 60, 1),
            "eventos_celular": eventos_celular,
        },
        "foco_no_tempo": {"minutos": minutos, "foco": serie_foco},
        "acertos_por_topico": barras,
    }
