# Plano de Migração: HuggingFace Embeddings → Google Generative AI Embeddings

## Contexto e Motivação

O modelo `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` era carregado localmente no servidor Railway, mantendo o processo Python consumindo **~0.75 vCPU constante** mesmo sem requisições ativas. Isso gerou um custo de **$15.98/mês só de CPU** no primeiro mês de produção.

A solução é substituir o modelo HuggingFace pelo **Google Generative AI Embeddings** (`text-multilingual-embedding-002`), que executa inferência na API Google — eliminando o processo local e zerando o consumo de CPU/RAM associado ao modelo de embeddings no Railway.

**Regra inviolável:** o modelo de embeddings usado na **ingestão** (notebook) deve ser **exatamente o mesmo** usado nas **queries em produção** (API). Dois modelos diferentes geram espaços semânticos incompatíveis, tornando a busca por similaridade sem sentido.

---

## Comparativo de Modelos

| Atributo | Modelo Atual | Modelo Novo |
|---|---|---|
| Nome | `paraphrase-multilingual-MiniLM-L12-v2` | `text-multilingual-embedding-002` |
| Provider | HuggingFace (local) | Google Generative AI (API) |
| Dimensões | 384 | 768 |
| Suporte a PT-BR | Sim | Sim (nativo) |
| Custo em produção | ~$15.98/mês (CPU Railway) | ~$0.01–0.05/mês (API Google) |
| Custo de ingestão | Gratuito (local) | Gratuito (free tier Google) |

---

## Impacto Esperado na Fatura Railway

| Recurso | Antes | Depois |
|---|---|---|
| CPU Railway | ~$15.98/mês | ~$1–2/mês |
| RAM Railway | ~$9.91/mês | ~$4–5/mês |
| Google Embeddings API | $0 | ~$0.05/mês |
| **Total estimado** | **~$25.94/mês** | **~$7/mês** |

---

## Pré-requisitos

1. `GOOGLE_API_KEY` já configurada no `.env` local e nas variáveis de ambiente do Railway — a mesma chave usada pelo Gemini LLM.
2. Billing ativo no Google AI Studio (para produção). Para ingestão, o free tier é suficiente com throttling.
3. `langchain-google-genai` adicionado como dependência:
   ```bash
   uv add langchain-google-genai
   ```

---

## Arquivos Alterados

### 1. `src/app/infrastructure/vector_store/embeddings.py`

**Substituição completa do arquivo.**

```python
"""
Módulo para criação do serviço de embeddings.

Usa Google Generative AI Embeddings (text-multilingual-embedding-002):
- 768 dimensões
- Suporte nativo a português
- Inferência na API Google — zero CPU/RAM no servidor Railway
- Mesmo modelo usado no notebook de ingestão e na API em produção
"""
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.config import config


def create_embeddings_service() -> GoogleGenerativeAIEmbeddings:
    """
    Cria o serviço de embeddings usando Google Generative AI.

    IMPORTANTE: Este modelo deve ser o mesmo usado no pipeline de ingestão
    (notebooks/embeddings.ipynb). Qualquer divergência entre o modelo de
    ingestão e o modelo de query resulta em buscas sem sentido semântico.

    Returns:
        GoogleGenerativeAIEmbeddings configurado e pronto para uso.
    """
    return GoogleGenerativeAIEmbeddings(
        model="models/text-multilingual-embedding-002",
        google_api_key=config.GOOGLE_API_KEY,
    )
```

---

### 2. `src/core/config.py`

**Alterar apenas a variável `EMBEDDING_MODEL_NAME`.**

```python
# DE:
EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

# PARA:
EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL_NAME",
    "models/text-multilingual-embedding-002",
)
```

---

### 3. `notebooks/embeddings.ipynb`

**Alterações no notebook de ingestão:**

#### 3a. Substituir o bloco de imports de embeddings

```python
# DE:
from langchain_huggingface import HuggingFaceEmbeddings

# PARA:
from langchain_google_genai import GoogleGenerativeAIEmbeddings
```

#### 3b. Adicionar célula de DROP TABLE antes da criação do vector store

Esta célula deve ser executada **uma única vez** antes da reingestão. A tabela precisa ser recriada porque a dimensão mudou de 384 para 768 — estrutura incompatível com a tabela existente.

