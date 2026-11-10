import json
import random
import re
from . import config
from .rag import remover_referencias

PROMPT = """Você é um gerador de avaliações formativas para um Ambiente Virtual de Aprendizagem.
A partir do trecho de material didático abaixo, gere exatamente 1 questão de múltipla escolha em português, com 4 alternativas, ancorada exclusivamente no trecho.

TRECHO-FONTE:
{trecho}
{contexto}
Responda SOMENTE com um JSON válido no formato:
{{"pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "..."}}"""

PROMPT_TOPICO = """Você é um professor que prepara material de estudo para um Ambiente Virtual de Aprendizagem.
Recebe o título de um tópico e o conteúdo bruto extraído de um material didático (em formato de tópicos/slides).

Sua tarefa:
1. Escreva uma EXPLICAÇÃO didática e coerente do tópico, em português, em prosa corrida (2 a 4 parágrafos curtos), conectando as ideias de forma fluida. Não copie a lista de tópicos: explique como um professor explicaria, baseando-se apenas no conteúdo fornecido.
2. Em seguida, crie 1 questão de múltipla escolha (4 alternativas, exatamente 1 correta) que avalie a compreensão da explicação. As 4 alternativas devem ser plausíveis e sobre o tema.

TÍTULO DO TÓPICO:
{titulo}

CONTEÚDO BRUTO:
{conteudo}

Responda SOMENTE com um JSON válido no formato:
{{"explicacao": "...", "pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "..."}}"""

PROMPT_EXTRAIR = """Você é um professor analisando o conteúdo de um material didático extraído de um PDF.
Identifique os principais tópicos REALMENTE abordados no material e, para cada um, escreva uma explicação didática clara em português, em prosa corrida (2 a 4 parágrafos), baseada SOMENTE no conteúdo fornecido.

Regras:
- Não invente tópicos que não estão no material.
- Use entre 3 e 8 tópicos, conforme a extensão e a variedade do conteúdo. Materiais curtos podem ter menos.
- O título de cada tópico deve refletir o assunto tratado.
- A explicação deve ensinar o conteúdo, não apenas listar palavras.

CONTEÚDO DO MATERIAL:
{conteudo}

Responda SOMENTE com um JSON válido no formato:
{{"topicos": [{{"titulo": "...", "explicacao": "..."}}]}}"""

PROMPT_PERGUNTA = """Com base na explicação a seguir sobre o tópico "{titulo}", crie 1 questão de múltipla escolha em português que avalie a compreensão do conteúdo.
A questão deve ter enunciado claro e contextualizado, 4 alternativas plausíveis e exatamente 1 correta.

EXPLICAÇÃO:
{explicacao}

Responda SOMENTE com um JSON válido no formato:
{{"pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "..."}}"""


_STOP = set(
    "a o e de da do das dos para por com sem que se na no nas nos um uma uns umas "
    "em ao aos as os ou como mais menos entre sobre sob ate apos antes cada qual quais "
    "este esta estes estas esse essa essas esses isso aquilo seu sua seus suas pela pelo "
    "the and of to in is are be by an as at it this that".split()
)


def _termos_salientes(texto: str) -> list[str]:
    palavras = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9/-]{3,}", texto)
    surface: dict[str, str] = {}
    freq: dict[str, int] = {}
    for p in palavras:
        chave = p.lower()
        if chave in _STOP:
            continue
        freq[chave] = freq.get(chave, 0) + 1
        surface.setdefault(chave, p)
    ordenados = sorted(freq, key=lambda c: (freq[c], surface[c][0].isupper(), len(c)), reverse=True)
    return [surface[c] for c in ordenados]


def _janela(texto: str, termo: str) -> str:
    for frase in re.split(r"(?<=[.!?])\s+", texto):
        if re.search(r"\b" + re.escape(termo) + r"\b", frase) and len(frase.strip()) > 25:
            return frase.strip()
    pos = texto.lower().find(termo.lower())
    ini = max(0, pos - 70)
    fim = min(len(texto), pos + len(termo) + 70)
    return ("…" if ini > 0 else "") + texto[ini:fim].strip() + ("…" if fim < len(texto) else "")


