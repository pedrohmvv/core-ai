"""DTOs para chat."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, model_validator


# Exemplos para documentação Swagger/OpenAPI
CHAT_REQUEST_EXAMPLE = {
    "chat_input": "Quais alimentos são ricos em vitamina C?",
    "session_id": "sess-abc-123",
    "user_id": "user-456",
    "metadata": {},
}

CHAT_REQUEST_PDF_EXAMPLE = {
    "pdf_base64": "<conteúdo base64 do PDF>",
    "session_id": "sess-abc-123",
    "user_id": "user-456",
    "metadata": {},
}


class ChatRequestDTO(BaseModel):
    """DTO de requisição de chat.

    A primeira mensagem do chat deve ser um PDF (pdf_base64).
    Mensagens seguintes devem ser texto (chat_input).
    """
    chat_input: Optional[str] = Field(None, description="Mensagem do usuário (para mensagens após o primeiro PDF)")
    pdf_base64: Optional[str] = Field(None, description="PDF do documento em base64 (obrigatório na primeira mensagem)")
    session_id: str = Field(..., description="ID da sessão")
    user_id: str = Field(..., description="ID do usuário")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")

    @model_validator(mode="after")
    def require_chat_input_or_pdf(self):
        if not self.chat_input and not self.pdf_base64:
            raise ValueError("É necessário enviar 'chat_input' ou 'pdf_base64'.")
        if self.chat_input and self.pdf_base64:
            raise ValueError("Envie apenas um dos dois: 'chat_input' ou 'pdf_base64'.")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [CHAT_REQUEST_EXAMPLE, CHAT_REQUEST_PDF_EXAMPLE],
        },
    }


class ChatResponseDTO(BaseModel):
    """DTO de resposta de chat."""
    response: str = Field(..., description="Resposta do agente")
    session_id: str = Field(..., description="ID da sessão")
    followUpQuestions: List[str] = Field(default_factory=list, description="Perguntas de follow-up geradas")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "Alimentos ricos em vitamina C incluem...",
                    "session_id": "sess-abc-123",
                    "followUpQuestions": ["Quanto consumir por dia?", "E para gestantes?"],
                }
            ]
        }
    }


class ChatListItemDTO(BaseModel):
    """DTO para item de chat na listagem."""
    id: str = Field(..., description="ID do chat")
    title: str = Field(..., description="Título do chat")
    created_at: str = Field(..., description="Data de criação (ISO format)")


class UserChatsResponseDTO(BaseModel):
    """DTO de resposta para listagem de chats do usuário."""
    user_id: str = Field(..., description="ID do usuário")
    chats: List[ChatListItemDTO] = Field(..., description="Lista de chats do usuário")


class ChatMessageDTO(BaseModel):
    """DTO para uma mensagem individual do chat."""
    role: str = Field(..., description="Role da mensagem (user ou assistant)")
    content: str = Field(..., description="Conteúdo da mensagem")
    timestamp: Optional[str] = Field(None, description="Timestamp da mensagem (ISO format)")


class ChatMessagesResponseDTO(BaseModel):
    """DTO de resposta para listagem de mensagens de uma sessão."""
    session_id: str = Field(..., description="ID da sessão")
    messages: List[ChatMessageDTO] = Field(..., description="Lista de mensagens da sessão")


class ConversationDTO(BaseModel):
    """DTO para uma conversa completa (sessão com mensagens)."""
    session_id: str = Field(..., description="ID da sessão")
    messages: List[ChatMessageDTO] = Field(..., description="Lista de mensagens da conversa")
    message_count: int = Field(..., description="Número total de mensagens")


class UserConversationsResponseDTO(BaseModel):
    """DTO de resposta para listagem de todas as conversas de um usuário."""
    user_id: str = Field(..., description="ID do usuário")
    total_conversations: int = Field(..., description="Número total de conversas")
    conversations: List[ConversationDTO] = Field(..., description="Lista de conversas do usuário")