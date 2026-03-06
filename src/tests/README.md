# Guia de Testes

Este diretório contém os testes da aplicação Sileto LangGraph.

## 📋 Estrutura de Testes

```
tests/
├── conftest.py              # Configurações e fixtures compartilhadas
├── app/
│   └── chat/
│       ├── test_chat_service.py    # Testes unitários do serviço
│       └── test_chat_api.py        # Testes de integração da API
```

## 🧪 Tipos de Testes

### 1. Testes Unitários

Testam componentes isolados com mocks:

```bash
pytest src/tests/app/chat/test_chat_service.py -v
```

**O que testa:**
- Processamento de mensagens
- Conversão para DTOs
- Lógica de negócio isolada

### 2. Testes de Integração (API)

Testam o endpoint completo com TestClient:

```bash
pytest src/tests/app/chat/test_chat_api.py -v
```

**O que testa:**
- Endpoints da API
- Validação de requests
- Respostas corretas
- Tratamento de erros

## 🚀 Como Executar

### Todos os Testes

```bash
# Do diretório raiz do projeto
pytest src/tests/ -v

# Ou do diretório src/
cd src
pytest tests/ -v
```

### Testes Específicos

```bash
# Apenas testes unitários
pytest src/tests/app/chat/test_chat_service.py -v

# Apenas testes de API
pytest src/tests/app/chat/test_chat_api.py -v

# Teste específico
pytest src/tests/app/chat/test_chat_api.py::test_chat_endpoint_success -v
```

### Com Cobertura

```bash
pytest src/tests/ --cov=app --cov-report=html
```

## 📝 Adicionando Novos Testes

### Exemplo: Teste Unitário

```python
@pytest.mark.asyncio
async def test_meu_novo_teste(mock_langgraph_service):
    service = ChatService(langgraph_service=mock_langgraph_service)
    # ... seu teste
```

### Exemplo: Teste de API

```python
def test_novo_endpoint(client):
    response = client.post("/api/v1/chat", json={...})
    assert response.status_code == 200
```

## 🔧 Fixtures Disponíveis

- `mock_langgraph_service`: Mock do LangGraphService
- `chat_service`: Instância do ChatService com mock
- `app`: Aplicação FastAPI configurada
- `client`: TestClient para testes de API

## ⚠️ Notas

- Os testes usam mocks para não depender de infraestrutura real
- Para testes end-to-end, configure as variáveis de ambiente
- Testes de integração podem ser lentos (dependem de mocks configurados)

