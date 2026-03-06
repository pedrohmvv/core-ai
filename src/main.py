"""
Ponto de entrada da aplicação.
"""
import logging
import os
import sys
from pathlib import Path

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Adicionar o diretório src ao path para que os imports funcionem
# Isso permite executar tanto como módulo (python -m src.main) quanto diretamente
SRC_DIR = Path(__file__).parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import click
import uvicorn

from core.config import config


@click.command()

@click.option(
    "--env",
    type=click.Choice(["local", "dev", "prod"], case_sensitive=False),
    default="local",
)

@click.option(
    "--debug",
    type=click.BOOL,
    is_flag=True,
    default=False,
)

def main(env: str, debug: bool):
    """Inicia o servidor FastAPI."""
    os.environ["ENV"] = env
    os.environ["DEBUG"] = str(debug)
    
    # Atualiza nível de log se debug for True
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug(f"Modo debug ativado para ambiente: {env}")
    else:
        logger.info(f"Iniciando em ambiente: {env}")
    
    # Ajustar o caminho do app para funcionar independente de onde é executado
    # Se executado como módulo (python -m src.main), usar caminho relativo
    # Se executado diretamente (python src/main.py), também funciona
    app_path = "app.server:app"
    
    uvicorn.run(
        app=app_path,
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=True if config.ENV != "production" else False,
        workers=1,
    )


if __name__ == "__main__":
    main()

