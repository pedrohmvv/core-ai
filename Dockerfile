# Dockerfile para deploy do Sileto LangGraph no Azure
# Suporta: Azure Container Apps, Azure App Service, AKS

FROM python:3.13-slim

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Configurações do uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Evitar buffers no stdout/stderr (logs em tempo real)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema (psycopg precisa de libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de dependência
COPY pyproject.toml uv.lock ./

# Instalar dependências sem instalar o projeto em si (cache eficiente)
RUN uv sync --frozen --no-install-project --no-dev

# Copiar código da aplicação
COPY src/ ./src/

# Garantir que o ambiente virtual está no PATH
ENV PATH="/app/.venv/bin:$PATH"

# Porta exposta (Azure usa PORT via env)
EXPOSE 8000

# Variáveis para produção
ENV ENV=prod
ENV APP_HOST=0.0.0.0

# Comando de inicialização
# Azure Container Apps / App Service injetam PORT automaticamente
CMD ["python", "-m", "src.main", "--env", "prod"]

