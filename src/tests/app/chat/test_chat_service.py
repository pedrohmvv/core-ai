"""
Testes para ChatService.
"""
import pytest
from app.chat.application.service.chat_service import ChatService
from app.chat.domain.command.chat_command import ChatCommand


@pytest.mark.asyncio
async def test_process_message_success(mock_langgraph_service):
    """Testa processamento de mensagem com sucesso."""
    service = ChatService(langgraph_service=mock_langgraph_service)
    
    command = ChatCommand(
        chat_input="What is Sileto?",
        session_id="test-session-123",
        is_follow_up=False
    )
    
    result = await service.process_message(command)
    
    assert result["response"] == "Test response"


@pytest.mark.asyncio
async def test_to_response_dto(mock_langgraph_service):
    """Testa conversão para DTO."""
    service = ChatService(langgraph_service=mock_langgraph_service)
    
    result = {
        "response": "Test response",
        "followUpQuestions": {"follow_ups": ["Q1", "Q2"]}
    }
    
    dto = service.to_response_dto(result, "test-session-123")
    
    assert dto.response == "Test response"
    assert dto.session_id == "test-session-123"

