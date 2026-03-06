"""
Configuração de testes.
"""
import pytest
from unittest.mock import Mock, AsyncMock

from app.infrastructure.langgraph.service import LangGraphService
from app.chat.application.service.chat_service import ChatService


@pytest.fixture
def mock_langgraph_service():
    """Mock do LangGraphService."""
    service = Mock(spec=LangGraphService)
    service.invoke = AsyncMock(return_value={
        "response": "Test response",
        "followUpQuestions": {"follow_ups": ["Question 1", "Question 2"]}
    })
    return service


@pytest.fixture
def chat_service(mock_langgraph_service):
    """Instância do ChatService com mock."""
    return ChatService(langgraph_service=mock_langgraph_service)

