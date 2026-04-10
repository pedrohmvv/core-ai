import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from typing import Optional


load_dotenv()
from pydantic_settings import BaseSettings

# Railway e outros PaaS fornecem DATABASE_URL ao vincular Postgres; tem prioridade
_DATABASE_URL = os.environ.get("DATABASE_URL")

if _DATABASE_URL:
    # Garantir esquema postgresql:// (Railway às vezes usa postgres://)
    _sync_url = _DATABASE_URL if _DATABASE_URL.startswith("postgresql://") else _DATABASE_URL.replace("postgres://", "postgresql://", 1)
    DB_URI_SYNC = _sync_url
    DB_URI_ASYNC = _sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    DB_MEMORY_STORE = _sync_url
else:
    # PostgreSQL via variáveis individuais (local ou .env)
    DB_POSTGRESDB_USER = os.environ.get("DB_POSTGRESDB_USER") or "admin"
    DB_POSTGRESDB_PASSWORD = os.environ.get("DB_POSTGRESDB_PASSWORD") or "adminpassword"
    DB_POSTGRESDB_HOST = os.environ.get("DB_POSTGRESDB_HOST") or "localhost"
    DB_POSTGRESDB_PORT = os.environ.get("DB_POSTGRESDB_PORT") or "5432"
    DB_POSTGRESDB_DATABASE = os.environ.get("DB_POSTGRESDB_DATABASE") or "nutriai_db"
    DB_POSTGRESDB_USER_ENC = quote_plus(DB_POSTGRESDB_USER) if DB_POSTGRESDB_USER else ""
    DB_POSTGRESDB_PASSWORD_ENC = quote_plus(DB_POSTGRESDB_PASSWORD) if DB_POSTGRESDB_PASSWORD else ""
    DB_URI_ASYNC = (
        f"postgresql+asyncpg://{DB_POSTGRESDB_USER_ENC}:{DB_POSTGRESDB_PASSWORD_ENC}"
        f"@{DB_POSTGRESDB_HOST}:{DB_POSTGRESDB_PORT}/{DB_POSTGRESDB_DATABASE}"
    )
    DB_URI_SYNC = (
        f"postgresql://{DB_POSTGRESDB_USER_ENC}:{DB_POSTGRESDB_PASSWORD_ENC}"
        f"@{DB_POSTGRESDB_HOST}:{DB_POSTGRESDB_PORT}/{DB_POSTGRESDB_DATABASE}"
    )
    DB_MEMORY_STORE = DB_URI_SYNC

# Google API Key (Gemini)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_GEMINI_MODEL = os.environ.get("GOOGLE_GEMINI_MODEL") or "gemini-2.5-flash"

# Embedding model (Google Generative AI)
EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL_NAME",
    "models/gemini-embedding-001",
)

EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "768"))

# Railway e outros PaaS injetam PORT; localmente usa APP_PORT ou 8000
APP_PORT = int(os.environ.get("PORT") or os.environ.get("APP_PORT") or 8000)

class Config(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = APP_PORT
    WRITER_DB_URL: str = DB_URI_ASYNC
    READER_DB_URL: str = DB_URI_ASYNC
    # Vector Store Configuration
    VECTOR_STORE_TABLE_NAME: str = os.environ.get(
        "VECTOR_STORE_TABLE_NAME", "pg_langchain_vectors"
    )
    CHAT_HISTORY_TABLE_NAME: str = os.environ.get(
        "CHAT_HISTORY_TABLE_NAME", "chat_history"
    )

    # Google API Key (Gemini)
    GOOGLE_API_KEY: Optional[str] = GOOGLE_API_KEY
    GOOGLE_GEMINI_MODEL: str = GOOGLE_GEMINI_MODEL

    # Embedding model (Google Generative AI)
    EMBEDDING_MODEL_NAME: str = EMBEDDING_MODEL_NAME
    EMBEDDING_DIMENSIONS: int = EMBEDDING_DIMENSIONS

    # Database URIs
    DB_URI_ASYNC: str = DB_URI_ASYNC
    DB_URI_SYNC: str = DB_URI_SYNC
    DB_MEMORY_STORE: str = DB_MEMORY_STORE

class TestConfig(Config):
    WRITER_DB_URL: str = DB_URI_ASYNC
    READER_DB_URL: str = DB_URI_ASYNC


class LocalConfig(Config):
    pass


class ProductionConfig(Config):
    ENV: str = "production"
    DEBUG: bool = False


def get_config():
    env = os.getenv("ENV", "local")
    config_type = {
        "test": TestConfig(),
        "local": LocalConfig(),
        "prod": ProductionConfig(),
    }
    return config_type[env]


config: Config = get_config()