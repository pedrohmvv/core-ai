"""
Módulo principal para criação da Vector Store.

Este módulo orquestra a criação de todos os componentes necessários
(engine, embeddings) e retorna a store configurada.
"""
import asyncio
from sqlalchemy.exc import ProgrammingError
from langchain_postgres import PGVectorStore
from .engine import create_engine
from .embeddings import create_embeddings_service
from core.config import config

_cached_store: PGVectorStore | None = None
_store_lock = asyncio.Lock()


async def create_vector_store(
    table_name: str | None = None,
    overwrite_existing: bool = False,
) -> PGVectorStore:
    """
    Inicializa a tabela (se necessário) e retorna uma instância do PGVectorStore.

    Na primeira chamada, cria o engine, embeddings e a tabela no banco. Nas
    chamadas subsequentes, retorna a instância em cache sem nenhuma operação
    de I/O adicional.

    Args:
        table_name: Nome da tabela onde os vetores serão armazenados.
                   Se None, usa o valor do config.
        overwrite_existing: Se True, recria a tabela do zero. Default: False.

    Returns:
        PGVectorStore configurado e pronto para uso
    """
    global _cached_store

    # Fast path: store já inicializada, sem lock
    if _cached_store is not None and not overwrite_existing:
        return _cached_store

    async with _store_lock:
        # Double-check após adquirir o lock para evitar criação duplicada
        # em chamadas concorrentes
        if _cached_store is not None and not overwrite_existing:
            return _cached_store

        if table_name is None:
            table_name = config.VECTOR_STORE_TABLE_NAME

        engine = create_engine()
        embeddings_service = create_embeddings_service()

        try:
            await engine.ainit_vectorstore_table(
                table_name=table_name,
                vector_size=config.EMBEDDING_DIMENSIONS,
                overwrite_existing=overwrite_existing,
            )
        except ProgrammingError as e:
            if "already exists" not in str(e):
                raise

        store = await PGVectorStore.create(
            engine=engine,
            table_name=table_name,
            embedding_service=embeddings_service,
        )

        _cached_store = store
        return store
