import random
from collections import defaultdict
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, schemas, rag, llm, config
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

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
    texto = rag.extrair_texto(conteudo)
    limpo = rag.limpar_texto(texto)
    chunks = rag.fragmentar(limpo)
    if not chunks:
        raise HTTPException(422, "Não foi possível extrair conteúdo do PDF")
    material = models.Material(cadeira_id=cadeira_id, titulo=titulo, status="pronto")
    db.add(material)
    db.commit()
    db.refresh(material)
    rag.indexar(material.id, chunks)
    return material


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
    return {"removido": True}


@app.post("/materiais/{material_id}/preview", response_model=schemas.PerguntaOut)
def preview_material(material_id: int, db: Session = Depends(get_db)):
    if not llm.disponivel():
        raise HTTPException(503, "Configure um LLM (ex.: Gemini) no .env para gerar questões")
    chunks = rag.bons_chunks(rag.obter_chunks(material_id))
    if not chunks:
        raise HTTPException(422, "Material sem conteúdo indexado; reenvie o PDF")
    chunk = random.choice(chunks)
    try:
        q = llm.pergunta_llm(chunk)
    except Exception as e:
        raise HTTPException(502, f"Falha no LLM ({config.LLM_PROVIDER}): {e}. Verifique a chave e o modelo no .env.")
    return schemas.PerguntaOut(
        pergunta=q["pergunta"],
        opcoes=q["opcoes"],
        correta=int(q["correta"]),
        justificativa=q.get("justificativa", ""),
        fonte=chunk[:400],
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
        for chunk in rag.bons_chunks(rag.obter_chunks(mid)):
            candidatos.append((mid, chunk))
    if not candidatos:
        raise HTTPException(422, "Sem conteúdo para gerar questões")
    material_id, chunk = random.choice(candidatos)
    try:
        q = llm.pergunta_llm(chunk)
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
        status="sessao",
    )
    db.add(questao)
    db.commit()
    db.refresh(questao)
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
        for chunk in rag.bons_chunks(rag.obter_chunks(mid)):
            candidatos.append((mid, chunk))
    if not candidatos:
        raise HTTPException(422, "Sem conteúdo para gerar questões")
    n = max(1, min(dados.n, 8, len(candidatos)))
    escolhidos = random.sample(candidatos, n)
    try:
        questoes = llm.perguntas_lote([c for _, c in escolhidos])
    except Exception as e:
        raise HTTPException(502, f"Falha no LLM ({config.LLM_PROVIDER}): {e}")
    criadas = []
    for (material_id, chunk), q in zip(escolhidos, questoes):
        questao = models.Questao(
            material_id=material_id,
            ordem=0,
            topico="",
            pergunta=q["pergunta"],
            opcoes=q["opcoes"],
            correta=int(q["correta"]),
            justificativa=q.get("justificativa", ""),
            chunk_fonte=chunk,
            status="sessao",
        )
        db.add(questao)
        criadas.append(questao)
    db.commit()
    for c in criadas:
        db.refresh(c)
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
        partes.extend(rag.bons_chunks(rag.obter_chunks(mid)))
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
    db.add(models.Resposta(sessao_id=sessao_id, questao_id=dados.questao_id, escolhida=dados.escolhida, acertou=acertou))
    db.commit()
    return {"acertou": acertou, "correta": questao.correta, "justificativa": questao.justificativa}


@app.post("/sessoes/{sessao_id}/encerrar")
def encerrar_sessao(sessao_id: int, db: Session = Depends(get_db)):
    sessao = db.get(models.Sessao, sessao_id)
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada")
    sessao.encerrada = True
    db.commit()
    return {"encerrada": True}


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
