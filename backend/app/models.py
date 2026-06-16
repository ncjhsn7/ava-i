from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, JSON, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Cadeira(Base):
    __tablename__ = "cadeiras"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    materiais: Mapped[list["Material"]] = relationship(back_populates="cadeira", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = "materiais"
    id: Mapped[int] = mapped_column(primary_key=True)
    cadeira_id: Mapped[int] = mapped_column(ForeignKey("cadeiras.id"))
    titulo: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="processando")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    cadeira: Mapped[Cadeira] = relationship(back_populates="materiais")
    questoes: Mapped[list["Questao"]] = relationship(back_populates="material", cascade="all, delete-orphan")


class Questao(Base):
    __tablename__ = "questoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiais.id"))
    ordem: Mapped[int] = mapped_column(Integer)
    topico: Mapped[str] = mapped_column(String(200), default="")
    pergunta: Mapped[str] = mapped_column(Text)
    opcoes: Mapped[list] = mapped_column(JSON)
    correta: Mapped[int] = mapped_column(Integer)
    justificativa: Mapped[str] = mapped_column(Text, default="")
    chunk_fonte: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    material: Mapped[Material] = relationship(back_populates="questoes")


class Sessao(Base):
    __tablename__ = "sessoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    cadeira_id: Mapped[int] = mapped_column(ForeignKey("cadeiras.id"))
    modo: Mapped[str] = mapped_column(String(20), default="simulado")
    inicio: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    encerrada: Mapped[bool] = mapped_column(Boolean, default=False)


class Telemetria(Base):
    __tablename__ = "telemetria"
    id: Mapped[int] = mapped_column(primary_key=True)
    sessao_id: Mapped[int] = mapped_column(ForeignKey("sessoes.id"))
    t_offset: Mapped[int] = mapped_column(Integer)
    focus: Mapped[float] = mapped_column(Float)
    phone_eventos: Mapped[int] = mapped_column(Integer, default=0)
    modo: Mapped[str] = mapped_column(String(20), default="simulado")


class Resposta(Base):
    __tablename__ = "respostas"
    id: Mapped[int] = mapped_column(primary_key=True)
    sessao_id: Mapped[int] = mapped_column(ForeignKey("sessoes.id"))
    questao_id: Mapped[int] = mapped_column(ForeignKey("questoes.id"))
    escolhida: Mapped[int] = mapped_column(Integer)
    acertou: Mapped[bool] = mapped_column(Boolean)
