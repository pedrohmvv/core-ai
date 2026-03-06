"""
Módulo para criação do PostgreSQL Engine.
"""
from langchain_postgres import PGEngine

from core.config import config


def create_engine() -> PGEngine:
    """
    Cria o PGEngine a partir das variáveis de ambiente.
    
    Returns:
        PGEngine configurado e pronto para uso
    """
    # PGEngine.from_connection_string cria um async engine internamente,
    # então precisa de uma connection string com driver async (postgresql+asyncpg://)
    return PGEngine.from_connection_string(config.DB_URI_ASYNC)

