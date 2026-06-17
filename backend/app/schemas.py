from pydantic import BaseModel


class CadeiraIn(BaseModel):
    nome: str


class CadeiraOut(BaseModel):
    id: int
    nome: str

    class Config:
        from_attributes = True


class MaterialOut(BaseModel):
    id: int
    cadeira_id: int
    titulo: str
    status: str

    class Config:
        from_attributes = True


class QuestaoOut(BaseModel):
    id: int
    ordem: int
    topico: str
    pergunta: str
    opcoes: list[str]
    correta: int
    justificativa: str
    chunk_fonte: str
    status: str

    class Config:
        from_attributes = True


class PerguntaOut(BaseModel):
    pergunta: str
    opcoes: list[str]
    correta: int
    justificativa: str
    fonte: str


class SessaoIn(BaseModel):
    cadeira_id: int
    modo: str = "simulado"
    material_ids: list[int] = []


class ProximaIn(BaseModel):
    material_ids: list[int] = []
    n: int = 5


class EstudoIn(BaseModel):
    material_ids: list[int] = []
    nivel: str = "Intermediário"
    objetivo: str = "Revisão para prova"
    tempo: str = "15 min"


class RespostaIn(BaseModel):
    questao_id: int
    escolhida: int


class TelemetriaItem(BaseModel):
    t_offset: int
    focus: float
    phone_eventos: int = 0
    modo: str = "simulado"


class TelemetriaLote(BaseModel):
    itens: list[TelemetriaItem]
