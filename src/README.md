# Sileto LangGraph - Estrutura Modular

Este diretório contém a versão refatorada e modularizada do sistema de chat com RAG usando LangGraph.

## 📁 Estrutura

```
src/
├── core/                    # Módulos core da aplicação
│   ├── config.py           # Configurações centralizadas
│   ├── db/                 # Database (SQLAlchemy, sessões)
│   ├── exceptions/         # Exceções customizadas
│   └── repository/        # Repositórios base
│
├── app/                    # Módulos da aplicação
│   ├── infrastructure/     # Infraestrutura (vector store, embeddings, langgraph)
│   │   ├── vector_store/  # PGVector Store
│   │   ├── langgraph/     # Serviço LangGraph e tools
│   │   └── prompts/       # Templates de prompts Jinja2
│   │
│   ├── chat/              # Módulo de chat
│   │   ├── domain/        # Camada de domínio
│   │   │   ├── entity/    # Entidades
│   │   │   ├── command/   # Comandos
│   │   │   └── usecase/   # Casos de uso (interfaces)
│   │   ├── application/   # Camada de aplicação
│   │   │   ├── dto/       # Data Transfer Objects
│   │   │   └── service/   # Serviços de aplicação
│   │   └── adapter/       # Camada de adaptadores
│   │       └── input/     # Adaptadores de entrada (API)
│   │
│   ├── container.py       # Dependency Injection Container
│   └── server.py         # Servidor FastAPI
│
├── tests/                 # Testes unitários
│   └── app/
│       └── chat/
│
└── main.py               # Ponto de entrada da aplicação
```

## 🏗️ Arquitetura

A aplicação segue os princípios de **Clean Architecture**:

### Camadas

1. **Domain** (Domínio)
   - Entidades de negócio
   - Casos de uso (interfaces)
   - Comandos

2. **Application** (Aplicação)
   - Serviços de aplicação
   - DTOs
   - Orquestração de casos de uso

3. **Infrastructure** (Infraestrutura)
   - Vector Store (PGVector)
   - Embeddings (Azure OpenAI)
   - LangGraph Service
   - Prompts

4. **Adapter** (Adaptadores)
   - API (FastAPI routers)
   - Processadores de input

### Princípios

- **Separação de responsabilidades**: Cada camada tem uma responsabilidade clara
- **Inversão de dependência**: Camadas superiores não dependem de inferiores
- **Baixo acoplamento**: Módulos independentes
- **Alta coesão**: Funcionalidades relacionadas agrupadas

## 🚀 Como Usar

### Configuração

Configure as variáveis de ambiente (veja `.env.example`):

```bash
# PostgreSQL
LOCAL_DB_POSTGRESDB_USER=postgres
LOCAL_DB_POSTGRESDB_PASSWORD=postgres
LOCAL_DB_POSTGRESDB_HOST=localhost
LOCAL_DB_POSTGRESDB_PORT=5432
LOCAL_DB_POSTGRESDB_DATABASE=postgres

# Azure OpenAI Embeddings
EMBEDDING_API_KEY=your_key
EMBEDDING_API_URL=your_endpoint
EMBEDDING_API_MODEL=your_deployment
LANGGRAPH_LLM_API_VERSION=2023-05-15

# LLM
LANGGRAPH_LLM_API_KEY=your_key
LANGGRAPH_LLM_API_URL=http://localhost:4000/v1
LANGGRAPH_LLM_API_MODEL=sileto
LANGGRAPH_LLM_API_TEMPERATURE=0.3
```

### Executar

```bash
# Desenvolvimento
python -m src.main --env local

# Produção
python -m src.main --env prod
```

### API

A API estará disponível em `http://localhost:8000`

**Endpoint de Chat:**
```bash
POST /api/v1/chat
Content-Type: application/json

{
  "chat_input": "What is Sileto?",
  "session_id": "session-123",
  "metadata": {}
}
```

**Resposta:**
```json
{
  "response": "Resposta do agente...",
  "follow_up_questions": ["Pergunta 1", "Pergunta 2"],
  "session_id": "session-123"
}
```

## 🧪 Testes

```bash
pytest src/tests/
```

## 📝 Notas

- O código funcional original está em `src_dev/` e foi migrado para esta estrutura modular
- A arquitetura segue o padrão do `api-boilerplate/`
- O comportamento funcional original foi mantido, apenas reorganizado

