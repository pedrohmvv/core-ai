"""
Servidor FastAPI.

Documentação interativa (Swagger/OpenAPI):
- Swagger UI: GET /docs
- ReDoc: GET /redoc
- Especificação OpenAPI JSON: GET /openapi.json
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
from fastapi.middleware.cors import CORSMiddleware

from app.chat.adapter.input.api.v1.chat import chat_router
from app.container import Container
from app.infrastructure.vector_store import create_vector_store
from core.config import config
from core.exceptions import CustomException
from fastapi.responses import JSONResponse
from fastapi import Request

logger = logging.getLogger(__name__)

# Tags OpenAPI para agrupar e descrever endpoints no Swagger
OPENAPI_TAGS = [
    {
        "name": "chat",
        "description": "Endpoints de chat: enviar mensagens, listar conversas e recuperar histórico por usuário ou sessão.",
    },
]


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Inicializa recursos compartilhados antes de aceitar requisições."""
    logger.info("Inicializando Vector Store...")
    await create_vector_store()
    logger.info("Vector Store pronta.")
    yield


def init_routers(app_: FastAPI) -> None:
    """Inicializa os routers da aplicação."""
    container = Container()
    chat_router.container = container
    app_.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])


def init_listeners(app_: FastAPI) -> None:
    """Inicializa os listeners da aplicação."""
    # Exception handler
    @app_.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        return JSONResponse(
            status_code=exc.code,
            content={"error_code": exc.error_code, "message": exc.message},
        )


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""
    app_ = FastAPI(
        title="CORE-AI API",
        description="API para sistema de análise de exames de sangue e chat nutricional com RAG usando LangGraph e Google Gemini.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    
    # # CORS
    # app_.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=["*"],
    #     allow_credentials=True,
    #     allow_methods=["*"],
    #     allow_headers=["*"],
    # )
    
    init_routers(app_=app_)
    init_listeners(app_=app_)
    
    return app_


app = create_app()

