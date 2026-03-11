"""Router da API para chat.

Este módulo define os endpoints REST para operações de chat,
incluindo processamento de mensagens, listagem de chats e recuperação de histórico.

A primeira mensagem do chat deve ser sempre um PDF (enviado em pdf_base64).
As demais mensagens devem ser texto (chat_input).
"""
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from app.chat.application.dto.chat_dto import (
    ChatRequestDTO,
    ChatResponseDTO,
    UserChatsResponseDTO,
    ChatMessagesResponseDTO,
    UserConversationsResponseDTO,
)
from app.chat.application.service.chat_service import ChatService
from app.chat.domain.command.chat_command import ChatCommand
from app.container import Container
from app.infrastructure.pdf import extract_text_from_pdf_base64

chat_router = APIRouter()


def _resolve_chat_input(request: ChatRequestDTO, chat_service: ChatService) -> str:
    """
    Resolve o texto a processar: extrai do PDF em base64 ou usa chat_input.
    Valida que a primeira mensagem do chat seja PDF e as seguintes sejam texto.
    """
    is_first_message = not chat_service.chat_exists(request.session_id)

    if request.pdf_base64:
        if not is_first_message:
            raise HTTPException(
                status_code=400,
                detail="Apenas a primeira mensagem do chat pode ser um PDF. Use 'chat_input' para continuar a conversa.",
            )
        try:
            return extract_text_from_pdf_base64(request.pdf_base64)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    if request.chat_input:
        if is_first_message:
            raise HTTPException(
                status_code=400,
                detail="A primeira mensagem do chat deve ser um PDF (envie 'pdf_base64').",
            )
        return request.chat_input.strip()

    raise HTTPException(
        status_code=400,
        detail="Envie 'pdf_base64' na primeira mensagem ou 'chat_input' nas seguintes.",
    )


@chat_router.post(
    "",
    response_model=ChatResponseDTO,
    summary="Enviar mensagem",
    response_description="Resposta do agente com texto e perguntas de follow-up sugeridas",
)
@inject
async def process_chat_message(
    request: ChatRequestDTO,
    chat_service: ChatService = Depends(Provide[Container.chat_service]),
) -> ChatResponseDTO:
    """Processa mensagem de chat e retorna resposta com follow-ups.

    Primeira mensagem: envie o documento em pdf_base64.
    Demais mensagens: envie o texto em chat_input.
    """
    chat_input = _resolve_chat_input(request, chat_service)
    command = ChatCommand(
        chat_input=chat_input,
        session_id=request.session_id,
        user_id=request.user_id,
        is_follow_up=False,
        metadata=request.metadata,
    )
    result = await chat_service.process_message(command)
    return chat_service.to_response_dto(result, request.session_id)


@chat_router.get(
    "/user/{user_id}",
    response_model=UserChatsResponseDTO,
    summary="Listar chats do usuário",
    response_description="Lista de chats do usuário ordenados do mais recente ao mais antigo",
)
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


@chat_router.get(
    "/session/{session_id}/messages",
    response_model=ChatMessagesResponseDTO,
    summary="Mensagens da sessão",
    response_description="Lista de mensagens (user e assistant) da sessão",
)
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


@chat_router.get(
    "/user/{user_id}/conversations",
    response_model=UserConversationsResponseDTO,
    summary="Conversas do usuário",
    response_description="Todas as conversas do usuário com suas mensagens",
)
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

