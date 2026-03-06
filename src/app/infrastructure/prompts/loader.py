"""
Carregador de prompts Jinja2.
"""
from pathlib import Path
from jinja2 import Template


def load_prompt(prompt_name: str) -> Template:
    """
    Carrega um prompt jinja2 a partir de um arquivo.
    
    Args:
        prompt_name: Nome do arquivo do prompt (ex: "agent.jinja2")
    
    Returns:
        Template: Template do prompt jinja2
    """
    # Obtém o diretório raiz do projeto
    project_root = Path(__file__).parent.parent.parent.parent.parent
    prompts_dir = project_root / "src" / "app" / "infrastructure" / "prompts"
    
    # Se não encontrar em src_dev, tenta em src/app/infrastructure/prompts
    if not prompts_dir.exists():
        prompts_dir = Path(__file__).parent
    
    prompt_path = prompts_dir / prompt_name
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt não encontrado: {prompt_path}")
    
    with open(prompt_path, "r", encoding="utf-8") as file:
        return Template(file.read())

