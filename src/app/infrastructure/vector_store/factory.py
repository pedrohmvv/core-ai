"""
Módulo principal para criação da Vector Store.

Este módulo orquestra a criação de todos os componentes necessários
(engine, embeddings) e retorna a store configurada.
"""
from langchain_postgres import PGVectorStore
from .engine import create_engine
from .embeddings import create_embeddings_service
from core.config import config


async def create_vector_store(table_name: str | None = None) -> PGVectorStore:
    """
    Cria e retorna uma instância do PGVectorStore configurada.
    
    Args:
        table_name: Nome da tabela onde os vetores serão armazenados.
                   Se None, usa o valor do config.
    
    Returns:
        PGVectorStore configurado e pronto para uso
    """
    if table_name is None:
        table_name = config.VECTOR_STORE_TABLE_NAME
    
    # Cria o engine
    engine = create_engine()
    
    # Cria o serviço de embeddings
    embeddings_service = create_embeddings_service()
    
    # Cria e retorna a store
    store = await PGVectorStore.create(
        engine=engine,
        table_name=table_name,
        embedding_service=embeddings_service
    )
    
    return store

