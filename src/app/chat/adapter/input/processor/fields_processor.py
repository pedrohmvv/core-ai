"""Processador de campos unificados."""
from typing import Dict, Any

from app.chat.domain.entity.chat_message import ChatMessage


class UnifyingFieldsProcessor:
    """Processa e unifica campos do input."""
    
    FOLLOW_UP_KEYWORDS = "You are a smart RAG follow-up generator."
    
    @classmethod
    def detect_followup(cls, chat_input: str) -> bool:
        """Detecta se a mensagem é um follow-up automático."""
        input_lower = chat_input.lower().strip()
        if input_lower.startswith(cls.FOLLOW_UP_KEYWORDS.lower()):
            return True
        return False
    
    @classmethod
    def process(cls, chat_input: str, session_id: str, metadata: Dict[str, Any] | None = None) -> ChatMessage:
        """Processa o input e unifica os campos."""
        is_followup = cls.detect_followup(chat_input)
        return ChatMessage(
            chat_input=chat_input,
            session_id=session_id,
            is_follow_up=is_followup,
            metadata={
                **(metadata or {}),
                "processed": True,
                "followup_detected": is_followup
            }
        )