def _gerar_mock(trecho: str) -> dict:
    texto = re.sub(r"\s+", " ", trecho).strip()
    termos = _termos_salientes(texto)
    distintos: list[str] = []
    for t in termos:
        if t.lower() not in {d.lower() for d in distintos}:
            distintos.append(t)
    if distintos:
        correta = random.choice(distintos[:6])
        usados = {correta.lower()}
        candidatos = [d for d in distintos if d.lower() != correta.lower()]
        candidatos += re.findall(r"[A-Za-zÀ-ÿ]{3,}", texto)
        distratores: list[str] = []
        for cand in candidatos:
            chave = cand.lower()
            if chave in usados or chave in _STOP:
                continue
            distratores.append(cand)
            usados.add(chave)
            if len(distratores) == 3:
                break
        if len(distratores) == 3:
            janela = re.sub(r"\b" + re.escape(correta) + r"\b", "_____", _janela(texto, correta), count=1)
            return {
                "pergunta": f"Leia a passagem e escolha o termo que completa corretamente a lacuna:\n\n«{janela}»",
                "opcoes": [correta, *distratores],
                "correta": 0,
                "justificativa": f"Na passagem-fonte, o termo que preenche a lacuna é «{correta}».",
            }
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", texto) if len(f.strip()) > 40]
    base = (frases[0] if frases else texto[:160])[:150]
    return {
        "pergunta": "Assinale a alternativa que reproduz uma informação presente na passagem-fonte.",
        "opcoes": [
            base,
            "A passagem não apresenta nenhuma informação sobre o tema da disciplina.",
            "A passagem trata de um assunto sem relação com o conteúdo estudado.",
            "A passagem apresenta o tema apenas como exemplo a ser evitado.",
        ],
        "correta": 0,
        "justificativa": "A alternativa correta reproduz o conteúdo da passagem-fonte (modo de demonstração sem LLM).",
    }


def _gerar_anthropic(trecho: str, contexto: str) -> dict:
    import anthropic

    cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    ctx = f"\nCONTEXTO ADICIONAL (cenário expandido):\n{contexto}\n" if contexto else "\n"
    msg = cliente.messages.create(
        model=config.LLM_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": PROMPT.format(trecho=trecho, contexto=ctx)}],
    )
    texto = msg.content[0].text
    bruto = re.search(r"\{.*\}", texto, re.S)
    return json.loads(bruto.group(0)) if bruto else _gerar_mock(trecho)


def _embaralhar(questao: dict) -> dict:
    opcoes = list(questao.get("opcoes", []))
    correta = int(questao.get("correta", 0))
    if not 0 <= correta < len(opcoes):
        return questao
    explicacoes = questao.get("explicacoes")
    if not isinstance(explicacoes, list) or len(explicacoes) != len(opcoes):
        explicacoes = None
    ordem = list(range(len(opcoes)))
    random.shuffle(ordem)
    questao["opcoes"] = [opcoes[i] for i in ordem]
    questao["correta"] = ordem.index(correta)
    questao["explicacoes"] = [str(explicacoes[i]) for i in ordem] if explicacoes else []
    return questao


def gerar_questao(trecho: str, contexto: str = "") -> dict:
    if config.LLM_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        try:
            return _embaralhar(_gerar_anthropic(trecho, contexto))
        except Exception:
            return _embaralhar(_gerar_mock(trecho))
    return _embaralhar(_gerar_mock(trecho))


def _topico_anthropic(titulo: str, conteudo: str) -> dict:
    import anthropic

    cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = cliente.messages.create(
        model=config.LLM_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": PROMPT_TOPICO.format(titulo=titulo or "(sem título)", conteudo=conteudo)}],
    )
    texto = msg.content[0].text
    bruto = re.search(r"\{.*\}", texto, re.S)
    dados = json.loads(bruto.group(0)) if bruto else {}
    if not dados.get("opcoes") or not dados.get("explicacao"):
        raise ValueError("resposta do modelo incompleta")
    return dados


