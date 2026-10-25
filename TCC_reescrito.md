# RESUMO

O ensino remoto e híbrido tornou os Ambientes Virtuais de Aprendizagem (AVAs) parte da rotina de estudo, mas o estudo autônomo nesses ambientes esbarra em dois problemas recorrentes: a atenção se dispersa durante a leitura e falta um mecanismo que verifique, na hora, se o conteúdo foi de fato compreendido. Este trabalho propõe um AVA inteligente que reúne três módulos. O primeiro recebe o material do professor e gera, automaticamente, questões formativas ancoradas nesse material, usando a técnica de *Retrieval-Augmented Generation* (RAG), na qual um modelo de linguagem responde guiado por trechos recuperados do próprio conteúdo, em vez de "inventar" a resposta. O segundo estima, localmente no navegador do estudante, indicadores de engajamento visual a partir da câmera, combinando o estado dos olhos e a direção da cabeça com a detecção de smartphones no campo de visão. O terceiro entrega ao professor um painel analítico que cruza esses indicadores de engajamento com o desempenho nas questões. Quando o computador do estudante não consegue rodar o modelo de detecção de objetos, o sistema continua funcionando apenas com os indicadores mais leves, comportamento que chamamos de degradação graciosa, ou seja, o recurso pesado é desligado sem derrubar a aplicação. A proposta detalha o problema, o referencial teórico, a arquitetura, a metodologia, o plano de avaliação (condicionado à aprovação do Comitê de Ética em Pesquisa) e o cronograma.

**Palavras-Chave:** ambiente virtual de aprendizagem, modelos de linguagem, geração aumentada por recuperação, visão computacional, engajamento, avaliação formativa, LGPD.

---

# 1. INTRODUÇÃO

A transformação digital do ensino, acelerada pela pandemia de COVID-19, tornou os Ambientes Virtuais de Aprendizagem (AVAs) uma infraestrutura padrão na educação presencial, híbrida e remota [HBF19, Bat19]. Esse movimento ampliou o acesso ao material didático, mas transferiu ao estudante uma carga maior de autorregulação: cabe a ele decidir quando, como e com que profundidade estudar. Ao mesmo tempo, técnicas de Inteligência Artificial (IA), em especial de Processamento de Linguagem Natural (PLN) e de Visão Computacional (VC), deixaram de ser promessa distante e passaram a operar dentro de plataformas educacionais, apoiando tanto a personalização do ensino quanto o acompanhamento do engajamento [Van11, HBF19].

Mesmo com AVAs maduros, o estudo autônomo enfrenta dois gargalos. O primeiro é a dispersão da atenção: o estudante alterna constantemente entre o material e estímulos externos, sobretudo o celular, o que prejudica a aprendizagem [KDB17, Bat19]. O segundo é a passividade do material: o aluno lê PDFs e slides sem nenhum ponto de verificação imediato, o que alimenta uma sensação de domínio que nem sempre corresponde à retenção real [DDD17].

Do lado do professor, somam-se outros dois problemas. Produzir avaliação formativa contínua não escala: extrair manualmente os conceitos-chave de cada material para gerar exercícios é trabalhoso e raramente acompanha o ritmo do semestre. E falta visibilidade sobre o processo: o professor recebe as notas, mas não enxerga onde a turma se dispersou nem qual material gerou mais dificuldade. Os Sistemas de Tutoria Inteligente (ITS) clássicos já mostraram que a tutoria assistida por computador pode produzir ganhos de aprendizagem próximos aos da tutoria humana individual [Van11], mas dependiam de regras escritas à mão, o que limitava sua escala. Os modelos de linguagem de grande porte (LLMs) [BMR+20, ZZL+23] e a arquitetura de RAG [LPP+20, GXG+23] mudam esse cenário: hoje é viável gerar perguntas formativas ancoradas no material do próprio professor, com risco controlado de erro, algo inviável nos tutores simbólicos da década passada.

Diante disso, este trabalho propõe um Ambiente Virtual de Aprendizagem Inteligente que reúne, numa única plataforma, a geração automática de avaliações formativas, a medição local de engajamento e um painel para o professor. As seções seguintes detalham os objetivos; o Capítulo 2 aprofunda os fundamentos teóricos que sustentam cada uma dessas escolhas.

