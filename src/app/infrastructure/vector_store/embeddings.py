"""
Módulo para criação do serviço de embeddings com Google Generative AI.
"""
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from core.config import config


def create_embeddings_service() -> GoogleGenerativeAIEmbeddings:
    """
    Cria o serviço de embeddings usando o modelo Google Generative AI configurado.

    Modelo padrão: models/gemini-embedding-001 com output_dimensionality=768,
    adequado para português e buscas semânticas multilingues.

    Returns:
        GoogleGenerativeAIEmbeddings configurado e pronto para uso
    """
    return GoogleGenerativeAIEmbeddings(
        model=config.EMBEDDING_MODEL_NAME,
        output_dimensionality=768,
    )
