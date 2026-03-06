-- Tabelas usadas pelo chat (listagem de conversas, resumos e histórico opcional).
-- Execute após a extensão pgvector e antes de subir a API.
-- O LangGraph checkpointer cria suas próprias tabelas (checkpoints, checkpoint_blobs) via checkpointer.setup().

-- Listagem de chats por usuário (GET /user/{user_id})
CREATE TABLE IF NOT EXISTS chat (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'Nova Conversa',
    user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat (created_at DESC);

-- Resumos de conversa para contexto (summarize_node)
CREATE TABLE IF NOT EXISTS chat_summaries (
    session_id UUID PRIMARY KEY,
    chat_summary TEXT NOT NULL DEFAULT ''
);

-- Histórico opcional de mensagens (logger_node / save_message_to_db)
CREATE TABLE IF NOT EXISTS chat_history (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    message JSONB NOT NULL,
    summary BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history (session_id);
