"""Serviço de aplicação para chat.

Este módulo implementa a lógica de negócio para processamento de mensagens,
listagem de chats e recuperação de histórico de conversas.
"""
import logging
from typing import Dict, Any

from app.chat.domain.command.chat_command import ChatCommand
from app.chat.domain.usecase.chat_usecase import ChatUseCase
from app.chat.application.dto.chat_dto import (
    ChatResponseDTO, 
    UserChatsResponseDTO,
    ChatListItemDTO,
    ChatMessagesResponseDTO,
    ChatMessageDTO,
    UserConversationsResponseDTO,
    ConversationDTO
)
from app.infrastructure.langgraph.service import LangGraphService
from app.infrastructure.langgraph.utils import get_user_chats

logger = logging.getLogger(__name__)

class ChatService(ChatUseCase):
    """Serviço que implementa o caso de uso de chat.
    
    Coordena o processamento de mensagens através do LangGraphService
    e fornece métodos para listagem e recuperação de conversas.
    """
    
    def __init__(self, langgraph_service: LangGraphService):
        """Inicializa o serviço de chat.
        
        Args:
            langgraph_service: Serviço LangGraph para processamento de mensagens
        """
        self.langgraph_service = langgraph_service
    
    async def process_message(self, command: ChatCommand) -> Dict[str, Any]:
        """Processa mensagem de chat e retorna resposta.
        
        Args:
            command: Comando contendo dados da mensagem
            
        Returns:
            Dicionário com 'response' e 'followUpQuestions'
        """
        logger.info(f"Processando mensagem - Session: {command.session_id} - User: {command.user_id}")
        result = await self.langgraph_service.invoke(
            chat_input=command.chat_input,
            session_id=command.session_id,
            user_id=command.user_id,
            is_follow_up=command.is_follow_up
        )
        logger.info(f"Mensagem processada - Session: {command.session_id} - User: {command.user_id}")
        return result
    
    def to_response_dto(self, result: Dict[str, Any], session_id: str) -> ChatResponseDTO:
        """Converte resultado do processamento para DTO.
        
        Args:
            result: Resultado do processamento do LangGraph
            session_id: ID da sessão
            
        Returns:
            DTO de resposta formatado
        """
        follow_ups = result.get("followUpQuestions", [])
        if isinstance(follow_ups, dict):
            follow_ups = follow_ups.get("follow_ups", [])
        elif not isinstance(follow_ups, list):
            follow_ups = []
        
        return ChatResponseDTO(
            response=result.get("response", ""),
            session_id=session_id,
            followUpQuestions=follow_ups
        )
    
    def list_user_chats(self, user_id: str) -> UserChatsResponseDTO:
        """Lista chats do usuário.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            DTO com lista de chats ordenados por data (mais recentes primeiro)
        """
        logger.info(f"Listando chats do usuário: {user_id}")
        chats_data = get_user_chats(user_id)
        
        chat_items = [
            ChatListItemDTO(
                id=chat["id"],
                title=chat["title"],
                created_at=chat["created_at"]
            )
            for chat in chats_data
        ]
        
        logger.info(f"Encontrados {len(chat_items)} chat(s) para user_id: {user_id}")
        return UserChatsResponseDTO(user_id=user_id, chats=chat_items)
    
    def get_session_messages(self, session_id: str) -> ChatMessagesResponseDTO:
        """Retorna mensagens da sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            DTO com lista de mensagens (user e assistant) da sessão
        """
        logger.info(f"Buscando mensagens da sessão: {session_id}")
        messages_data = self.langgraph_service.get_session_messages(session_id)
        
        message_items = [
            ChatMessageDTO(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp")
            )
            for msg in messages_data
        ]
        
        logger.info(f"Encontradas {len(message_items)} mensagem(ns) para session_id: {session_id}")
        return ChatMessagesResponseDTO(session_id=session_id, messages=message_items)
    
    def get_user_conversations(self, user_id: str) -> UserConversationsResponseDTO:
        """Retorna conversas do usuário com mensagens.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            DTO com todas as conversas do usuário incluindo mensagens
        """
        logger.info(f"Buscando conversas do usuário: {user_id}")
        conversations_data = self.langgraph_service.get_messages_by_user(user_id)
        
        conversation_items = [
            ConversationDTO(
                session_id=conv["session_id"],
                messages=[
                    ChatMessageDTO(
                        role=msg["role"],
                        content=msg["content"],
                        timestamp=msg.get("timestamp")
                    )
                    for msg in conv["messages"]
                ],
                message_count=conv["message_count"]
            )
            for conv in conversations_data
        ]
        
        logger.info(f"Encontradas {len(conversation_items)} conversa(s) para user_id: {user_id}")
        return UserConversationsResponseDTO(
            user_id=user_id,
            total_conversations=len(conversation_items),
            conversations=conversation_items
        )

