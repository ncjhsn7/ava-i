# Análise: texto da proposta × protótipo desenvolvido

Comparação entre o que está escrito no TCC e o que está, de fato, implementado no código (backend FastAPI + frontend Angular). Para cada item: estado e recomendação (ajustar **texto** ou **código**).

Legenda: ✅ alinhado · ⚠️ parcial/diferente · ❌ no texto, não no código · ➕ no código, não no texto.

---

## 1. Pontos no TEXTO que divergem do CÓDIGO

| Item na proposta | O que o código faz | Estado | Recomendação |
|---|---|---|---|
| **Banco PostgreSQL** (Cap. 4.2 e 5.2) | Usa **SQLite** (`sqlite:///./ava.db`, via SQLAlchemy) | ❌ | **Texto.** Trocar "PostgreSQL" por "SQLite" (ou justificar: SQLite basta para a PoC; Postgres ficaria como evolução). |
| **LLM: Claude (Anthropic) ou GPT (OpenAI)** (4.3 original) | Usa **Google Gemini** (`gemini-2.5-flash`); há também suporte a Anthropic, mas o ativo é o Gemini | ⚠️ | **Texto.** Na versão reescrita já está genérico ("modelo acessado por API"); se citar o modelo, citar Gemini. |
| **Autenticação e gestão de usuários** (4.2: "autenticação"; 5.2: persistir "usuários") | **Não há** login nem tabela de usuários. Tabelas: cadeiras, materiais, questões, sessões, telemetria, respostas | ❌ | **Texto** (para a PoC) ou **código**. Remover "autenticação/usuários" do escopo da PoC, ou implementar um login simples. |
| **Professor revisa, aprova/edita e publica as questões** (Módulo 1) | **Não existe** fluxo de aprovar/publicar. O professor sobe PDFs e pode "pré-visualizar" uma questão de exemplo; as questões são geradas na hora durante a sessão | ❌ | **Decisão importante.** Ou reimplementar a curadoria (aprovar/publicar), ou reescrever o Módulo 1 para refletir o fluxo atual (geração sob demanda). |
| **Perguntas pré-geradas na preparação** (tabela de riscos; QP2 reescrita) | Geradas **em tempo real** durante a sessão (endpoint `/lote`, em lotes de 5, via Gemini) | ❌ | **Texto + decisão.** Hoje o código contradiz a mitigação de custo. Ou voltar a pré-gerar, ou assumir a geração em tempo real no texto (e tratar o custo de outra forma). |
| **Dois cenários: Restrito e Expandido (PDF + fontes externas)** (4.3, Fase 3) | Só o **Restrito** (gera apenas do PDF). Não há busca externa | ❌ | **Texto** (mover Expandido para trabalho futuro) **ou código** (implementar fontes complementares controladas pelo professor). |
| **Questões "de múltipla escolha e abertas curtas"** (Módulo 1) | Só **múltipla escolha** | ⚠️ | **Texto.** Remover "abertas curtas", ou implementar. |
| **focusScore: calibração de 30 segundos** (4.1) | Calibração de **5 segundos** | ❌ | **Texto.** Trocar 30 s por 5 s (valor real no código). |
| **Degradação graciosa: teste sintético de latência, desabilita se > 250 ms** (4.1.1) | O YOLO é apenas **tentado**; se o modelo/runtime falhar ao carregar, ele é desligado com aviso. **Não há** benchmark sintético nem limiar de 250 ms | ⚠️ | **Texto.** Descrever a degradação como ela é (YOLO opcional, desligado em caso de falha de carregamento/hardware), sem o número 250 ms — que, aliás, o orientador já pediu referência. |
| **Pose da cabeça** (genérico) | Estimada por **geometria dos pontos** (posição do nariz em relação a olhos/queixo e bordas), não por matriz de transformação | ✅/⚠️ | **Texto** (opcional). Conceitualmente alinhado; se for detalhar, descrever o método por landmarks. |
| **Condição B: leitura intercalada com perguntas nos checkpoints** (6.2) | O app tem **modos separados**: questionário contínuo OU material de estudo. Não há um fluxo único "leitura + checkpoints" | ❌ | **Decisão de avaliação.** Para o experimento A/B funcionar como escrito, é preciso um modo "leitura com checkpoints". Ou implementá-lo, ou redesenhar as condições A/B conforme o que existe. |