def gerar_topico(titulo: str, conteudo: str) -> dict:
    if config.LLM_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        try:
            return _embaralhar(_topico_anthropic(titulo, conteudo))
        except Exception:
            pass
    questao = _embaralhar(_gerar_mock(conteudo))
    explicacao = f"{titulo}\n\n{conteudo}" if titulo else conteudo
    return {
        "explicacao": explicacao,
        "pergunta": questao["pergunta"],
        "opcoes": questao["opcoes"],
        "correta": questao["correta"],
        "justificativa": questao["justificativa"],
    }


def disponivel() -> bool:
    if config.LLM_PROVIDER == "anthropic":
        return bool(config.ANTHROPIC_API_KEY)
    if config.LLM_PROVIDER == "gemini":
        return bool(config.GEMINI_API_KEY)
    return False


def _partes_gemini(prompt: str, imagem: tuple[bytes, str] | None) -> list[dict]:
    if not imagem:
        return [{"text": prompt}]
    import base64

    dados, mime = imagem
    return [{"inline_data": {"mime_type": mime, "data": base64.b64encode(dados).decode("ascii")}}, {"text": prompt}]


class LimiteLLM(RuntimeError):
    """Cota do provedor esgotada: não adianta insistir agora."""


class LimiteDiarioLLM(LimiteLLM):
    """Cota diária esgotada: só renova no dia seguinte."""


def _gemini(prompt: str, max_tokens: int, json_mode: bool = True, schema: dict | None = None,
            modelo: str | None = None, esperar_limite: bool = True,
            imagem: tuple[bytes, str] | None = None, temperatura: float = 0.8) -> str:
    import urllib.request
    import urllib.error

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo or config.GEMINI_MODEL}:generateContent"
    gen = {
        "temperature": temperatura,
        "maxOutputTokens": max(max_tokens, 2048),
        "thinkingConfig": {"thinkingBudget": 0},
    }
    if json_mode:
        gen["responseMimeType"] = "application/json"
        if schema:
            gen["responseSchema"] = schema
    corpo = json.dumps({
        "contents": [{"parts": _partes_gemini(prompt, imagem)}],
        "generationConfig": gen,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=corpo,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": config.GEMINI_API_KEY,
        },
    )
    import time

    nome_modelo = modelo or config.GEMINI_MODEL
    dados = None
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode("utf-8", "ignore")
            if e.code == 429:
                _registrar_falha(f"429 do Gemini ({nome_modelo})", detalhe)
                if "PerDay" in detalhe:
                    # Cota DIÁRIA: esperar segundos não resolve, falha na hora.
                    raise LimiteDiarioLLM(
                        f"a cota diária gratuita do Gemini ({nome_modelo}) acabou; ela renova amanhã. "
                        "Para continuar hoje, troque GEMINI_MODEL no .env (ex.: gemini-2.5-flash-lite) e reinicie o backend."
                    ) from None
            if e.code in (429, 503) and tentativa < 2 and esperar_limite:
                # Limite por minuto (ou servidor ocupado): espera um pouco e tenta de novo.
                m = re.search(r'"retryDelay":\s*"(\d+)', detalhe)
                espera = int(m.group(1)) if m else 5 * (tentativa + 1)
                time.sleep(min(max(espera, 2), 15))
                continue
            if e.code == 429:
                raise LimiteLLM("limite por minuto da camada gratuita do Gemini atingido (429). Aguarde um minuto e tente de novo.") from None
            raise RuntimeError(f"HTTP {e.code}: {detalhe[:200]}") from None
    candidato = (dados.get("candidates") or [{}])[0]
    partes = candidato.get("content", {}).get("parts", [])
    texto = "".join(p.get("text", "") for p in partes)
    if not texto:
        raise ValueError(f"resposta vazia (finishReason={candidato.get('finishReason')})")
    return texto


