# Core-AI

**SaaS de apoio clínico para Nutricionistas.** O Core-AI analisa exames de sangue (PDFs) e cruza esses dados com uma base de conhecimento científica (RAG) para gerar estratégias dietéticas e protocolos de suplementação. Atua como **co-piloto** com regra de negócio crítica: **Zero Alucinação** — todas as condutas e dosagens devem estar fundamentadas nos documentos recuperados (strict citation).

---

## 1. Título e Visão Geral

O **Core-AI** é uma aplicação enterprise de apoio à decisão clínica no nicho da **Nutrição Clínica**. O sistema:

- **Ingere** documentos científicos (PDFs) numa base vetorial (PostgreSQL + pgvector).
- **Expõe** um chat conversacional onde o nutricionista faz perguntas ou envia dados de exames.
- **Responde** com análises e recomendações **estritamente citadas** às fontes (RAG), sem inventar dosagens ou protocolos.
- **Sugere** perguntas de follow-up com base em lacunas clínicas (detalhes presentes nas fontes mas não explorados na resposta).

O frontend consome a **API REST** (FastAPI); integrações com interfaces (e.g. Streamlit ou frontends custom) são feitas via HTTP.

- **Deploy na Railway (API + PostgreSQL com pgvector):** ver [docs/DEPLOY-RAILWAY.md](docs/DEPLOY-RAILWAY.md).

---

## 2. Arquitetura do Sistema

### Fluxo híbrido

1. **Caminho de ingestão (RAG)**  
   PDFs em `data/documentos` (ou `data/not_processed`) são processados por um pipeline (notebook `notebooks/embeddings.ipynb`): extração de texto, chunking, embeddings locais (HuggingFace) e gravação na tabela `pg_langchain_vectors`. Esta base é a **única** fonte de verdade para recomendações clínicas.

2. **Caminho de chat interativo**  
   O utilizador envia mensagens via API. A **primeira mensagem** de cada conversa deve ser **sempre um PDF** (exames em base64); as seguintes são **texto** (`chat_input`). O backend extrai o texto do PDF (pypdf) e processa no mesmo fluxo. Opcionalmente, o cliente envia **dados do paciente** (sexo, idade, alergias, remédios em uso), usados no prompt do agente para contextualizar o relatório (dosagens, interações fármaco-nutriente, contraindicações).  
   O **LangGraph** orquestra o fluxo:
   - **create_chat** → criação do registo de conversa (tabela `chat`) se for nova sessão.
   - **summarize** → se houver muitas mensagens da IA, gera resumo e reduz contexto (memória em `chat_summaries`).
   - **run_agent** → agente com uma tool de busca (RAG) no PGVector; o LLM responde com base **apenas** nos documentos recuperados e com citações inline; o prompt inclui o **Perfil do Paciente** (sexo, idade, alergias, remédios) quando informado.
   - **check_error** → roteamento para resposta de sucesso ou de erro.
   - **return_response / return_error** → formatação da resposta.
   - **run_follow_up_llm** → geração de perguntas de follow-up a partir da resposta e dos documentos (lacunas clínicas).
   - **logger_node** (opcional) → persistência de mensagens em `chat_history`.

### Estado LangGraph

O estado do grafo (`GraphState`) inclui: `chatInput`, `sessionId`, `userId`, `messages` (reducer `operator.add`), `response`, `followUpQuestions`, `summary`, `lastSourceDocuments`, **`patientInfo`** (sexo, idade, alergias, remedios — usados no prompt do agente) e flags de erro. O **checkpointer** (PostgresSaver) persiste o estado por `thread_id` (session_id), permitindo conversas longas com memória. O `patientInfo` enviado na primeira mensagem (com o PDF) fica guardado no checkpoint e é reutilizado nas mensagens seguintes se o cliente não enviar de novo.

---

## 3. Pré-requisitos

