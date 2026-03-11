
Resumo do **schema do banco de dados** usado no projeto:

---

## Banco e tecnologia

- **PostgreSQL** (com extensão **pgvector** para embeddings).
- Conexão via `DATABASE_URL` ou variáveis em `core/config.py`; nome padrão do banco: `nutriai_db`.

---

## Schema definido no projeto

O schema das tabelas de chat está em **`init-db/01-chat-tables.sql`**:

### 1. Tabela `chat`
Listagem de conversas por usuário (ex.: GET /user/{user_id}).

| Coluna     | Tipo        | Restrições                          |
|-----------|-------------|-------------------------------------|
| `id`      | UUID        | PRIMARY KEY                         |
| `title`   | TEXT        | NOT NULL, DEFAULT 'Nova Conversa'   |
| `user_id` | TEXT        | NOT NULL                            |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

- Índices: `idx_chat_user_id`, `idx_chat_created_at` (created_at DESC).

### 2. Tabela `chat_summaries`
Resumos de conversa (usado pelo `summarize_node`).

| Coluna         | Tipo | Restrições   |
|----------------|------|--------------|
| `session_id`   | UUID | PRIMARY KEY  |
| `chat_summary` | TEXT | NOT NULL, DEFAULT '' |

### 3. Tabela `chat_history`
Histórico de mensagens (usado pelo `logger_node` / `save_message_to_db`).

| Coluna      | Tipo        | Restrições                          |
|-------------|-------------|-------------------------------------|
| `id`        | BIGSERIAL   | PRIMARY KEY                         |
| `session_id`| UUID        | NOT NULL                            |
| `message`   | JSONB       | NOT NULL                            |
| `summary`   | BOOLEAN     | NOT NULL, DEFAULT FALSE             |
| `sent_at`   | TIMESTAMPTZ | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

- Índice: `idx_chat_history_session_id`.

---

## Tabelas criadas pelo LangChain

- **Checkpointer (LangGraph):** o checkpointer cria suas próprias tabelas (`checkpoints`, `checkpoint_blobs`) via `checkpointer.setup()` — não estão no `01-chat-tables.sql`.
- **RAG / vetores:** a tabela de vetores (nome configurável por `VECTOR_STORE_TABLE_NAME`, padrão **`pg_langchain_vectors`**) é criada automaticamente pelo **LangChain** (pacote `langchain_postgres`, `PGVectorStore`) na primeira ingestão ou uso do RAG. O projeto não define o DDL dessa tabela; a estrutura segue o schema do LangChain (collection + embedding ou equivalente, com coluna de vetor e metadados).

---

## Onde está cada coisa no código

- **Definição SQL das tabelas de chat:** `init-db/01-chat-tables.sql`
- **Config (nomes de tabelas):** `src/core/config.py` (`VECTOR_STORE_TABLE_NAME`, `CHAT_HISTORY_TABLE_NAME`)
- **Uso de `chat` / `chat_history`:** `src/app/infrastructure/langgraph/utils.py` (INSERT em `chat_history`, criação de registro em `chat`)
- **Vector store:** `src/app/infrastructure/vector_store/factory.py` e `engine.py` (PGVectorStore com tabela configurável)

Se quiser, posso propor um único arquivo de documentação (ex.: `docs/DATABASE_SCHEMA.md`) com esse resumo e os trechos relevantes do `01-chat-tables.sql`.