def _completar(prompt: str, max_tokens: int = 900, json_mode: bool = True, schema: dict | None = None,
               leve: bool = False) -> str:
    if config.LLM_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        import anthropic

        cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = cliente.messages.create(
            model=config.LLM_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    if config.LLM_PROVIDER == "gemini" and config.GEMINI_API_KEY:
        if leve:  # tarefa leve: modelo menor e sem ficar esperando o limite gratuito
            return _gemini(prompt, max_tokens, json_mode, schema, modelo=config.GEMINI_MODEL_LEVE, esperar_limite=False)
        return _gemini(prompt, max_tokens, json_mode, schema)
    raise RuntimeError("Nenhum LLM configurado")


PROMPT_ESTUDO = """Você é um professor preparando material de estudo para um aluno, com base no conteúdo de PDFs da disciplina.

Perfil do aluno:
- Nível de conhecimento na matéria: {nivel}
- Objetivo do estudo: {objetivo}
- Tempo disponível: {tempo}

Adapte o material ao perfil: ajuste a linguagem ao nível, o foco ao objetivo e o tamanho ao tempo disponível.

Produza um material de estudo em português assim:
1. Uma explicação clara e didática do conteúdo, em prosa, organizada em seções com títulos curtos.
2. No final, uma seção "Pontos-chave" com os principais itens, um por linha.

Use TEXTO SIMPLES (sem markdown, sem asteriscos, sem #): cada título numa linha própria, e cada item de lista começando com "• ". Baseie-se SOMENTE no conteúdo abaixo.

CONTEÚDO:
{conteudo}"""


PROMPT_VISAO = """Esta imagem é uma página de um material didático em PDF; ela pode conter um ou vários slides.
Transcreva o CONTEÚDO da página em português, em texto simples, para servir de base a questões de estudo:
- Para cada slide ou bloco, escreva o título numa linha e os tópicos em linhas começando com "• ", na ordem de leitura.
- Se uma figura, ilustração, gráfico ou tabela transmitir informação (um exemplo, uma situação, dados), descreva-a em uma frase começando com "Figura: ". Ignore imagens só decorativas.
- IGNORE elementos de layout: datas, numeração de slides e páginas, cabeçalhos e rodapés, logotipos, nomes de instituição, créditos e marcas d'água.
- Não invente, não complete e não explique nada que não esteja na imagem. Não use markdown.
- Se a página não tiver conteúdo didático (em branco ou só decoração), responda apenas: SEM_CONTEUDO"""


def transcrever_pagina(imagem: bytes, mime: str = "image/jpeg") -> str:
    """Transcreve com um LLM multimodal uma página que só tem imagem (slides exportados
    como figura, handouts, digitalizações). Devolve "" se não houver conteúdo."""
    if config.LLM_PROVIDER == "anthropic" and config.ANTHROPIC_API_KEY:
        import anthropic
        import base64

        cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = cliente.messages.create(
            model=config.LLM_MODEL,
            max_tokens=2048,
            temperature=0,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime,
                                             "data": base64.b64encode(imagem).decode("ascii")}},
                {"type": "text", "text": PROMPT_VISAO},
            ]}],
        )
        texto = msg.content[0].text
    elif config.LLM_PROVIDER == "gemini" and config.GEMINI_API_KEY:
        texto = _gemini(PROMPT_VISAO, 2048, json_mode=False, modelo=config.GEMINI_MODEL_VISAO,
                        imagem=(imagem, mime), temperatura=0.1)
    else:
        raise RuntimeError("Nenhum LLM configurado")
    texto = (texto or "").strip()
    if texto.startswith("SEM_CONTEUDO"):
        return ""
    texto = re.sub(r"\*\*|__|^#+\s*", "", texto, flags=re.M)  # caso venha markdown mesmo assim
    return re.sub(r"^\s*[*-]\s+", "• ", texto, flags=re.M)