```python
import psycopg

with psycopg.connect(config.DB_URI_SYNC) as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {VECTOR_TABLE_NAME};")
    conn.commit()

logger.info("Tabela '%s' dropada. Pronto para reingestão com 768 dimensões.", VECTOR_TABLE_NAME)
```

#### 3c. Substituir a instanciação do modelo de embeddings

```python
# DE:
embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    model_kwargs={"device": "mps"},
    encode_kwargs={"normalize_embeddings": True},
)

# PARA:
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-multilingual-embedding-002",
    google_api_key=config.GOOGLE_API_KEY,
)
```

#### 3d. Substituir o loop de inserção em lotes pelo loop chunk a chunk com throttling

O loop de batch existente deve ser **completamente substituído** pelo seguinte, que insere um chunk por vez com pausa automática e retry em caso de rate limit (429):

```python
PAUSA_ENTRE_CHUNKS: float = 0.5  # segundos entre cada chunk
PAUSA_RATE_LIMIT: int = 60       # segundos de espera ao receber 429

erros: list[int] = []

for i, doc in enumerate(all_documents):
    sucesso = False
    tentativas = 0

    while not sucesso:
        try:
            vector_store.add_documents([doc])
            logger.info(
                "[%d/%d] ✅ %s p.%s",
                i + 1, len(all_documents),
                doc.metadata.get("source", "?"),
                doc.metadata.get("page", "?"),
            )
            sucesso = True
            time.sleep(PAUSA_ENTRE_CHUNKS)

        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                tentativas += 1
                logger.warning(
                    "[%d/%d] ⚠️ Rate limit (tentativa %d). Aguardando %ds...",
                    i + 1, len(all_documents), tentativas, PAUSA_RATE_LIMIT,
                )
                time.sleep(PAUSA_RATE_LIMIT)
            else:
                logger.error("[%d/%d] ❌ Erro fatal: %s", i + 1, len(all_documents), e)
                erros.append(i)
                break

if erros:
    logger.warning("Chunks com erro fatal (índices): %s", erros)
else:
    logger.info("✅ Pipeline concluído. Tabela '%s' populada com 768 dimensões.", VECTOR_TABLE_NAME)
```

---

## Arquivos Não Alterados

Os arquivos abaixo **não precisam de nenhuma modificação**. A troca de provider é totalmente encapsulada em `embeddings.py` e transparente para o restante do sistema.

- `src/app/infrastructure/vector_store/factory.py`
- `src/app/infrastructure/vector_store/engine.py`
- `src/app/infrastructure/langgraph/service.py`
- `src/app/infrastructure/langgraph/nodes.py`
- `src/app/infrastructure/langgraph/tools.py`
- `src/app/infrastructure/langgraph/state.py`
- `src/app/server.py`
- `src/app/container.py`
- `src/main.py`
- Todos os prompts Jinja2
- Variáveis de ambiente no Railway (a `GOOGLE_API_KEY` existente já é suficiente)

---

## Ordem de Execução

Execute nesta ordem exata para evitar inconsistências entre banco e API:

```
1. uv add langchain-google-genai
2. Aplicar alterações em embeddings.py e config.py
3. Rodar o notebook localmente:
   a. Célula de DROP TABLE (uma única vez)
   b. Pipeline completo de ingestão com throttling
   c. Célula de validação (similarity_search) — confirmar resultados coerentes
4. git add . && git commit -m "feat: migrar embeddings HuggingFace → Google Generative AI (768d)"
5. git push → deploy automático no Railway
```

**Não fazer deploy da API antes de concluir a reingestão.** Se a API subir com o novo modelo de embeddings antes de o banco ser recriado, todas as queries retornarão resultados errados ou erro de dimensão.

---

## Validação Pós-Migração

Após o deploy, verificar no Railway:

- **CPU Usage** do serviço `core-ai`: deve cair de ~0.75 vCPU para ~0.05–0.1 vCPU em idle
- **Memory Usage**: deve cair proporcionalmente com a remoção do modelo em memória
- **Teste funcional**: enviar um PDF pelo chat e verificar se a resposta do agente contém citações coerentes com o conteúdo do banco

Se as citações estiverem incoerentes ou vazias, significa que a reingestão não foi concluída corretamente — rodar o notebook novamente a partir da célula de DROP TABLE.