## 1.1 Objetivos

O objetivo geral é propor, projetar e avaliar um Ambiente Virtual de Aprendizagem Inteligente que integre (i) a geração automática de avaliações formativas, por RAG, sobre o material do professor; (ii) a inferência local de indicadores de engajamento visual no navegador do estudante; e (iii) um painel analítico que permita ao professor cruzar engajamento e desempenho.

São objetivos específicos:

1. Revisar o estado atual sobre ITS, RAG aplicada à educação e medição automática de engajamento por VC.
2. Especificar a arquitetura da plataforma, discutindo de forma explícita as restrições de hardware no cliente e os requisitos de privacidade impostos pela Lei Geral de Proteção de Dados (LGPD) [Bra18].
3. Implementar uma Prova de Conceito (PoC) funcional dos três módulos.
4. Validar a PoC com estudantes voluntários, mediante aprovação do Comitê de Ética em Pesquisa (CEP) da PUCRS, usando métodos estatísticos adequados ao tamanho da amostra.

---

# 2. REFERENCIAL TEÓRICO

Este capítulo aprofunda os fundamentos que sustentam a proposta, indo além da motivação apresentada na introdução. A Seção 2.1 detalha os mecanismos da dispersão da atenção e o papel do automonitoramento da aprendizagem. A Seção 2.2 examina os Sistemas de Tutoria Inteligente, os LLMs e a arquitetura de RAG. A Seção 2.3 descreve como a visão computacional mede engajamento. A Seção 2.4 trata da privacidade e da conformidade com a LGPD.

## 2.1 Dispersão da atenção e automonitoramento da aprendizagem no estudo remoto

Estudar em ambientes digitais exige autorregulação, e a pesquisa mostra que essa autorregulação costuma ser superestimada. Kirschner e De Bruyckere [KDB17] desmontam o mito do "nativo digital": a crença de que jovens conseguem alternar sem custo entre estudar e usar aplicativos não se sustenta. Na prática, essa alternância contínua eleva a carga cognitiva (o esforço mental exigido para processar a informação) e degrada o desempenho. Bates [Bat19] descreve o *cyber-slacking*, isto é, o uso oportunista do dispositivo para fins não acadêmicos durante o estudo, e seu efeito sobre a memória de trabalho. Já D'Mello, Dieterle e Duckworth [DDD17] propõem um arcabouço para medir engajamento de forma automatizada, combinando sinais comportamentais (como postura e direção do olhar) com sinais afetivos.

Um conceito é central nesse debate: o automonitoramento da aprendizagem, ou seja, a capacidade do estudante de acompanhar e regular o próprio progresso, em poucas palavras, perceber o quanto se está de fato entendendo. O problema da leitura passiva está justamente nesse ponto: sem retorno, o aluno não detecta a própria distração nem as lacunas de compreensão. A literatura converge para uma solução prática: inserir feedback imediato e pontos de verificação ao longo do estudo funciona como gatilho de automonitoramento, ajudando o aluno a perceber e corrigir a dispersão antes que ela vire fracasso na prova [DDD17, Van11]. Essa constatação é o que motiva, na proposta, intercalar a leitura com perguntas formativas.

## 2.2 Sistemas de Tutoria Inteligente, LLMs e RAG

Sistemas de Tutoria Inteligente (ITS) ajustam o ritmo, a sequência e o conteúdo da instrução conforme o estado de conhecimento do aluno. A meta-análise de VanLehn [Van11] é a referência clássica: ela mostra que ITS bem projetados, que interagem com o aluno em granularidade fina (passo a passo), alcançam ganhos de aprendizagem comparáveis aos da tutoria humana individual, um resultado expressivo que ajudou a consolidar a área. Historicamente, porém, esses sistemas dependiam de bases de regras escritas e mantidas manualmente, o que tornava cara e lenta a sua expansão para novos conteúdos.

