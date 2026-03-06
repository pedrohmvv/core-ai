"""
Módulo para criação do serviço de embeddings com HuggingFace (sentence-transformers).
"""
from langchain_huggingface import HuggingFaceEmbeddings

from core.config import config


def create_embeddings_service() -> HuggingFaceEmbeddings:
    """
    Cria o serviço de embeddings usando o modelo HuggingFace configurado.
    
    Modelo padrão: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2,
    adequado para português e buscas semânticas multilingues.
    
    Returns:
        HuggingFaceEmbeddings configurado e pronto para uso
    """
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL_NAME,
    )