- **Python** 3.13+ (definido em `pyproject.toml`)
- **uv** (gestor de pacotes e ambientes) — [instalação](https://docs.astral.sh/uv/getting-started/installation/)
- **Docker** (para PostgreSQL com pgvector)
- **Chave de API Google** (Gemini) para o LLM principal

---

## 4. Variáveis de Ambiente (`.env`)

Crie um ficheiro `.env` na raiz do projeto com as variáveis abaixo. **Nunca** commite chaves reais.

| Variável | Descrição | Exemplo / Default |
|----------|-----------|-------------------|
| `DB_POSTGRESDB_USER` | Utilizador PostgreSQL | `admin` |
| `DB_POSTGRESDB_PASSWORD` | Password PostgreSQL | `adminpassword` |
| `DB_POSTGRESDB_HOST` | Host do PostgreSQL | `localhost` |
| `DB_POSTGRESDB_PORT` | Porta | `5432` |
| `DB_POSTGRESDB_DATABASE` | Nome da base de dados | `nutriai_db` |
| `GOOGLE_API_KEY` | Chave da API Google (Gemini) | *(obrigatório)* |
| `GOOGLE_GEMINI_MODEL` | Modelo Gemini | `gemini-2.5-flash` |
| `EMBEDDING_MODEL_NAME` | Modelo HuggingFace para embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| `APP_PORT` | Porta da API | `8000` |
| `VECTOR_STORE_TABLE_NAME` | Tabela de vetores RAG | `pg_langchain_vectors` |
| `CHAT_HISTORY_TABLE_NAME` | Tabela de histórico de mensagens | `chat_history` |

Exemplo mínimo:

```env
DB_POSTGRESDB_USER=admin
DB_POSTGRESDB_PASSWORD=adminpassword
DB_POSTGRESDB_HOST=localhost
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=nutriai_db

GOOGLE_API_KEY=sua_chave_google_aqui
GOOGLE_GEMINI_MODEL=gemini-2.5-flash

APP_PORT=8000
```

---

## 5. Instalação e Execução (Passo a Passo)

### 5.1. Base de dados (PostgreSQL + pgvector)

O projeto espera um PostgreSQL com a extensão **pgvector**. Pode usar um contentor Docker.

**Exemplo com Docker (sem ficheiro compose no repositório):**

```bash
docker run -d \
  --name nutriai-postgres \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=adminpassword \
  -e POSTGRES_DB=nutriai_db \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

**Inicialização do banco (scripts em `init-db/`):**

Os scripts devem ser executados **uma vez** na base de dados (por ordem):

1. **`init-db/01-init-vector.sql`** — cria a extensão `vector` (pgvector).
2. **`init-db/01-chat-tables.sql`** — cria as tabelas do chat: `chat`, `chat_summaries`, `chat_history`.

Exemplo (com `psql` ou cliente equivalente):

```bash
psql -h localhost -U admin -d nutriai_db -f init-db/01-init-vector.sql
psql -h localhost -U admin -d nutriai_db -f init-db/01-chat-tables.sql
```

Se usar um volume ou imagem custom, pode configurar um script de entrypoint que execute estes ficheiros na primeira vez que o contentor sobe.

A tabela **`pg_langchain_vectors`** é criada automaticamente pelo **LangChain PGVectorStore** na primeira utilização (ingestão de embeddings ou arranque da aplicação, consoante o fluxo). Não é criada pelos scripts em `init-db/`.

### 5.2. Dependências Python (uv)

Na raiz do projeto:

```bash
uv sync
```

Isto cria o ambiente virtual e instala as dependências definidas em `pyproject.toml` (LangChain, LangGraph, FastAPI, HuggingFace, etc.).

### 5.3. Executar a API

```bash
uv run python -m src.main --env local
```

Com debug:

```bash
uv run python -m src.main --env local --debug
```

A API fica disponível em `http://0.0.0.0:8000` (ou `APP_PORT`). Em ambiente não-produção, a documentação interativa está em `/docs` e `/redoc`.

### 5.4. Documentação da API (Swagger / OpenAPI)

O projeto está documentado com **OpenAPI 3** (Swagger). Com a API a correr em ambiente **local** ou **dev**:

| Recurso | URL | Descrição |
|--------|-----|-----------|
| **Swagger UI** | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentação interativa: testar endpoints e ver schemas |
| **ReDoc** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Documentação em formato de leitura |
| **OpenAPI JSON** | [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) | Especificação bruta (para ferramentas ou clientes gerados) |

Em **produção** (`--env prod`), as rotas `/docs`, `/redoc` e `/openapi.json` ficam desativadas por segurança. Para uma **referência textual** dos endpoints, payloads e regras de negócio (primeira mensagem = PDF, dados do paciente), consulte **[docs/API.md](docs/API.md)**.

---

## 6. Pipeline de Ingestão (RAG)

A base de conhecimento científica é populada através do notebook **`notebooks/embeddings.ipynb`**:

1. **Entrada:** PDFs em `data/documentos` ou em `data/not_processed` (conforme a secção configurada no notebook).
2. **Processamento:** carregamento com PyPDFLoader, validação de texto (skip de PDFs só com imagem/OCR futuro), chunking com `RecursiveCharacterTextSplitter`, metadados `source` e `page`.
3. **Embeddings:** modelo HuggingFace local `paraphrase-multilingual-MiniLM-L12-v2` (sem custo de API).
4. **Gravação:** inserção em lotes na tabela **`pg_langchain_vectors`** via PGVectorStore (LangChain).

Execute as células do notebook na ordem (com o PostgreSQL a correr e `.env` configurado). O pipeline usa `config.DB_URI_ASYNC` / `DB_URI_SYNC` e a mesma tabela `pg_langchain_vectors` que a API.

---

## 7. Características Principais (Key Features)

### Prevenção de alucinações (Medical Guardrails)

- O prompt do agente (**`agent.jinja2`**) impõe **Single Source of Truth**: recomendações (dosagens, protocolos, diagnósticos) têm de estar **100%** nos documentos recuperados pelo RAG.
- **Zero Hallucination:** o modelo não pode usar apenas conhecimento pré-treino para sugerir dosagens ou condutas; se um biomarcador alterado não tiver protocolo nos documentos, o sistema deve declarar explicitamente que a informação não está disponível nas fontes fornecidas (Containment Rule).

### Rastreabilidade (Strict inline citations)

- Toda a afirmação clínica deve ser seguida de citação no formato `(Fonte: [Nome do Documento, Página X])`.
- A tool de busca (`document_search_with_urls` em `tools.py`) devolve conteúdo já formatado com citações; o LLM é instruído a manter e repetir esse formato na resposta final.

### Follow-up com base em lacunas clínicas (Gaps)

- Após cada resposta do agente, o nó **run_follow_up_llm** invoca o LLM com o prompt **`follow_up.jinja2`**.
- O prompt analisa a última resposta do agente e os **source_documents** para identificar **gaps**: detalhes presentes nas fontes mas não explorados (e.g. interações fármaco-nutriente, cofatores, contraindicações).
- São geradas 3–5 perguntas de follow-up em PT-BR, acionáveis e fundamentadas nos documentos, para o nutricionista aprofundar o caso.

---

## Stack Técnica (resumo)

| Componente | Tecnologia |
|------------|------------|
| Orquestração | LangGraph / LangChain |
| LLM (raciocínio) | Google Gemini (ChatGoogleGenerativeAI) — configurável via `GOOGLE_GEMINI_MODEL` |
| Embeddings | HuggingFace local: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Base vetorial e memória | PostgreSQL + pgvector |
| Tabela RAG | `pg_langchain_vectors` |
| Tabelas de chat | `chat`, `chat_summaries`, `chat_history` |
| API | FastAPI |
| Runtime / deps | Python 3.13, uv |

---

## Estrutura do Projeto (resumo)

```
nutri-ai/
├── src/
│   ├── main.py                    # Entrada: uvicorn + click (--env, --debug)
│   ├── core/
│   │   ├── config.py              # Configuração (.env, DB, Gemini, embeddings)
│   │   └── db/                    # Sessão e utilitários DB
│   └── app/
│   │   ├── server.py              # FastAPI app (NutriAI API)
│   │   ├── container.py           # Dependency injection
│   │   ├── chat/                  # Casos de uso, DTOs, API v1 chat
│   │   └── infrastructure/
│   │     ├── langgraph/          # service, nodes, state, tools, utils
│   │     ├── vector_store/      # PGVectorStore, embeddings HuggingFace
│   │     └── prompts/            # agent.jinja2, follow_up.jinja2
│   └── tests/
│       ├── app/       
│       ├── __init__.py
│       ├── conftest.py
│       ├── run_tests.bat
│       ├── run_tests.sh
│       └── README.md

├── init-db/
│   ├── 01-init-vector.sql         # CREATE EXTENSION vector
│   └── 01-chat-tables.sql         # chat, chat_summaries, chat_history
├── docs/
│   ├── API.md                    # Documentação da API (endpoints, payloads, regras)
│   └── DEPLOY-RAILWAY.md
├── notebooks/
│   ├── embeddings.ipynb          # Pipeline RAG (PDF → chunks → pg_langchain_vectors)
│   └── api_chat_test.ipynb      # Testes manuais da API de chat (PDF + paciente + follow-up)
├── pyproject.toml                 # Dependências (uv)
├── uv.lock
├── Dockerfile                    # Imagem para deploy (python 3.13, uv)
└── README.md                     # Este ficheiro
```

---

*Documento gerado para o projeto Core-AI (Nutri-AI) — Enterprise Grade.*
