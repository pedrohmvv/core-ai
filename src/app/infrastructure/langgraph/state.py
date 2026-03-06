from typing import TypedDict, Annotated, Dict, Any, List
from langchain_core.messages import BaseMessage
import operator

class GraphState(TypedDict):
    """Estado do grafo LangGraph"""
    chatInput: str  # Input do usuário
    sessionId: str  # ID da sessão
    userId: str  # ID do usuário
    isFollowUp: bool  # Se é um follow-up automático
    systemPrompt: str  # Prompt do sistema (AI Assistant ou Follow-up)
    messages: Annotated[list[BaseMessage], operator.add]  # Histórico de mensagens
    response: str  # Resposta final do agente
    followUpQuestions: List[str]  # Perguntas de follow-up geradas
    #lastUserMessage: str  - Última mensagem do usuário para contexto de follow-up
    #lastAgentMessage: str  - Última resposta do agente para contexto de follow-up
    lastSourceDocuments: str  # Documentos RAG associados à última resposta (para follow-up)
    summary: str  # Resumo acumulado da conversa para contexto histórico
    error: bool
    errorMessage: str
    errorException: str