---

## 2. Pontos no CÓDIGO que NÃO estão no TEXTO

| Recurso implementado | Descrição | Recomendação |
|---|---|---|
| ➕ **Entidade "Cadeira"** | Os materiais são agrupados por cadeira (disciplina); o aluno escolhe a cadeira e depois os PDFs | **Texto.** Incluir a cadeira no modelo de dados e no fluxo (Módulo 2). |
| ➕ **"Material de estudo" gerado por IA** | Além do questionário, o aluno gera um resumo/explicação do conteúdo, **adaptado** ao nível de conhecimento, objetivo e tempo disponível | **Texto.** É uma contribuição relevante; vale descrever (e ajuda a justificar o uso do LLM além das questões). |
| ➕ **Questionário "endless" + seleção de PDFs** | O aluno marca quais PDFs praticar e responde a um fluxo contínuo de questões geradas em lote | **Texto.** Descrever esse modo (difere do "checkpoints durante a leitura"). |
| ➕ **Revisão dos erros** | O aluno refaz as questões que errou na cadeira (prática de recuperação dos erros) | **Texto.** Boa adição pedagógica; citar na proposta/avaliação. |
| ➕ **Detalhes reais do focusScore** | Janela deslizante de **8 s**, **período de graça de 2,5 s** para distrações curtas, limiar de olho = **0,72 × mediana** do EAR calibrado | **Texto.** Atualizar a definição do focusScore (4.1) com esses parâmetros torna a métrica reprodutível. |
| ➕ **Detecção de "olhar para baixo/fora da tela"** | Pega o celular no colo (fora da câmera) via queda da pose, não só pelo YOLO | **Texto.** Reforça a robustez do indicador; vale mencionar. |

---

## 3. Pontos ALINHADOS (✅)

- Frontend em **Angular SPA + TypeScript**.
- **MediaPipe** (FaceLandmarker) para marcos faciais e **EAR** para abertura dos olhos.
- **YOLOv8-nano em ONNX via ONNX Runtime Web** para detecção de smartphone.
- **Processamento de visão 100% no cliente**; o servidor recebe só métricas agregadas (privacy by design).
- **Telemetria periódica** (foco, eventos de celular, modo) enviada a cada poucos segundos.
- **Painel** que cruza engajamento (foco/tempo/eventos) com desempenho (acertos por material).
- **RAG**: extração + fragmentação (LangChain text splitter) + **ChromaDB** + geração condicionada ao contexto.

---

## 4. Resumo executivo e prioridades

Como o documento é uma **proposta (TC1)**, alguma divergência é natural: o texto descreve o plano e o protótipo evoluiu. Para a versão final (TC2), o ideal é alinhar. Sugestão de prioridade:

**Correções rápidas de texto (baixo esforço, evitam contradição com a demo):**
1. PostgreSQL → SQLite.
2. Calibração 30 s → 5 s.
3. Remover o limiar de 250 ms; descrever a degradação como ela é.
4. LLM: citar Gemini (ou manter genérico).
5. Remover "questões abertas curtas" (só múltipla escolha) ou marcar como futuro.

**Decisões de fundo (texto + possivelmente código):**
6. **Curadoria do professor (aprovar/publicar)** e **pré-geração das perguntas**: hoje o código faz geração em tempo real, sem aprovação. Decidir se reimplementa (mais fiel à proposta) ou se reescreve a proposta para o fluxo atual.
7. **Cenário Expandido**: implementar (fontes controladas pelo professor) ou mover para trabalho futuro.
8. **Condição experimental B** (leitura + checkpoints): hoje não existe nesse formato. Ajustar o desenho do experimento ao que o app faz, ou criar o modo.

**Acréscimos a documentar (o código tem, o texto não):**
9. Cadeira, material de estudo adaptativo, questionário endless, revisão dos erros, e os parâmetros reais do focusScore (janela 8 s, graça 2,5 s, limiar 0,72×mediana).
