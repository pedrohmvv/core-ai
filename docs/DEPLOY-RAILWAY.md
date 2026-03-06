# Deploy do Core-AI (Nutri-AI) no Railway

Este guia cobre o deploy da **API FastAPI** e do **PostgreSQL com pgvector** no Railway. O banco local (Docker) é substituído pelo Postgres gerenciado pelo Railway com a extensão pgvector.

---

## 1. Pré-requisitos

- Conta no [Railway](https://railway.app)
- Repositório do projeto no GitHub (recomendado para deploy contínuo)
- **GOOGLE_API_KEY** (Gemini) para o LLM

---

## 2. Criar o projeto e o banco de dados (PostgreSQL + pgvector)

### 2.1. Novo projeto no Railway

1. Acesse [railway.app](https://railway.app) e crie um novo projeto (ou use um existente).

### 2.2. Adicionar PostgreSQL com pgvector

O Railway não oferece pgvector no Postgres “padrão”. Use o **template com pgvector**:

1. No projeto, clique em **"+ New"** → **"Template"**.
2. Busque por **"Postgres with pgVector Engine"** ou use o link direto:  
   [Deploy Postgres with pgVector Engine](https://railway.com/new/template/postgres-with-pgvector-engine)
3. Selecione o projeto e confirme o deploy. O template sobe um Postgres com a extensão **vector** já disponível.

Após o deploy, o serviço Postgres aparecerá no projeto e as variáveis de conexão (por exemplo `DATABASE_URL`) estarão disponíveis.

### 2.3. Inicializar o schema (extensão + tabelas do chat)

É preciso rodar **uma vez** os scripts em `init-db/` nesse banco:

1. **Extensão pgvector** (o template já pode tê-la; rodar não quebra):  
   `init-db/01-init-vector.sql`
2. **Tabelas do chat**:  
   `init-db/01-chat-tables.sql`

**Opção A – Pelo Railway (recomendado)**  
No painel do serviço Postgres, abra a aba **"Data"** ou **"Query"** e execute o conteúdo dos dois arquivos (ou use o terminal do Railway se disponível).

**Opção B – Da sua máquina com `psql`**  
Railway expõe variáveis como `DATABASE_URL` (público) ou `DATABASE_URL_PRIVATE`. Use a URL no `psql`:

```bash
# Instale psql se necessário (macOS: brew install libpq && brew link --force libpq)
# No painel do Railway, copie DATABASE_URL (ex.: postgresql://postgres:xxx@xxx.railway.app:5432/railway)

psql "postgresql://postgres:SENHA@HOST:PORTA/railway" -f init-db/01-init-vector.sql
psql "postgresql://postgres:SENHA@HOST:PORTA/railway" -f init-db/01-chat-tables.sql
```

A tabela **`pg_langchain_vectors`** é criada automaticamente pelo LangChain na primeira ingestão/uso do RAG; não é criada por esses scripts.

---

## 3. Deploy da API (serviço FastAPI)

### 3.1. Novo serviço a partir do repositório

1. No mesmo projeto Railway, **"+ New"** → **"GitHub Repo"**.
2. Conecte o GitHub (se ainda não estiver) e escolha o repositório do **nutri-ai**.
3. O Railway detecta o **Dockerfile** na raiz e usa ele para o build. Confirme que o **Root Directory** está vazio (raiz do repo).
4. O serviço será criado e fará o primeiro build.

### 3.2. Usar o Dockerfile

O projeto já tem um **Dockerfile** na raiz. O Railway usa ele por padrão quando existe. O comando de start é:

```dockerfile
CMD ["python", "-m", "src.main", "--env", "prod"]
```

Não é necessário alterar nada para o Railway usar a porta: a aplicação lê a variável **`PORT`** (que o Railway define) e usa em vez de `APP_PORT`.

### 3.3. Variáveis de ambiente

No painel do serviço da **API** (não do Postgres):

1. Abra **"Variables"**.
2. **Vincule o banco**: em **"Add variable"** ou **"Variables"** → **"Add Reference"**, escolha as variáveis do serviço **Postgres** (por exemplo **`DATABASE_URL`**). Assim a API recebe a URL do banco automaticamente.
3. Defina as variáveis obrigatórias:

| Variável            | Obrigatório | Descrição |
|---------------------|------------|-----------|
| `DATABASE_URL`      | Sim (referência) | Referência ao Postgres (Railway preenche ao vincular) |
| `GOOGLE_API_KEY`    | Sim | Chave da API Google (Gemini) |
| `GOOGLE_GEMINI_MODEL` | Não | Ex.: `gemini-2.5-flash` (default) |
| `ENV`               | Não | Use `prod` em produção (o CMD já usa `--env prod`) |
| `PORT`              | Não | Definido pelo Railway; não precisa configurar |

Opcionais (podem ficar em default):

- `EMBEDDING_MODEL_NAME` – modelo de embeddings (ex.: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`)
- `VECTOR_STORE_TABLE_NAME` – ex.: `pg_langchain_vectors`
- `CHAT_HISTORY_TABLE_NAME` – ex.: `chat_history`

A aplicação usa **`DATABASE_URL`** quando existir (conexão com o Postgres do Railway) e ignora `DB_POSTGRESDB_*` nesse caso.

### 3.4. Domínio e porta

- Em **"Settings"** do serviço da API, em **"Networking"**, clique em **"Generate Domain"** para obter um URL público (ex.: `https://seu-servico.up.railway.app`).
- O Railway injeta **`PORT`**; a API já está preparada para usá-la.

---

## 4. Resumo do fluxo

1. **Projeto Railway** criado.
2. **Postgres com pgvector** adicionado via template “Postgres with pgVector Engine”.
3. **Scripts `init-db/`** executados uma vez no banco (extensão vector + tabelas do chat).
4. **Serviço da API** criado a partir do repo (Dockerfile), com **referência a `DATABASE_URL`** do Postgres e **`GOOGLE_API_KEY`** definida.
5. **Domínio** gerado para a API; acesse `/docs` para a documentação Swagger.

---

## 5. Migrar banco local (Docker) para o Railway

Se você já tem dados no Postgres que roda no Docker (por exemplo `nutriai-postgres`) e quer levar tudo para o Postgres do Railway:

### 5.1. Fazer o dump do banco no Docker

Na raiz do projeto (ou em qualquer pasta onde queira salvar o dump):

```bash
# Container e DB conforme README: nutriai-postgres, user admin, DB nutriai_db
docker exec nutriai-postgres pg_dump -U admin --no-owner --no-acl nutriai_db > dump.sql
```

Isso gera o arquivo **`dump.sql`** com schema + dados (tabelas do chat, `pg_langchain_vectors`, extensão vector, etc.). Os flags `--no-owner` e `--no-acl` evitam erros de permissão ao restaurar no Railway.

### 5.2. Restaurar no Postgres do Railway

1. No painel do Railway, abra o serviço **Postgres** e copie a **`DATABASE_URL`** (ou `DATABASE_URL_PRIVATE`; use a pública se estiver fora da rede Railway).
2. Se a URL vier como `postgres://`, o `psql` aceita; para outros clientes pode ser preciso usar `postgresql://`.
3. Com **`psql`** instalado (ex.: `brew install libpq && brew link --force libpq` no macOS):

```bash
psql "DATABASE_URL_DO_RAILWAY" -f dump.sql
```

Exemplo (substitua pela sua URL):

```bash
psql "postgresql://postgres:SENHA@containers-us-west-xxx.railway.app:5432/railway" -f dump.sql
```

Se aparecerem erros do tipo “relation already exists”, o Railway já tem tabelas (por exemplo dos scripts `init-db/`). Você pode:

- **Opção A**: Restaurar num banco vazio (crie um novo DB no Railway só para isso, ou use um projeto novo) e depois apontar a API para ele; ou  
- **Opção B**: Dropar as tabelas no Railway e rodar de novo o `psql ... -f dump.sql` (só se não precisar do que está lá).

### 5.3. Resumo rápido

| Onde        | Comando |
|------------|---------|
| **Dump**   | `docker exec nutriai-postgres pg_dump -U admin --no-owner --no-acl nutriai_db > dump.sql` |
| **Restore**| `psql "SUA_DATABASE_URL_RAILWAY" -f dump.sql` |

Depois da restauração, a API no Railway (com `DATABASE_URL` apontando para esse Postgres) passa a usar os mesmos dados que você tinha no Docker.

---

## 6. Ingestão RAG (base de conhecimento) em produção

O pipeline de embeddings está no notebook **`notebooks/embeddings.ipynb`**. Em produção:

- **Opção A**: Rodar o notebook **localmente** apontando para o banco do Railway: defina no ambiente (ou `.env`) apenas **`DATABASE_URL`** com a URL pública do Postgres (e, se necessário, as outras variáveis usadas pelo notebook). Execute as células para popular **`pg_langchain_vectors`**.
- **Opção B**: Criar um job/script no Railway (ou em outro lugar) que rode o mesmo pipeline com **`DATABASE_URL`** do ambiente Railway, para não depender da sua máquina.

---

## 7. Troubleshooting

- **API não inicia / 503**: Confira os logs do serviço. Verifique se **`DATABASE_URL`** está referenciado e se o Postgres está no mesmo projeto (ou acessível).
- **Erro de conexão ao banco**: Use **`DATABASE_URL_PRIVATE`** se a API e o Postgres estiverem no mesmo projeto (recomendado em produção).
- **Tabela ou extensão não existe**: Garanta que rodou `01-init-vector.sql` e `01-chat-tables.sql` no banco do Railway.
- **Porta**: A aplicação usa **`PORT`** quando definida (Railway); não é necessário definir **`APP_PORT`** no Railway.

---

*Documento para o projeto Core-AI (Nutri-AI) — deploy na Railway com PostgreSQL + pgvector.*