def gerar_material_estudo(conteudo: str, nivel: str, objetivo: str, tempo: str) -> str:
    prompt = PROMPT_ESTUDO.format(nivel=nivel, objetivo=objetivo, tempo=tempo, conteudo=conteudo[:24000])
    return _completar(prompt, 4096, json_mode=False)


DIRETRIZES_QUESTAO = """Regras para a questão:
- Avalie a COMPREENSÃO de um conceito, definição, relação, propriedade ou procedimento do conteúdo. Prefira questões de aplicar, interpretar, comparar ou calcular a questões de memorização literal.
- Se o trecho traz um exemplo resolvido (valores numéricos, passo a passo), prefira uma questão que exija executar ou interpretar um passo desse procedimento (ex.: "dado x=-2, y=5, z=-4, quanto vale ∂f/∂x?").
- NÃO pergunte "qual é o objetivo/propósito/finalidade" de um exemplo, slide ou seção, nem "o que é apresentado/descrito".
- Pergunte SOMENTE sobre o que o trecho afirma ou demonstra explicitamente. Se um conceito aparece apenas como rótulo, título ou legenda de figura, sem explicação, NÃO crie uma definição para ele.
- O enunciado deve ser autossuficiente: o aluno NÃO verá o trecho ao responder. Não use expressões como "segundo o trecho", "de acordo com o material", "conforme o texto", "nos slides", "no PDF" ou "apresentado no material".
- PROIBIDO perguntar sobre: autor, professor, instituição, disciplina, datas, título do documento, número de slide/página/trecho ou bibliografia.
- O texto vem de extração automática de PDF e pode ter ruído (numeração de slides, cabeçalhos/rodapés, repetições, fórmulas quebradas). Ignore o ruído. Escreva fórmulas de forma legível (ex.: ∂f/∂x = z).
- 4 alternativas da mesma natureza, com tamanho e nível de detalhe parecidos: a correta NÃO pode ser a mais longa nem a mais detalhada. Exatamente 1 correta. Distratores refletem erros conceituais plausíveis de um estudante, nunca absurdos. Não use "todas/nenhuma das anteriores" nem "apenas/somente" para enfraquecer distratores.
- "justificativa": explicação breve (1 a 2 frases, até ~250 caracteres), em linguagem de professor, do conceito por trás da resposta correta: explique o PORQUÊ (o mecanismo, a razão), sem repetir o texto da alternativa e sem começar com "Correta"/"A resposta certa é". Deve ser coerente com a alternativa correta e não pode citar "o trecho" nem "o material".
- "explicacoes": lista com 4 frases curtas, na MESMA ordem de "opcoes", dizendo por que cada alternativa está certa ou errada (para as erradas, aponte o equívoco conceitual).
- "evidencia": copie LITERALMENTE do trecho a menor passagem (no máximo 200 caracteres) que sustenta a resposta correta. Ela precisa de fato justificar a resposta; uma fórmula ou rótulo solto não serve.
- Antes de responder, verifique: a resposta correta é sustentada pela evidência? Cada distrator é inequivocamente errado à luz do trecho? Se não, reformule; se não for possível, marque "pular": true.
- Se o trecho não tiver conteúdo técnico avaliável (capa, sumário, referências, agradecimentos, apenas nomes/metadados ou apenas fórmulas sem explicação), não invente: marque "pular": true."""

PROMPT_PERGUNTA_CONTEUDO = """Você é um professor criando uma questão de estudo a partir de um material didático.
Com base APENAS no trecho abaixo, crie 1 questão de múltipla escolha em português.

{diretrizes}

TRECHO:
{conteudo}

Responda SOMENTE com um JSON válido, em um destes formatos:
{{"pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "...", "explicacoes": ["...", "...", "...", "..."], "evidencia": "..."}}
{{"pular": true}}"""


class TrechoSemConteudo(ValueError):
    pass


