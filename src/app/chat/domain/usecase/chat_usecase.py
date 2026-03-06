"""Use case para processamento de chat."""
from abc import ABC, abstractmethod
from typing import Dict, Any

from app.chat.domain.command.chat_command import ChatCommand


class ChatUseCase(ABC):
    """Interface para o caso de uso de chat."""
    
    @abstractmethod
    async def process_message(self, command: ChatCommand) -> Dict[str, Any]:
        """Processa mensagem de chat e retorna resposta."""
        pass

