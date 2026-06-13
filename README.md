# AVA-I — Ambiente Virtual de Aprendizagem Inteligente

Implementação real da plataforma proposta no TCC, com as tecnologias do artigo:
Angular (SPA) · FastAPI · SQLAlchemy/PostgreSQL · LangChain · ChromaDB · LLM via API · MediaPipe Face Mesh (EAR) · YOLOv8 via ONNX Runtime Web.

## 1. Backend (FastAPI)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API em http://localhost:8000 — documentação interativa em http://localhost:8000/docs

### O que VOCÊ precisa configurar (arquivo `backend/.env`)

| Variável | O que fazer |
|---|---|
| `ANTHROPIC_API_KEY` | Cole sua chave de https://console.anthropic.com e mude `LLM_PROVIDER=anthropic`. Sem chave, `LLM_PROVIDER=mock` gera questões de demonstração e tudo funciona offline. |
| `DATABASE_URL` | Padrão é SQLite (zero configuração). Para PostgreSQL como no artigo: rode `docker compose up -d` na pasta backend, instale `pip install psycopg2-binary` e use `DATABASE_URL=postgresql://ava:ava@localhost:5432/ava`. |
| `EMBEDDINGS` | `default` usa o modelo do ChromaDB (baixa ~80 MB na primeira ingestão, requer internet). `simple` usa embedding leve por hashing, útil para desenvolvimento offline. |

## 2. Frontend (Angular)

```bash
cd frontend
npm install
npx ng serve
```

Aplicação em http://localhost:4200 (o backend precisa estar rodando).

### Detector de celular (YOLOv8) — opcional

O modelo não acompanha o repositório por tamanho. Para ativar:

```bash
pip install ultralytics
yolo export model=yolov8n.pt format=onnx imgsz=640
```

Copie o `yolov8n.onnx` gerado para `frontend/src/assets/`. Sem o arquivo, a plataforma aplica degradação graciosa: a sessão continua apenas com o Face Mesh, exatamente como descrito no Capítulo 4 do TCC.

A câmera real (MediaPipe) funciona direto no `ng serve` — clique em "Ativar câmera" na sessão de estudo e permita o acesso. A calibração do limiar de EAR leva 5 segundos.

## 3. Fluxo de uso

1. **Docente** → envie um PDF, escolha o cenário (Restrito ou Expandido), revise as questões geradas com o trecho-fonte, aprove e publique.
2. **Sessão de estudo** → escolha o material e a condição experimental (Controle ou Intervenção), ative a câmera se quiser telemetria real, leia e responda os checkpoints.
3. **Dashboard** → veja engajamento por minuto (controle × intervenção, QP2), acerto por questão e a dispersão focusScore × accuracyRate (QP1), alimentados pelos dados reais das sessões.

## 4. Estrutura

```
backend/app/rag.py    extração (pypdf), chunking (LangChain), ChromaDB, recuperação de vizinhos
backend/app/llm.py    geração de questões (Anthropic ou mock), prompt e parse de JSON
backend/app/main.py   endpoints REST: materiais, questões, sessões, telemetria, dashboard
frontend/src/app/services/vision.service.ts   MediaPipe Face Mesh, cálculo de EAR, calibração, focusScore
frontend/src/app/services/yolo.service.ts     ONNX Runtime Web, classe cell phone, k quadros consecutivos
```