# Campos obrigatórios e em ordem: sem isso o Gemini pode devolver itens quase vazios.
# "pular" vem por último, como veredito da autochecagem depois de redigir a questão.
_CAMPOS_QUESTAO = ["pergunta", "opcoes", "correta", "justificativa", "explicacoes", "evidencia", "pular"]
_SCHEMA_QUESTAO_PROPS = {
    "pergunta": {"type": "STRING"},
    "opcoes": {"type": "ARRAY", "items": {"type": "STRING"}},
    "correta": {"type": "INTEGER"},
    "justificativa": {"type": "STRING"},
    "explicacoes": {"type": "ARRAY", "items": {"type": "STRING"}},
    "evidencia": {"type": "STRING"},
    "pular": {"type": "BOOLEAN"},
}
SCHEMA_QUESTAO = {
    "type": "OBJECT",
    "properties": _SCHEMA_QUESTAO_PROPS,
    "required": _CAMPOS_QUESTAO,
    "propertyOrdering": _CAMPOS_QUESTAO,
}
SCHEMA_LOTE = {
    "type": "OBJECT",
    "properties": {
        "questoes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"trecho": {"type": "INTEGER"}, **_SCHEMA_QUESTAO_PROPS},
                "required": ["trecho", *_CAMPOS_QUESTAO],
                "propertyOrdering": ["trecho", *_CAMPOS_QUESTAO],
            },
        }
    },
    "required": ["questoes"],
}


def _registrar_falha(motivo: str, conteudo: str) -> None:
    """Guarda respostas problemáticas do LLM em logs/llm_falhas.log para diagnóstico."""
    try:
        import datetime
        import os

        os.makedirs("logs", exist_ok=True)
        with open(os.path.join("logs", "llm_falhas.log"), "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.datetime.now().isoformat(timespec='seconds')} | {motivo}\n{conteudo[:8000]}\n")
    except Exception:
        pass


_ultima_resposta = {"texto": ""}


def _json_llm(prompt: str, max_tokens: int, schema: dict, tentativas: int = 2, leve: bool = False) -> dict:
    """Chama o LLM e interpreta o JSON; se vier malformado, tenta de novo."""
    erro = None
    for _ in range(tentativas):
        texto = _completar(prompt, max_tokens, schema=schema, leve=leve)
        bruto = re.search(r"\{.*\}", texto, re.S)
        if not bruto:
            erro = ValueError("o modelo não retornou JSON")
            continue
        try:
            dados = json.loads(bruto.group(0))
            _ultima_resposta["texto"] = texto
            return dados
        except json.JSONDecodeError as e:
            _registrar_falha(f"JSON inválido: {e.msg}", texto)
            erro = ValueError(f"JSON inválido do modelo ({e.msg})")
    raise erro


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def _evidencia_valida(evidencia: str, chunk: str) -> str:
    """Mantém a evidência só se ela realmente existir no trecho (ou quase)."""
    ev = _normalizar(evidencia)
    ch = _normalizar(chunk)
    if not ev or not ch:
        return ""
    if ev.lower() in ch.lower():
        return ev
    import difflib

    m = difflib.SequenceMatcher(None, ch.lower(), ev.lower(), autojunk=False).find_longest_match(0, len(ch), 0, len(ev))
    if m.size >= max(30, int(0.6 * len(ev))):
        return ch[m.a:m.a + m.size].strip()
    return ""


