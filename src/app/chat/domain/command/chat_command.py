"""Comandos de domínio para chat."""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ChatCommand:
    """Comando para processar uma mensagem de chat."""
    chat_input: str
    session_id: str
    user_id: str
    is_follow_up: bool = False
    metadata: Optional[Dict[str, Any]] = None

