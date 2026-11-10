"""Ingestão de PDFs: texto por página, limpeza do layout (cabeçalho, rodapé,
numeração) e transcrição por visão das páginas que são só imagem — slides
exportados como figura, handouts do PowerPoint, digitalizações."""
from io import BytesIO

from pypdf import PdfReader

import time

from . import config, llm, rag

# Escala de renderização: 2.5 deixa legível o texto de slides miniaturizados em handouts.
ESCALA_RENDER = 2.5


def _renderizar(documento, indice: int) -> bytes:
    imagem = documento[indice].render(scale=ESCALA_RENDER).to_pil().convert("RGB")
    saida = BytesIO()
    imagem.save(saida, "JPEG", quality=85)
    return saida.getvalue()


def processar_pdf(conteudo: bytes) -> tuple[list[str], list[str], int]:
    """Retorna (texto de cada página, fragmentos para indexar, nº de páginas lidas por visão)."""
    leitor = PdfReader(BytesIO(conteudo))
    paginas = rag.remover_cabecalhos_rodapes([p.extract_text() or "" for p in leitor.pages])
    lidas = 0
    documento = None
    if llm.disponivel():
        for i, pagina in enumerate(leitor.pages):
            if rag.contar_palavras(paginas[i]) >= config.VISAO_MIN_PALAVRAS or not rag.tem_imagem(pagina):
                continue
            try:
                if documento is None:
                    import pypdfium2 as pdfium

                    documento = pdfium.PdfDocument(conteudo)
                imagem = _renderizar(documento, i)
                try:
                    transcricao = llm.transcrever_pagina(imagem)
                except llm.LimiteLLM as e:
                    if isinstance(e, llm.LimiteDiarioLLM):
                        raise
                    time.sleep(30)  # limite por minuto da camada gratuita: espera e tenta de novo
                    transcricao = llm.transcrever_pagina(imagem)
            except llm.LimiteDiarioLLM as e:
                llm._registrar_falha("visão: cota diária do LLM esgotada; o resto do PDF fica sem transcrição", str(e))
                break
            except Exception as e:
                llm._registrar_falha(f"visão falhou na página {i + 1}", f"{type(e).__name__}: {e}")
                continue
            if rag.contar_palavras(transcricao) > rag.contar_palavras(paginas[i]):
                paginas[i] = transcricao
                lidas += 1
    if documento is not None:
        documento.close()
    chunks = rag.fragmentar(rag.limpar_texto("\n".join(paginas)))
    return paginas, chunks, lidas


def mensagem_sem_conteudo() -> str:
    if llm.disponivel():
        return ("Não foi possível extrair conteúdo do PDF: ele parece ser composto de imagens e a "
                "leitura por visão falhou (veja backend/logs/llm_falhas.log).")
    return ("Não foi possível extrair conteúdo do PDF: ele parece ser composto de imagens. "
            "Configure um LLM no .env para que as páginas sejam lidas por visão.")