# Perguntas sobre metadados do documento: descartadas.
_ENUNCIADO_PROIBIDO = re.compile(
    r"\b(?:autor(?:es|a)?|obras?|livros?|refer[êe]ncias? bibliogr|bibliografia|"
    r"fontes? adaptad|slides? adaptad|professor(?:es|a)?|universidade|institui[çc][ãa]o|editora|"
    r"objetivo principal|prop[óo]sito principal)\b",
    re.I,
)
# Perguntas sobre o layout do PDF ou sobre a própria tarefa (datas de impressão,
# numeração de slides, "trechos do material"): descartadas.
_ENUNCIADO_LAYOUT = re.compile(
    r"\b(?:qual (?:é |e )?(?:a )?data|(?:qual|quais) das datas|datas? (?:indicad|que aparec|no in[íi]cio)|"
    r"numera[çc][ãa]o d[eo]s? (?:slides?|p[áa]ginas?)|n[úu]mero d[oe]s? (?:slides?|p[áa]ginas?|trechos?)|"
    r"trechos? do material|cabe[çc]alhos?|rodap[ée]s?|criar quest[õo]es)\b",
    re.I,
)
# Muletas que remetem ao documento: removidas do enunciado (a questão continua valendo).
_MULETAS = re.compile(
    r",?\s*(?:de acordo com|segundo|conforme(?: indicado| descrito| apresentado)?(?: n)?)\s*"
    r"(?:o |a |os |as )?(?:material|texto|trecho|slides?|pdf|conte[úu]do|descrito)\b"
    r"|,?\s*(?:apresentad[ao]s?|descrit[ao]s?|indicad[ao]s?|mencionad[ao]s?)\s+n[oa]s?\s+(?:material|texto|trecho|slides?|pdf)\b"
    r"|,?\s*conforme descrito\b",
    re.I,
)


def _limpar_enunciado(pergunta: str) -> str:
    p = _MULETAS.sub("", pergunta)
    p = re.sub(r"\s+([?.,])", r"\1", p)
    p = re.sub(r"^[\s,;:]+", "", p)
    p = re.sub(r"\s{2,}", " ", p).strip()
    return p[:1].upper() + p[1:] if p else p


def _questao_valida(q: dict, chunk: str) -> dict:
    if q.get("pular"):
        raise TrechoSemConteudo("trecho sem conteúdo avaliável")
    q["pergunta"] = _limpar_enunciado(q.get("pergunta", ""))
    if _ENUNCIADO_PROIBIDO.search(q["pergunta"]) or _ENUNCIADO_LAYOUT.search(q["pergunta"]):
        _registrar_falha("enunciado sobre metadados descartado", q.get("pergunta", ""))
        raise TrechoSemConteudo("enunciado sobre metadados")
    if not q.get("pergunta") or not q.get("opcoes") or len(q["opcoes"]) < 2:
        raise ValueError("resposta do modelo inválida")
    q["evidencia"] = _evidencia_valida(q.get("evidencia", ""), chunk)
    return _embaralhar(q)


def pergunta_llm(conteudo: str) -> dict:
    prompt = PROMPT_PERGUNTA_CONTEUDO.format(diretrizes=DIRETRIZES_QUESTAO, conteudo=remover_referencias(conteudo)[:6000])
    dados = _json_llm(prompt, 2000, SCHEMA_QUESTAO)
    return _questao_valida(dados, conteudo)


def gerar_pergunta_conteudo(conteudo: str) -> dict:
    return pergunta_llm(conteudo)


PROMPT_LOTE = """Você é um professor criando questões de estudo a partir de um material didático.
Para CADA trecho numerado abaixo, crie 1 questão de múltipla escolha em português, respondível apenas com o conteúdo daquele trecho. Cada questão deve tratar de um conceito diferente; não repita a mesma ideia entre questões.

{diretrizes}

TRECHOS:
{trechos}

Responda SOMENTE com um JSON válido, com um item por trecho, indicando o número do trecho em "trecho":
{{"questoes": [{{"trecho": 1, "pergunta": "...", "opcoes": ["...", "...", "...", "..."], "correta": 0, "justificativa": "...", "explicacoes": ["...", "...", "...", "..."], "evidencia": "..."}}, {{"trecho": 2, "pular": true}}]}}"""


