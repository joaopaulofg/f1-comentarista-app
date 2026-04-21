# F1 Comentarista IA

## Integrantes
- **João Paulo Ferreira Gomes - 2415050023**
- **Letícia Farias de Assis Arruda - 2415050016**
- **Vinicius Leal de Melo - 2415050029**
- **Giusepp - **

## Descrição do Projeto
O **F1 Comentarista IA** é uma aplicação web que consulta dados reais de corridas de Fórmula 1 na OpenF1 e gera um comentário em português com apoio de um LLM local via Ollama.

O usuário escolhe uma corrida recente, visualiza pódio e top 10, e recebe uma análise em estilo jornalístico. O sistema foi desenvolvido com foco em simplicidade, organização do código e integração prática entre frontend, backend e IA.

## Tecnologias Utilizadas
- **Frontend:** Angular 18
- **Backend:** FastAPI + Python 3
- **Integração HTTP:** `httpx`
- **Modelagem de dados:** Pydantic
- **Dados esportivos:** OpenF1 API
- **LLM local:** Ollama
- **Modelo oficial do app:** `qwen3:0.6b`

## Funcionalidades
- Listagem das corridas recentes já concluídas
- Seleção de corrida pelo frontend
- Exibição de pódio e top 10
- Geração de comentário esportivo com IA
- Streaming do comentário para exibição progressiva

## Estrutura do Projeto
```text
f1-comentarista-app/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   ├── main.py
│   │   ├── models.py
│   │   └── routes.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── angular.json
│   └── package.json
└── README.md
```

## Instruções de Execução

### 1. Pré-requisitos
- Python 3.11+
- Node.js 20+
- npm
- Ollama instalado localmente

### 2. Instalar e preparar o Ollama
Instale o Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Baixe o modelo oficial usado pelo app:

```bash
ollama pull qwen3:0.6b
```

Se necessário, suba o serviço do Ollama:

```bash
ollama serve
```

### 3. Rodar o backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend disponível em `http://localhost:8000`.

### 4. Rodar o frontend
```bash
cd frontend
npm install
npm start
```

Frontend disponível em `http://localhost:4200`.

## Variáveis de Ambiente
Arquivo: `backend/.env`

Exemplo:

```env
OPENF1_BASE_URL=https://api.openf1.org/v1
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:0.6b
```

## Endpoints Principais
- `GET /api/races/recent?limit=10`
- `GET /api/races/{session_key}/commentary`
- `GET /api/races/{session_key}/commentary/stream`

## Uso de LLM no Projeto
O sistema utiliza um modelo local no Ollama para transformar o resultado estruturado da corrida em um comentário natural em português. O prompt foi ajustado para gerar textos curtos, objetivos e mais naturais, com foco no pódio e nos destaques reais do top 10.