Os LLMs [BMR+20, ZZL+23] alteraram esse quadro ao permitir gerar conteúdo pedagógico, inclusive perguntas, a partir de instruções em linguagem natural. Há, contudo, um risco conhecido: operados sem ancoragem em uma fonte confiável, esses modelos produzem alucinações, isto é, afirmações que soam plausíveis, mas são falsas. A arquitetura de *Retrieval-Augmented Generation* (RAG), proposta por Lewis et al. [LPP+20] e sistematizada por Gao et al. [GXG+23], reduz esse risco: antes de responder, o sistema recupera de uma base externa os trechos mais relevantes e os entrega ao modelo como contexto, fazendo a geração se apoiar no material de referência em vez da memória do modelo.

O fluxo de RAG funciona em duas etapas. Primeiro, o texto-fonte é dividido em fragmentos (*chunks*) e convertido em vetores (*embeddings*) que preservam a proximidade de significado entre trechos parecidos; esses vetores ficam guardados em um banco vetorial. Depois, no momento da geração, a consulta também é convertida em vetor, os fragmentos mais próximos são recuperados, e o modelo produz a resposta condicionada a esse contexto [GXG+23]. Essa abordagem se encaixa bem no problema de gerar avaliações ancoradas em um material específico, pois nele a "verdade de referência" é um conjunto de documentos delimitado e conhecido, exatamente o material do professor.

## 2.3 Medição visual de engajamento

A análise automática de engajamento por VC se apoia em dois sinais: o rastreamento do rosto do estudante e a detecção de objetos no seu ambiente.

Ferramentas de rastreamento facial permitem estimar a posição da cabeça e o estado dos olhos. O MediaPipe Face Mesh [LTN+19, KAGG19], por exemplo, estima em tempo real centenas de pontos do rosto a partir de uma câmera comum; é leve o bastante para rodar no navegador e tem uso recorrente em estudos de engajamento educacional [AK24, DD25]. Sobre esses pontos, calcula-se a métrica *Eye Aspect Ratio* (EAR), proposta por Soukupová e Cech [SC16], que resume em um único número o grau de abertura dos olhos e serve de base para detectores de piscada e de sonolência amplamente validados [MdCMSL20]. Ao combinar o EAR com a direção da cabeça, é possível inferir, com confiabilidade razoável, se o estudante está olhando para a tela do material.

O segundo sinal é a presença de um smartphone no campo da câmera, indício forte de *cyber-slacking*. Para detectá-lo, emprega-se a família de modelos YOLO (*You Only Look Once*) [RDGF16], na versão YOLOv8 [JCQ23], que oferece variantes "nano", pequenas o suficiente para inferência no navegador via TensorFlow.js ou ONNX Runtime Web (as ferramentas de execução desses modelos no cliente, citadas no Capítulo 4). Vale registrar uma limitação desse arranjo: a inferência do YOLO no navegador depende do hardware do estudante e pode pesar em máquinas modestas [JCQ23]. A proposta trata explicitamente essa restrição no Capítulo 4, com um caminho de contingência.

## 2.4 Privacidade, LGPD e processamento no cliente

O monitoramento por câmera em contexto educacional é particularmente sensível: o vídeo de um estudante é dado pessoal e, no caso de menores, dado pessoal de criança e adolescente, com proteção reforçada pela LGPD (Lei nº 13.709/2018) [Bra18]. A literatura sobre IA educacional ética [HBF19, UNE21] recomenda o princípio de *privacy by design*, que consiste em projetar o sistema, desde o início, para coletar o mínimo e processar os dados o mais perto possível da origem, em vez de tratar a privacidade como política adicionada depois. Seguindo esse princípio, a proposta executa toda a visão computacional no próprio navegador do estudante: nenhum quadro de vídeo trafega pela rede, e o servidor recebe apenas métricas numéricas agregadas, como descrito no Capítulo 4.

---

# 3. PROPOSTA

Este capítulo apresenta o sistema em nível conceitual. A discussão técnica detalhada está no Capítulo 4 (arquitetura) e no Capítulo 5 (metodologia).

## 3.1 Visão geral do sistema

Propõe-se um Ambiente Virtual de Aprendizagem Inteligente (AVA-I), em formato de aplicação web, com três módulos integrados.

**Módulo 1: Geração de avaliações formativas (professor).** O professor envia os PDFs do material. O sistema fragmenta o texto, gera os *embeddings*, indexa-os em um banco vetorial e, por RAG, usa esse conteúdo como fonte para o modelo de linguagem gerar perguntas formativas (de múltipla escolha e abertas curtas) ancoradas em trechos específicos. O professor revisa, edita ou aprova cada questão e a publica, isto é, disponibiliza-a dentro da própria plataforma para que apareça nas sessões de estudo.