def perguntas_lote(conteudos: list[str]) -> list[tuple[int, dict]]:
    """Retorna pares (índice do trecho, questão); trechos pulados ou inválidos ficam de fora."""
    if not conteudos:
        return []
    trechos = "\n\n".join(f"[{i + 1}] {remover_referencias(c)[:1500]}" for i, c in enumerate(conteudos))
    prompt = PROMPT_LOTE.format(diretrizes=DIRETRIZES_QUESTAO, trechos=trechos)
    dados = _json_llm(prompt, 8000, SCHEMA_LOTE)
    saida = []
    usados = set()
    for pos, q in enumerate(dados.get("questoes", [])):
        try:
            idx = int(q.get("trecho", pos + 1)) - 1
        except (TypeError, ValueError):
            idx = pos
        if not 0 <= idx < len(conteudos) or idx in usados:
            continue
        try:
            saida.append((idx, _questao_valida(q, conteudos[idx])))
            usados.add(idx)
        except ValueError:
            continue
    if not saida:
        _registrar_falha("lote sem questões válidas", _ultima_resposta["texto"])
        raise ValueError("o modelo não retornou questões válidas")
    return saida


PROMPT_AREA = """Classifique o material didático abaixo em UMA área do conhecimento ampla, do jeito que um estudante organizaria seus estudos (ex.: Inteligência Artificial, Cálculo, Redes de Computadores, Banco de Dados, Estatística, Culinária, História).
- Use de 1 a 4 palavras, em português, com iniciais maiúsculas.
- Prefira a área ampla à específica (ex.: "Inteligência Artificial" em vez de "Backpropagation").
- Se uma das áreas já existentes servir, repita EXATAMENTE o nome dela.

ÁREAS JÁ EXISTENTES: {existentes}

TÍTULO DO MATERIAL: {titulo}

INÍCIO DO CONTEÚDO:
{conteudo}

Responda SOMENTE com um JSON válido: {{"area": "..."}}"""

SCHEMA_AREA = {"type": "OBJECT", "properties": {"area": {"type": "STRING"}}, "required": ["area"]}


def classificar_area(titulo: str, conteudo: str, existentes: list[str]) -> str:
    prompt = PROMPT_AREA.format(
        existentes=", ".join(existentes) if existentes else "(nenhuma)",
        titulo=titulo or "(sem título)",
        conteudo=remover_referencias(conteudo)[:3000],
    )
    area = re.sub(r"\s+", " ", str(_json_llm(prompt, 200, SCHEMA_AREA, tentativas=1, leve=True).get("area", ""))).strip(" .\"'")[:60]
    if not area:
        raise ValueError("o modelo não retornou uma área")
    from .gamificacao import chave_area

    for e in existentes:  # reaproveita a grafia de uma área já existente (ignora acento e maiúsculas)
        if chave_area(e) == chave_area(area):
            return e
    return area


def extrair_topicos(texto: str) -> list[tuple[str, str]]:
    if not disponivel():
        return []
    import anthropic

    cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = cliente.messages.create(
        model=config.LLM_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": PROMPT_EXTRAIR.format(conteudo=texto[:16000])}],
    )
    bruto = re.search(r"\{.*\}", msg.content[0].text, re.S)
    dados = json.loads(bruto.group(0)) if bruto else {}
    saida = [
        (t.get("titulo", "").strip(), t.get("explicacao", "").strip())
        for t in dados.get("topicos", [])
        if t.get("explicacao", "").strip()
    ]
    if not saida:
        raise ValueError("o modelo não retornou tópicos válidos")
    return saida


def gerar_pergunta(titulo: str, explicacao: str) -> dict:
    if disponivel():
        try:
            import anthropic

            cliente = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            msg = cliente.messages.create(
                model=config.LLM_MODEL,
                max_tokens=900,
                messages=[{"role": "user", "content": PROMPT_PERGUNTA.format(titulo=titulo or "(tópico)", explicacao=explicacao)}],
            )
            bruto = re.search(r"\{.*\}", msg.content[0].text, re.S)
            dados = json.loads(bruto.group(0)) if bruto else {}
            if dados.get("opcoes"):
                return _embaralhar(dados)
        except Exception:
            pass
    return _embaralhar(_gerar_mock(explicacao))
