"""Comandos de domínio para chat."""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class ChatCommand:
    """Comando para processar uma mensagem de chat."""
    chat_input: str
    session_id: str
    user_id: str
    is_follow_up: bool = False
    metadata: Optional[Dict[str, Any]] = None
    sexo: Optional[str] = None
    idade: Optional[int] = None
    alergias: Optional[List[str]] = None
    remedios: Optional[List[str]] = None

