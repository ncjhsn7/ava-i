from pydantic import BaseModel


class QuestaoOut(BaseModel):
    id: int
    ordem: int
    pergunta: str
    opcoes: list[str]
    correta: int
    justificativa: str
    chunk_fonte: str
    status: str

    class Config:
        from_attributes = True


class MaterialOut(BaseModel):
    id: int
    titulo: str
    cenario: str
    status: str

    class Config:
        from_attributes = True


class QuestaoPatch(BaseModel):
    pergunta: str | None = None
    opcoes: list[str] | None = None
    correta: int | None = None
    status: str | None = None


class SessaoIn(BaseModel):
    material_id: int
    condicao: str = "intervencao"
    modo: str = "simulado"


class TelemetriaItem(BaseModel):
    t_offset: int
    focus: float
    phone_eventos: int = 0
    modo: str = "simulado"


class TelemetriaLote(BaseModel):
    itens: list[TelemetriaItem]


class RespostaIn(BaseModel):
    questao_id: int
    escolhida: int
