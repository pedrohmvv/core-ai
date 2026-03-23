# Documentação da API — Core-AI (Chat)

Base URL (local): `http://localhost:8000`  
Prefixo do Chat: `/api/v1/chat`

A API de chat permite que o nutricionista inicie uma conversa enviando um **PDF de exames** (primeira mensagem) e, em seguida, interaja por **mensagens de texto**. Opcionalmente, o cliente pode enviar **dados do paciente** (sexo, idade, alergias, remédios) para contextualizar o relatório gerado pelo agente.

---

## Regras de negócio

1. **Primeira mensagem do chat**  
   Deve ser **sempre um PDF** (campo `pdf_base64`). O backend decodifica o base64, extrai o texto com pypdf e processa esse texto no fluxo. Não é permitido iniciar uma conversa apenas com `chat_input`.

2. **Mensagens seguintes**  
   Devem ser **texto** (campo `chat_input`). Não é permitido enviar um novo PDF no meio da conversa; use a mesma `session_id` e envie apenas `chat_input`.

3. **Informações do paciente**  
   Os campos `sexo`, `idade`, `alergias` e `remedios` são **opcionais**. Quando enviados (geralmente na primeira mensagem, junto com o PDF), são incluídos no prompt do agente para personalizar o relatório (dosagens, interações fármaco-nutriente, contraindicações, alergias). Se não forem reenviados nas mensagens seguintes, o backend reutiliza os valores já guardados no checkpoint da sessão.

---

## Endpoints

### POST `/api/v1/chat` — Enviar mensagem (PDF ou texto)

Processa uma mensagem e retorna a resposta do agente com perguntas de follow-up sugeridas.

**Corpo da requisição (JSON)**

| Campo         | Tipo     | Obrigatório | Descrição |
|---------------|----------|-------------|-----------|
| `pdf_base64`  | string   | Sim*        | Conteúdo do PDF em base64. Obrigatório **apenas na primeira mensagem** da conversa. |
| `chat_input`  | string   | Sim*        | Mensagem em texto. Obrigatório **apenas nas mensagens após a primeira**. |
| `session_id`  | string   | Sim         | Identificador da sessão (conversa). Use o mesmo em todas as mensagens da mesma conversa. |
| `user_id`     | string   | Sim         | Identificador do usuário (nutricionista). |
| `sexo`        | string   | Não         | Sexo do paciente (ex.: `"M"`, `"F"`, `"Outro"`). |
| `idade`       | integer  | Não         | Idade do paciente em anos. |
| `alergias`    | array    | Não         | Lista de alergias (ex.: `["lactose", "penicilina"]`). Default: `[]`. |
| `remedios`    | array    | Não         | Lista de remédios em uso (ex.: `["Omeprazol 20mg", "Levotiroxina 50mcg"]`). Default: `[]`. |
| `metadata`    | object   | Não         | Metadados adicionais. Default: `{}`. |

\* É necessário enviar **exatamente um** de: `pdf_base64` (primeira mensagem) ou `chat_input` (demais mensagens). Não envie os dois no mesmo request.

**Resposta (200)**

```json
{
  "response": "Texto da resposta do agente em Markdown...",
  "session_id": "sess-abc-123",
  "followUpQuestions": [
    "Pergunta de follow-up 1?",
    "Pergunta de follow-up 2?"
  ]
}
```

**Erros**

| Código | Situação |
|--------|----------|
| 400    | Primeira mensagem sem `pdf_base64`; ou mensagem seguinte com `pdf_base64`; ou PDF/base64 inválido; ou nenhum de `pdf_base64`/`chat_input` enviado. |
| 422    | Validação do body (campos obrigatórios faltando, tipos inválidos). |

**Exemplo — Primeira mensagem (PDF + dados do paciente)**

```json
POST /api/v1/chat
Content-Type: application/json

{
  "pdf_base64": "<string base64 do PDF dos exames>",
  "session_id": "sess-001",
  "user_id": "user-456",
  "sexo": "F",
  "idade": 42,
  "alergias": ["lactose", "penicilina"],
  "remedios": ["Levotiroxina 50mcg", "Omeprazol 20mg"],
  "metadata": {}
}
```

**Exemplo — Mensagem seguinte (texto)**

```json
POST /api/v1/chat
Content-Type: application/json

{
  "chat_input": "Quais alimentos devo evitar com essa medicação?",
  "session_id": "sess-001",
  "user_id": "user-456",
  "metadata": {}
}
```

---

### GET `/api/v1/chat/user/{user_id}` — Listar chats do usuário

Retorna a lista de chats do usuário, ordenados do mais recente ao mais antigo.

**Parâmetros de path**

| Nome     | Tipo   | Descrição        |
|----------|--------|------------------|
| `user_id` | string | ID do usuário. |

**Resposta (200)**

```json
{
  "user_id": "user-456",
  "chats": [
    {
      "id": "uuid-do-chat",
      "title": "Resultados do Hemograma",
      "created_at": "2026-03-05T22:17:30.421773+00:00"
    }
  ]
}
```

---

### GET `/api/v1/chat/session/{session_id}/messages` — Mensagens da sessão

Retorna as mensagens (user e assistant) da sessão indicada.

**Parâmetros de path**

| Nome         | Tipo   | Descrição          |
|--------------|--------|--------------------|
| `session_id` | string | ID da sessão.     |

**Resposta (200)**

```json
{
  "session_id": "sess-001",
  "messages": [
    {
      "role": "user",
      "content": "Conteúdo da mensagem do usuário...",
      "timestamp": "2026-03-05T22:17:30.421773+00:00"
    },
    {
      "role": "assistant",
      "content": "Resposta do agente...",
      "timestamp": "2026-03-05T22:17:35.000000+00:00"
    }
  ]
}
```

---

### GET `/api/v1/chat/user/{user_id}/conversations` — Conversas do usuário

Retorna todas as conversas do usuário com suas mensagens.

**Parâmetros de path**

| Nome     | Tipo   | Descrição        |
|----------|--------|------------------|
| `user_id` | string | ID do usuário. |

**Resposta (200)**

```json
{
  "user_id": "user-456",
  "total_conversations": 2,
  "conversations": [
    {
      "session_id": "sess-001",
      "messages": [
        { "role": "user", "content": "...", "timestamp": "..." },
        { "role": "assistant", "content": "...", "timestamp": "..." }
      ],
      "message_count": 2
    }
  ]
}
```

---

## Fluxo recomendado no cliente

1. **Nova conversa**  
   Gerar um novo `session_id` (ex.: UUID).  
   Enviar **POST** com `pdf_base64` (PDF dos exames em base64), `session_id`, `user_id` e, se disponível, `sexo`, `idade`, `alergias`, `remedios`.

2. **Continuar a conversa**  
   Usar o mesmo `session_id`.  
   Enviar **POST** apenas com `chat_input`, `session_id` e `user_id`. Opcionalmente reenviar dados do paciente se tiverem sido atualizados.

3. **Listar chats / mensagens**  
   Usar **GET** `/api/v1/chat/user/{user_id}` para listar chats e **GET** `/api/v1/chat/session/{session_id}/messages` para o histórico de uma sessão.

---

## Documentação interativa (Swagger / ReDoc)

Com a API rodando em ambiente local ou dev:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)  
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)  
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

Em produção (`--env prod`), essas rotas podem estar desativadas. Os schemas e exemplos dos DTOs estão definidos em `src/app/chat/application/dto/chat_dto.py`.
