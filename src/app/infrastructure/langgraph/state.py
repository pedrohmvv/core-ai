from typing import TypedDict, Annotated, Dict, Any, List
from langchain_core.messages import BaseMessage
import operator


class PatientInfo(TypedDict, total=False):
    """Informações do paciente para contexto do relatório."""
    sexo: str
    idade: int
    alergias: List[str]
    remedios: List[str]


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
    lastSourceDocuments: str  # Documentos RAG associados à última resposta (para follow-up)
    summary: str  # Resumo acumulado da conversa para contexto histórico
    patientInfo: PatientInfo  # Sexo, idade, alergias, remédios (para o prompt do agente)
    error: bool
    errorMessage: str
    errorException: str