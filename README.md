# F1 Comentarista IA (Python + Angular)

App de estudo com IA generativa para comentar corridas de Fórmula 1.

## Stack
- **Backend**: FastAPI (Python)
- **Frontend**: Angular
- **Dados**: OpenF1 API
- **LLM local**: Ollama + `qwen3.6`

## Funcionalidades do MVP
1. Exibir as **10 últimas corridas**.
2. Selecionar uma corrida.
3. Gerar comentário em estilo "jornalista" com foco em:
   - pódio,
   - top-10,
   - resultado final.

## Pré-requisitos
- Python 3.11+
- Node.js 20+
- Angular CLI (`npm i -g @angular/cli`)
- Ollama instalado localmente

## Baixando o modelo no Ollama
```bash
ollama pull qwen3.6
```

## Rodando backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Rodando frontend
```bash
cd frontend
npm install
npm start
```

Frontend em `http://localhost:4200` e backend em `http://localhost:8000`.

## Endpoints principais
- `GET /api/races/recent?limit=10`
- `GET /api/races/{session_key}/commentary`

## Próximos passos sugeridos
- Melhorar prompt com contexto de classificação do campeonato.
- Adicionar cache local para reduzir chamadas na OpenF1.
- Permitir escolha de estilo (neutro, técnico, narrador).
