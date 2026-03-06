"""
Container de injeção de dependências.
"""
from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Factory, Singleton

from app.chat.application.service.chat_service import ChatService
from app.infrastructure.langgraph.service import LangGraphService


class Container(DeclarativeContainer):
    """Container principal para injeção de dependências."""
    
    wiring_config = WiringConfiguration(packages=["app"])
    
    # LangGraph Service (singleton)
    langgraph_service = Singleton(LangGraphService)
    
    # Chat Service
    chat_service = Factory(
        ChatService,
        langgraph_service=langgraph_service,
    )

