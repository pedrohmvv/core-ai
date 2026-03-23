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

# PDF mínimo com texto extraível (exame fictício) — válido para testar em "Try it out"
CHAT_REQUEST_PDF_EXAMPLE = {
    "pdf_base64": "JVBERi0xLjMKJenr8b8KMSAwIG9iago8PAovQ291bnQgMQovS2lkcyBbMyAwIFJdCi9NZWRpYUJveCBbMCAwIDU5NS4yOCA4NDEuODldCi9UeXBlIC9QYWdlcwo+PgplbmRvYmoKMiAwIG9iago8PAovT3BlbkFjdGlvbiBbMyAwIFIgL0ZpdEggbnVsbF0KL1BhZ2VMYXlvdXQgL09uZUNvbHVtbgovUGFnZXMgMSAwIFIKL1R5cGUgL0NhdGFsb2cKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDQgMCBSCi9QYXJlbnQgMSAwIFIKL1Jlc291cmNlcyA2IDAgUgovVHlwZSAvUGFnZQo+PgplbmRvYmoKNCAwIG9iago8PAovRmlsdGVyIC9GbGF0ZURlY29kZQovTGVuZ3RoIDExMQo+PgpzdHJlYW0KeJwzUvDiMtAzNVco53IKUdB3M1QwNNIzMFAISVNwDQEJGRvqGVoomFua6pmbK4SkKGi4ViTmplopeKTm5qcXJeYm6kGYOflJmXmJCoYmCun6KT56Cu45mcmpuZmJCpZGCrlgIU2FkCyQoQBqph6GCmVuZHN0cmVhbQplbmRvYmoKNSAwIG9iago8PAovQmFzZUZvbnQgL0hlbHZldGljYQovRW5jb2RpbmcgL1dpbkFuc2lFbmNvZGluZwovU3VidHlwZSAvVHlwZTEKL1R5cGUgL0ZvbnQKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL0ZvbnQgPDwvRjEgNSAwIFI+PgovUHJvY1NldCBbL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSV0KPj4KZW5kb2JqCjcgMCBvYmoKPDwKL0NyZWF0aW9uRGF0ZSAoRDoyMDI2MDMyMzEyMDAyMFopCj4+CmVuZG9iagp4cmVmCjAgOAowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMDEwMiAwMDAwMCBuIAowMDAwMDAwMjA1IDAwMDAwIG4gCjAwMDAwMDAyODUgMDAwMDAgbiAKMDAwMDAwMDQ2OCAwMDAwMCBuIAowMDAwMDAwNTY1IDAwMDAwIG4gCjAwMDAwMDA2NTIgMDAwMDAgbiAKdHJhaWxlcgo8PAovU2l6ZSA4Ci9Sb290IDIgMCBSCi9JbmZvIDcgMCBSCi9JRCBbPDkxOTFBNDY5MjFBQUZCODZCQkUyM0Q3M0VDNkZENDExPjw5MTkxQTQ2OTIxQUFGQjg2QkJFMjNENzNFQzZGRDQxMT5dCj4+CnN0YXJ0eHJlZgo3MDcKJSVFT0YK",
    "session_id": "sess-abc-123",
    "user_id": "user-456",
    "sexo": "M",
    "idade": 35,
    "alergias": ["lactose"],
    "remedios": ["Omeprazol 20mg"],
    "metadata": {},
}

# Exemplos nomeados para o Swagger UI (dropdown "Examples" no POST /api/v1/chat)
CHAT_REQUEST_OPENAPI_EXAMPLES = {
    "pdf_primeira_mensagem": {
        "summary": "1ª mensagem — PDF (base64)",
        "description": (
            "Obrigatório na primeira mensagem da sessão: envie o exame em PDF codificado em base64. "
            "Opcionalmente inclua sexo, idade, alergias e remédios para o relatório nutricional."
        ),
        "value": CHAT_REQUEST_PDF_EXAMPLE,
    },
    "mensagem_texto": {
        "summary": "Mensagens seguintes — texto",
        "description": "Após o primeiro PDF, use apenas chat_input para continuar a conversa (mesma session_id).",
        "value": CHAT_REQUEST_EXAMPLE,
    },
}


class ChatRequestDTO(BaseModel):
    """DTO de requisição de chat.

    A primeira mensagem do chat deve ser um PDF (pdf_base64).
    Mensagens seguintes devem ser texto (chat_input).
    Informações do paciente (sexo, idade, alergias, remedios) são opcionais e ajudam na produção do relatório.
    """
    chat_input: Optional[str] = Field(None, description="Mensagem do usuário (para mensagens após o primeiro PDF)")
    pdf_base64: Optional[str] = Field(None, description="PDF do documento em base64 (obrigatório na primeira mensagem)")
    session_id: str = Field(..., description="ID da sessão")
    user_id: str = Field(..., description="ID do usuário")
    sexo: Optional[str] = Field(None, description="Sexo do paciente (ex: M, F, Outro)")
    idade: Optional[int] = Field(None, description="Idade do paciente em anos")
    alergias: List[str] = Field(default_factory=list, description="Lista de alergias do paciente")
    remedios: List[str] = Field(default_factory=list, description="Lista de remédios que o paciente toma")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")

    @model_validator(mode="after")
    def require_chat_input_or_pdf(self):
        if not self.chat_input and not self.pdf_base64:
            raise ValueError("É necessário enviar 'chat_input' ou 'pdf_base64'.")
        if self.chat_input and self.pdf_base64:
            raise ValueError("Envie apenas um dos dois: 'chat_input' ou 'pdf_base64'.")
        return self


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