**Módulo 2: Sessão de estudo inteligente (estudante).** O estudante lê o material dentro do AVA-I, e a leitura é intercalada com as perguntas do Módulo 1. Com consentimento prévio, a câmera é usada localmente, no navegador, para estimar os indicadores de engajamento (estado dos olhos, direção da cabeça e presença de smartphone no campo da câmera). Nenhum quadro de vídeo é enviado ao servidor; apenas as métricas agregadas são transmitidas.

**Módulo 3: Painel analítico (professor).** De forma agregada e anonimizada, o professor visualiza em quais trechos a turma mais se dispersou, em quais perguntas houve mais erro e onde a queda de engajamento coincidiu com o baixo desempenho. Esses indícios ajudam o professor a revisar o próprio material.

## 3.2 Questões de pesquisa

A avaliação (Capítulo 6) é orientada por três questões de pesquisa.

**QP1: Engajamento e desempenho.** Existe relação entre o indicador agregado de engajamento visual e a taxa de acertos do estudante nas perguntas formativas geradas pela plataforma?

**QP2: Intervenção e dispersão.** Intercalar perguntas formativas durante a leitura reduz a frequência de uso do smartphone, em comparação com a leitura do mesmo material sem essas perguntas? Vale esclarecer o desenho: as perguntas não são geradas em tempo real durante a sessão. Elas são geradas e revisadas pelo professor na fase de preparação, ficam armazenadas e são apresentadas ao estudante em pontos de verificação predefinidos ao longo da leitura. Essa decisão também controla o custo de chamadas ao modelo (Capítulo 6).

**QP3: Usabilidade.** O processamento de visão computacional no navegador mantém a usabilidade da plataforma em nível aceitável? A usabilidade é medida pela *System Usability Scale* (SUS) [Bro96], um questionário padronizado cuja pontuação varia de 0 a 100; valores em torno de 68 são tomados como limiar de aceitabilidade conforme Bangor et al. [BKM08].

---

# 4. ARQUITETURA E INTEGRAÇÃO TECNOLÓGICA

A plataforma é organizada em três camadas, descritas a seguir. O critério arquitetural central é o *privacy by design* discutido na Seção 2.4 [HBF19, UNE21]: o processamento de imagem ocorre integralmente no cliente, e a rede transporta apenas dados agregados.

## 4.1 Frontend: Single Page Application

O frontend é uma *Single Page Application* (SPA), isto é, uma aplicação web que carrega uma única vez e atualiza o conteúdo sem recarregar a página. Ela é construída em Angular com TypeScript, escolhido pela arquitetura de componentes e pela tipagem forte, convenientes para compor no cliente módulos de IA relativamente pesados. Sobre essa base rodam dois modelos de visão computacional:

- **MediaPipe Face Mesh** [LTN+19, KAGG19], via a biblioteca MediaPipe Tasks for Web, para extrair os pontos faciais em tempo real. Sobre esses pontos, o cliente calcula o EAR [SC16] e estima a direção da cabeça. A partir daí, deriva o indicador de engajamento, definido como a proporção do tempo, na janela observada, em que (i) o rosto é detectado, (ii) a cabeça está aproximadamente voltada para a tela e (iii) o EAR está acima de um limiar calibrado para cada usuário, em uma breve calibração no início da sessão.
- **YOLOv8-nano** [RDGF16, JCQ23], exportado para o formato ONNX e executado via ONNX Runtime Web, para detectar a classe "smartphone" no campo da câmera. Cada detecção registra um evento associado ao instante da sessão.

### 4.1.1 Tratamento explícito da limitação de hardware

A inferência do YOLO no navegador é sensível ao hardware do cliente. Para lidar com isso, a SPA faz um teste de viabilidade ao carregar: inicializa o modelo em uma amostra sintética e mede a latência. Se a latência ultrapassar um limiar definido empiricamente no piloto interno, ou se o navegador não dispuser de aceleração gráfica (WebGL/WebGPU) funcional, o módulo de detecção de smartphone é desligado de forma graciosa, e a sessão segue apenas com os indicadores faciais, mais leves. Esse modo degradado fica registrado nos metadados da sessão e é tratado na análise: sessões em modo degradado não entram na verificação da QP2.

