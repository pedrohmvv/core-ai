"""Router da API para chat.

Este módulo define os endpoints REST para operações de chat,
incluindo processamento de mensagens, listagem de chats e recuperação de histórico.
"""
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.chat.application.dto.chat_dto import (
    ChatRequestDTO, 
    ChatResponseDTO,
    UserChatsResponseDTO,
    ChatMessagesResponseDTO,
    UserConversationsResponseDTO
)
from app.chat.application.service.chat_service import ChatService
from app.chat.domain.command.chat_command import ChatCommand
from app.container import Container

chat_router = APIRouter()


@chat_router.post("", response_model=ChatResponseDTO)
@inject
async def process_chat_message(
    request: ChatRequestDTO,
    chat_service: ChatService = Depends(Provide[Container.chat_service]),
) -> ChatResponseDTO:
    """Processa mensagem de chat e retorna resposta com follow-ups.
    
    Args:
        request: DTO com dados da mensagem do usuário
        chat_service: Serviço de chat injetado
        
    Returns:
        DTO com resposta do agente e perguntas de follow-up
    """
    command = ChatCommand(
        chat_input=request.chat_input,
        session_id=request.session_id,
        user_id=request.user_id,
        is_follow_up=False,
        metadata=request.metadata
    )
    result = await chat_service.process_message(command)
    return chat_service.to_response_dto(result, request.session_id)


@chat_router.get("/user/{user_id}", response_model=UserChatsResponseDTO)
@inject
def list_user_chats(
    user_id: str,
    chat_service: ChatService = Depends(Provide[Container.chat_service]),
) -> UserChatsResponseDTO:
    """Lista chats do usuário ordenados por data (mais recentes primeiro).
    
    Args:
        user_id: ID do usuário
        chat_service: Serviço de chat injetado
        
    Returns:
        DTO com lista de chats do usuário
    """
    return chat_service.list_user_chats(user_id)


@chat_router.get("/session/{session_id}/messages", response_model=ChatMessagesResponseDTO)
@inject
def get_session_messages(
    session_id: str,
    chat_service: ChatService = Depends(Provide[Container.chat_service]),
) -> ChatMessagesResponseDTO:
    """Retorna mensagens da sessão (user e assistant).
    
    Args:
        session_id: ID da sessão
        chat_service: Serviço de chat injetado
        
    Returns:
        DTO com lista de mensagens da sessão
    """
    return chat_service.get_session_messages(session_id)


@chat_router.get("/user/{user_id}/conversations", response_model=UserConversationsResponseDTO)
@inject
def get_user_conversations(
    user_id: str,
    chat_service: ChatService = Depends(Provide[Container.chat_service]),
) -> UserConversationsResponseDTO:
    """Retorna todas as conversas do usuário com mensagens.
    
    Args:
        user_id: ID do usuário
        chat_service: Serviço de chat injetado
        
    Returns:
        DTO com todas as conversas do usuário incluindo mensagens
    """
    return chat_service.get_user_conversations(user_id)

