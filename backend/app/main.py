from collections import defaultdict
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session
from . import models, schemas, rag, llm, config
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AVA-I API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/saude")
def saude():
    return {"status": "ok", "llm": config.LLM_PROVIDER, "embeddings": config.EMBEDDINGS}


@app.post("/materiais", response_model=schemas.MaterialOut)
async def criar_material(
    titulo: str = Form(...),
    cenario: str = Form("restrito"),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    conteudo = await arquivo.read()
    texto = rag.extrair_texto(conteudo)
    chunks = rag.fragmentar(texto)
    if not chunks:
        raise HTTPException(422, "Não foi possível extrair texto do PDF")
    material = models.Material(titulo=titulo, cenario=cenario)
    db.add(material)
    db.commit()
    db.refresh(material)
    rag.indexar(material.id, chunks)
    selecionados = rag.selecionar_chunks(chunks, config.QUESTOES_POR_MATERIAL)
    for ordem, (_, trecho) in enumerate(selecionados):
        contexto = rag.vizinhos(material.id, trecho) if cenario == "expandido" else ""
        q = llm.gerar_questao(trecho, contexto)
        db.add(models.Questao(
            material_id=material.id,
            ordem=ordem,
            pergunta=q["pergunta"],
            opcoes=q["opcoes"],
            correta=int(q["correta"]),
            justificativa=q.get("justificativa", ""),
            chunk_fonte=trecho,
        ))
    material.status = "gerado"
    db.commit()
    db.refresh(material)
    return material


@app.get("/materiais", response_model=list[schemas.MaterialOut])
def listar_materiais(status: str | None = None, db: Session = Depends(get_db)):
    consulta = db.query(models.Material)
    if status:
        consulta = consulta.filter(models.Material.status == status)
    return consulta.order_by(models.Material.id.desc()).all()


@app.get("/materiais/{material_id}/questoes", response_model=list[schemas.QuestaoOut])
def listar_questoes(material_id: int, status: str | None = None, db: Session = Depends(get_db)):
    consulta = db.query(models.Questao).filter(models.Questao.material_id == material_id)
    if status:
        consulta = consulta.filter(models.Questao.status == status)
    return consulta.order_by(models.Questao.ordem).all()


@app.patch("/questoes/{questao_id}", response_model=schemas.QuestaoOut)
def atualizar_questao(questao_id: int, dados: schemas.QuestaoPatch, db: Session = Depends(get_db)):
    questao = db.get(models.Questao, questao_id)
    if not questao:
        raise HTTPException(404, "Questão não encontrada")
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(questao, campo, valor)
    db.commit()
    db.refresh(questao)
    return questao


@app.post("/materiais/{material_id}/publicar", response_model=schemas.MaterialOut)
def publicar_material(material_id: int, db: Session = Depends(get_db)):
    material = db.get(models.Material, material_id)
    if not material:
        raise HTTPException(404, "Material não encontrado")
    aprovadas = [q for q in material.questoes if q.status == "aprovada"]
    if not aprovadas:
        raise HTTPException(422, "Aprove pelo menos uma questão antes de publicar")
    material.status = "publicado"
    db.commit()
    db.refresh(material)
    return material


@app.post("/sessoes")
def iniciar_sessao(dados: schemas.SessaoIn, db: Session = Depends(get_db)):
    sessao = models.Sessao(material_id=dados.material_id, condicao=dados.condicao, modo=dados.modo)
    db.add(sessao)
    db.commit()
    db.refresh(sessao)
    return {"id": sessao.id}


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


@app.get("/dashboard/{material_id}")
def dashboard(material_id: int, db: Session = Depends(get_db)):
    sessoes = db.query(models.Sessao).filter(models.Sessao.material_id == material_id).all()
    ids = [s.id for s in sessoes]
    telemetria = db.query(models.Telemetria).filter(models.Telemetria.sessao_id.in_(ids)).all() if ids else []
    respostas = db.query(models.Resposta).filter(models.Resposta.sessao_id.in_(ids)).all() if ids else []

    foco_por_sessao = defaultdict(list)
    fones_por_sessao = defaultdict(int)
    for t in telemetria:
        foco_por_sessao[t.sessao_id].append(t.focus)
        fones_por_sessao[t.sessao_id] += t.phone_eventos

    acertos_por_sessao = defaultdict(lambda: [0, 0])
    acertos_por_questao = defaultdict(lambda: [0, 0])
    for r in respostas:
        acertos_por_sessao[r.sessao_id][0] += int(r.acertou)
        acertos_por_sessao[r.sessao_id][1] += 1
        acertos_por_questao[r.questao_id][0] += int(r.acertou)
        acertos_por_questao[r.questao_id][1] += 1

    pontos = []
    for sid, focos in foco_por_sessao.items():
        certas, total = acertos_por_sessao.get(sid, [0, 0])
        if total:
            pontos.append({"focus": round(sum(focos) / len(focos), 1), "acerto": round(100 * certas / total, 1)})

    condicao_por_sessao = {s.id: s.condicao for s in sessoes}
    linha = defaultdict(lambda: defaultdict(list))
    for t in telemetria:
        minuto = t.t_offset // 60
        linha[condicao_por_sessao.get(t.sessao_id, "intervencao")][minuto].append(t.focus)
    minutos = sorted({m for cond in linha.values() for m in cond})
    serie = lambda cond: [round(sum(linha[cond][m]) / len(linha[cond][m]), 1) if linha[cond].get(m) else None for m in minutos]

    questoes = db.query(models.Questao).filter(models.Questao.material_id == material_id).order_by(models.Questao.ordem).all()
    barras = [{
        "questao": f"Q{q.ordem + 1}",
        "acerto": round(100 * acertos_por_questao[q.id][0] / acertos_por_questao[q.id][1], 1) if acertos_por_questao[q.id][1] else None,
    } for q in questoes]

    eventos = defaultdict(list)
    for sid, n in fones_por_sessao.items():
        eventos[condicao_por_sessao.get(sid, "intervencao")].append(n)
    media = lambda xs: round(sum(xs) / len(xs), 2) if xs else 0

    todos_focos = [f for fs in foco_por_sessao.values() for f in fs]
    return {
        "kpis": {
            "sessoes": len(sessoes),
            "focus_medio": round(sum(todos_focos) / len(todos_focos), 1) if todos_focos else 0,
            "eventos_controle": media(eventos["controle"]),
            "eventos_intervencao": media(eventos["intervencao"]),
        },
        "engajamento": {"minutos": minutos, "controle": serie("controle"), "intervencao": serie("intervencao")},
        "acertos_por_questao": barras,
        "pontos": pontos,
    }
