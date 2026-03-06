"""Entidade de domínio para mensagens de chat."""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class ChatMessage:
    """Entidade que representa uma mensagem de chat."""
    chat_input: str
    session_id: str
    is_follow_up: bool
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Gera timestamp automático se não fornecido."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