## 4.2 Backend: API REST

O backend é construído em Python com FastAPI, escolhido pelo bom desempenho em entrada e saída assíncrona e pela validação de dados nativa, úteis para orquestrar chamadas a modelos de linguagem com latência variável. Suas responsabilidades são: (i) autenticação e gestão de sessões; (ii) recebimento da telemetria agregada, nunca de fluxos de vídeo; (iii) orquestração das chamadas ao módulo de RAG; (iv) persistência dos usuários, materiais, sessões e respostas; e (v) entrega dos dados consolidados ao painel do professor.

## 4.3 Módulo de IA generativa (RAG)

O módulo de RAG é implementado em Python, usando o LangChain para orquestrar a ingestão. Os PDFs do professor passam por extração de texto, fragmentação em *chunks* de tamanho configurável e geração de *embeddings* com modelos abertos. Os vetores são indexados em um banco vetorial (ChromaDB), e a geração das perguntas fica a cargo de um modelo de linguagem acessado por API, condicionado ao contexto recuperado.

Cabe um cuidado de escala: o índice vetorial cresce com a quantidade e o tamanho dos PDFs, e um corpus muito grande pode tornar a indexação e a busca custosas. Como medida, o índice é organizado por disciplina (uma coleção por material) e, no escopo da PoC, o corpus é deliberadamente delimitado, o que mantém o custo sob controle.

## 4.4 Fluxo de dados

A Figura [X] resume o fluxo descrito a seguir.

1. O professor envia o PDF; o backend aciona a ingestão e indexa o conteúdo no banco vetorial.
2. O estudante inicia a sessão; a SPA roda sempre o Face Mesh e tenta rodar o YOLO, se viável.
3. A cada intervalo de poucos segundos, a SPA envia ao backend um lote com o instante, o indicador de engajamento, a contagem de eventos de smartphone e o modo da sessão.
4. Em cada ponto de verificação, uma pergunta previamente gerada é apresentada; a resposta do aluno volta para o backend.
5. O painel consulta o backend para cruzar engajamento e desempenho.

---

# 5. METODOLOGIA

A pesquisa é aplicada, de abordagem quantitativa-qualitativa, e segue a *Design Science Research* (DSR) [HMPR04], uma metodologia voltada a resolver problemas reais por meio da construção e da avaliação de um artefato. Aqui, o artefato é uma instanciação: um protótipo funcional do AVA-I. Construí-lo e avaliá-lo é o que gera o conhecimento pretendido sobre a viabilidade e os limites da abordagem.

O desenvolvimento está organizado em quatro fases. Cada componente é avaliado de forma independente antes da avaliação integrada com usuários. Este capítulo descreve o processo; a descrição do artefato em si está nos Capítulos 3 e 4.

## 5.1 Fase 1: Revisão complementar e especificação

