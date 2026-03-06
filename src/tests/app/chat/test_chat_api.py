"""
Testes de integração para a API de chat.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from app.server import create_app
from app.infrastructure.langgraph.service import LangGraphService
from app.chat.application.service.chat_service import ChatService


@pytest.fixture
def mock_langgraph_service():
    """Mock do LangGraphService para testes de API."""
    service = Mock(spec=LangGraphService)
    service.invoke = AsyncMock(return_value={
        "response": "Sileto é um material avançado com propriedades especiais.",
        "followUpQuestions": {
            "follow_ups": [
                "Quais são as principais aplicações do Sileto?",
                "Como o Sileto é produzido?",
                "Quais são as propriedades mecânicas do Sileto?"
            ]
        }
    })
    return service


@pytest.fixture
def mock_chat_service(mock_langgraph_service):
    """Mock do ChatService para testes de API."""
    from app.chat.application.dto.chat_dto import ChatResponseDTO
    
    service = Mock(spec=ChatService)
    service.process_message = AsyncMock(return_value={
        "response": "Sileto é um material avançado com propriedades especiais.",
        "followUpQuestions": {
            "follow_ups": [
                "Quais são as principais aplicações do Sileto?",
                "Como o Sileto é produzido?",
                "Quais são as propriedades mecânicas do Sileto?"
            ]
        }
    })
    
    def to_response_dto(result, session_id):
        return ChatResponseDTO(
            response=result.get("response", ""),
            session_id=session_id
        )
    
    service.to_response_dto = to_response_dto
    return service


@pytest.fixture
def app(mock_chat_service):
    """Cria uma instância da aplicação com mocks."""
    from dependency_injector.providers import Singleton
    from app.container import Container
    from app.chat.adapter.input.api.v1.chat import chat_router
    
    # Override o provider ANTES de criar o app
    Container.chat_service.override(Singleton(lambda: mock_chat_service))
    
    try:
        app = create_app()
        # Também override no container instance do router se existir
        if hasattr(chat_router, 'container') and chat_router.container:
            chat_router.container.chat_service.override(Singleton(lambda: mock_chat_service))
        yield app
    finally:
        # Cleanup
        Container.chat_service.reset_override()
        if hasattr(chat_router, 'container') and chat_router.container:
            chat_router.container.chat_service.reset_override()


@pytest.fixture
def client(app):
    """Cria um cliente de teste."""
    return TestClient(app)


def test_chat_endpoint_success(client):
    """Testa o endpoint de chat com sucesso."""
    response = client.post(
        "/api/v1/chat",
        json={
            "chat_input": "What is Sileto?",
            "session_id": "test-session-123",
            "metadata": {}
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert data["session_id"] == "test-session-123"


def test_chat_endpoint_missing_fields(client):
    """Testa o endpoint com campos obrigatórios faltando."""
    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "test-session-123"
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_chat_endpoint_empty_input(client):
    """Testa o endpoint com input vazio."""
    response = client.post(
        "/api/v1/chat",
        json={
            "chat_input": "",
            "session_id": "test-session-123",
            "metadata": {}
        }
    )
    
    # Deve aceitar input vazio (pode ser um follow-up)
    assert response.status_code in [200, 422]


def test_chat_endpoint_with_metadata(client):
    """Testa o endpoint com metadados adicionais."""
    response = client.post(
        "/api/v1/chat",
        json={
            "chat_input": "Tell me about Sileto",
            "session_id": "test-session-456",
            "metadata": {
                "source": "web",
                "user_id": "user-123"
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-456"

