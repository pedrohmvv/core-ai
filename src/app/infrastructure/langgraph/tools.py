"""
Ferramentas (tools) para o agente LangGraph.
"""
import logging
from typing import Optional

from langchain.tools import tool
from langchain_postgres import PGVectorStore

logger = logging.getLogger(__name__)

# Store global (será injetada pelo serviço)
_global_store: Optional[PGVectorStore] = None


def set_global_store(store: PGVectorStore):
    """Define a store global para uso nas tools."""
    global _global_store
    _global_store = store


def get_global_store() -> PGVectorStore:
    """Obtém a store global."""
    if _global_store is None:
        raise RuntimeError("Vector store não foi inicializada. Chame set_global_store() primeiro.")
    return _global_store


@tool
def document_search_with_urls(query: str) -> str:
    """Busca documentos técnicos sobre ciência de materiais na base Sileto."""
    logger.info(f"Tool: document_search_with_urls - Query: {query}")
    store = get_global_store()
    search_kwargs = {"k": 12}
    
    try:
        docs = store.as_retriever(search_kwargs=search_kwargs).invoke(query)
        logger.info(f"Busca retornou {len(docs)} documentos.")
    except Exception as e:
        logger.error(f"Erro na busca do vector store: {str(e)}")
        return "Erro ao buscar documentos. Por favor, tente novamente mais tarde."
    
    formatted_results = []
    for doc in docs:
        # Extração de metadados (name ou source = nome do documento, ex.: PDF)
        name = doc.metadata.get('name') or doc.metadata.get('source', 'Documento Desconhecido')
        page = doc.metadata.get('page', 'S/N')
        
        # Tentar encontrar URL em diferentes campos de metadados
        url = doc.metadata.get('url') or None
        
        # Formatar citação com link markdown se URL estiver disponível
        if url:
            # Formato markdown: [texto](url) - o frontend renderizará como link clicável
            citation = f"(Fonte: [[{name}, p. {page}]]({url}))"
        else:
            # Formato sem link se não houver URL
            citation = f"(Fonte: [{name}, p. {page}])"
        
        content = f"CONTEÚDO: {doc.page_content}\nCITAÇÃO: {citation}"
        formatted_results.append(content)
        
    return "\n---\n".join(formatted_results)


# Exportar as tools para uso no LangGraph
DocumentSearchTool = document_search_with_urls