Aprofundamento do referencial em três frentes: ITS com LLMs (com foco em trabalhos posteriores a VanLehn [Van11]); medição automática de engajamento educacional (em particular D'Mello et al. [DDD17] e trabalhos recentes com Face Mesh [AK24, DD25]); e aspectos legais (LGPD aplicada à educação) [Bra18]. Ao fim da fase, a especificação técnica é congelada para guiar a implementação.

## 5.2 Fase 2: Backend e pipeline RAG

Construção da API em FastAPI, modelagem do banco (usuários, materiais, sessões, perguntas e respostas) e implementação do pipeline de RAG com LangChain e ChromaDB, combinação amplamente adotada na literatura aplicada de RAG [GXG+23], o que favorece a reprodutibilidade. A validação interna gera questões para três materiais de referência (capítulos de livros-texto abertos), com inspeção manual da qualidade pelos autores e revisão do orientador.

## 5.3 Fase 3: Frontend e módulos de VC

Desenvolvimento da SPA em Angular e integração do MediaPipe Face Mesh e do YOLOv8-nano via ONNX Runtime Web, escolhidos pela maturidade no navegador e pelo bom equilíbrio entre acurácia e latência no cliente, com a ressalva de hardware já discutida [LTN+19, JCQ23]. Nesta fase entram o teste de viabilidade de hardware e a degradação graciosa do Capítulo 4. Os limiares de EAR e de direção da cabeça são calibrados em um pequeno piloto interno (autores e voluntários informais), usado apenas para ajustar parâmetros, não para validar as questões de pesquisa.

## 5.4 Fase 4: Avaliação experimental controlada

Execução do protocolo do Capítulo 6, com aprovação prévia do CEP-PUCRS. A coleta ocorre fora do horário de aula, no ambiente doméstico do estudante, com sessões guiadas remotamente.

---

# 6. AVALIAÇÃO

## 6.1 Considerações éticas

Por envolver coleta de dados com seres humanos (estudantes voluntários, com captura de imagem, ainda que processada localmente), o projeto será submetido ao CEP-PUCRS, via Plataforma Brasil, antes de qualquer coleta. Estão previstos: protocolo de pesquisa, Termo de Consentimento Livre e Esclarecido (TCLE), descrição das medidas de minimização de risco (em especial, nenhum vídeo trafega pela rede e apenas métricas agregadas são armazenadas) e plano de descarte dos dados ao fim do projeto. A submissão ao CEP é condição para iniciar a Fase 4.

## 6.2 Desenho experimental

A avaliação usa um desenho intra-sujeitos: cada participante passa pelas duas condições e serve como seu próprio controle. A ordem das condições é contrabalanceada (parte começa por uma, parte pela outra) para diluir efeitos de ordem, aprendizagem e fadiga.

- **Condição A (controle):** leitura do material no AVA-I sem as perguntas formativas. A telemetria de engajamento roda em segundo plano.
- **Condição B (intervenção):** leitura de material equivalente (pareado em tamanho e dificuldade), com perguntas formativas inseridas nos pontos de verificação. Telemetria igual à da condição A.

Cada participante faz as duas sessões com pelo menos 24 horas de intervalo, em ordem aleatória e com materiais distintos, para evitar contaminação. Cada sessão dura de 30 a 40 minutos.

A escolha do desenho intra-sujeitos decorre do tamanho da amostra. Com poucos participantes, comparar cada pessoa consigo mesma elimina a variabilidade entre indivíduos (cada um lê de um jeito) e isola melhor o efeito da intervenção, o que aumenta o poder estatístico. Por isso não se adota um teste entre grupos independentes; Wohlin et al. [WRH+12] recomendam justamente esse arranjo quando o número de participantes é limitado.

## 6.3 Participantes

De 12 a 18 estudantes voluntários de Ciência da Computação ou áreas afins da PUCRS, maiores de 18 anos, com acesso a notebook com câmera. O recrutamento se dá por divulgação em turmas e canais oficiais, com anuência dos professores responsáveis. O intervalo amostral considera (i) o caráter exploratório do estudo; (ii) a literatura de testes de usabilidade [Nie00], segundo a qual os ganhos em descoberta de problemas decrescem após cerca de 15 participantes; e (iii) a heterogeneidade de hardware, que deve reduzir o número de sessões válidas para a QP2.

## 6.4 Indicadores

A plataforma extrai três indicadores quantitativos.

- **Engajamento visual:** proporção entre o tempo com rosto detectado, cabeça voltada para a tela e EAR acima do limiar individual, e a duração total da sessão (Capítulo 4).
- **Eventos de smartphone:** número de intervalos da sessão em que a classe "smartphone" foi detectada por pelo menos *k* quadros consecutivos. Aplicável apenas a sessões fora do modo degradado.
- **Taxa de acertos:** proporção de acertos nas perguntas formativas (condição B). Cada pergunta é revisada pelos autores e pelo orientador antes da sessão, para garantir o gabarito.

Coleta-se ainda um indicador de usabilidade: a SUS [Bro96], aplicada ao fim do experimento e interpretada conforme Bangor et al. [BKM08].

## 6.5 Análise estatística

Com a amostra prevista (n ≤ 18), não se pode assumir normalidade dos dados, o que torna inadequados os testes paramétricos clássicos, como o teste t e a correlação de Pearson [Fie13]. Adotam-se, portanto, testes não-paramétricos.

- **QP1 (engajamento e desempenho):** correlação de Spearman entre o engajamento visual e a taxa de acertos nas sessões da condição B, reportando o coeficiente, o p-valor e o intervalo de confiança por *bootstrap* (reamostragem dos próprios dados para estimar a incerteza).
- **QP2 (intervenção e dispersão):** teste de Wilcoxon dos postos sinalizados (pareado), comparando os eventos de smartphone de cada participante nas condições A e B (apenas sessões fora do modo degradado), com a estatística, o p-valor e o tamanho do efeito.
- **QP3 (usabilidade):** estatística descritiva da SUS (média, mediana e intervalo de confiança por *bootstrap*), comparada aos parâmetros de Bangor et al. [BKM08].

Os resultados são reportados com a ressalva de que o estudo é exploratório: o objetivo é gerar evidência preliminar sobre a viabilidade da abordagem, não generalizar para a população.

## 6.6 Avaliação do painel pelo docente

Em paralelo à avaliação com estudantes, o painel do professor passa por uma avaliação qualitativa própria.

- **Inspeção heurística** com 2 a 3 docentes conteudistas, usando as heurísticas de Nielsen [Nie94], para identificar problemas de usabilidade e de clareza analítica.
- **Entrevista semiestruturada** com cada docente, após usar o painel com dados reais (anonimizados) de uma turma simulada, abordando: clareza dos indicadores; utilidade percebida para revisar o material; confiança nas perguntas geradas; e intenção de uso futuro.
- **Análise de conteúdo** das entrevistas, segundo Bardin [Bar11], com codificação por dois autores e consenso por triangulação.

Essa etapa complementa a avaliação com estudantes e responde diretamente à pergunta de como saber se a plataforma é útil para o professor.

## 6.7 Riscos e mitigações

A Tabela 6.1 sintetiza os principais riscos e as mitigações previstas.

---

# 7. CRONOGRAMA

O TCC está estruturado em dois semestres. O primeiro (TC1) cobriu a proposta, a fundamentação e o início da implementação; o segundo (TC2) concentra a conclusão da implementação, a avaliação e a escrita final. Como o TC1 já estará concluído quando esta versão for avaliada, apresenta-se apenas o cronograma de TC2 (Tabela 7.1).

## 7.1 Marcos de decisão

- **Fim de setembro/2026:** backend e RAG funcionais, com geração de questões validadas em três materiais. Caso contrário, simplifica-se o cenário de geração mais complexo.
- **Fim de outubro/2026:** frontend e Face Mesh estáveis, e teste de viabilidade do YOLO no navegador concluído. Se a viabilidade for baixa na amostra recrutada, a QP2 é reportada como inconclusiva por restrição de hardware, e a avaliação concentra-se em QP1 e QP3.
- **Aprovação do CEP:** havendo atraso, a Fase 4 avança em modo de piloto interno (autores e 2 a 3 voluntários, sem coleta científica), enquanto a documentação do painel e a inspeção heurística com docentes seguem normalmente.

---

# 8. CONSIDERAÇÕES FINAIS

Esta proposta reúne, em uma única plataforma, três frentes: a geração automática de avaliações formativas por RAG, a medição local de engajamento por visão computacional e um painel analítico para o professor. A privacidade é tratada por arquitetura, com todo o processamento de imagem ocorrendo no navegador, e não como política acessória. As escolhas técnicas se apoiam no referencial do Capítulo 2 e, onde há restrições reais (em especial o custo de rodar o YOLO no navegador), a proposta as reconhece e prevê um caminho de degradação graciosa (Capítulo 4).

A avaliação (Capítulo 6) combina métodos quantitativos não-paramétricos, adequados ao tamanho da amostra, com métodos qualitativos junto a docentes, e está condicionada à aprovação do Comitê de Ética em Pesquisa. O cronograma (Capítulo 7) é compatível com os prazos de TC2 e traz marcos de decisão claros para absorver incertezas técnicas e éticas.

Ao final, espera-se contribuir com (i) evidência empírica preliminar sobre a relação entre engajamento visual e desempenho em avaliações formativas geradas por IA; (ii) uma discussão fundamentada sobre os limites práticos de rodar modelos de aprendizado profundo no navegador para monitoramento educacional com privacidade preservada; e (iii) um artefato funcional que sirva de base para trabalhos futuros em AVAs inteligentes.
