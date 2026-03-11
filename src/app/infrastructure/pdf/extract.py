"""Extração de texto a partir de PDF (base64)."""
import base64
import logging
from io import BytesIO

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf_base64(pdf_base64: str) -> str:
    """
    Decodifica um PDF em base64 e extrai o texto com pypdf.

    Args:
        pdf_base64: String base64 do conteúdo do PDF.

    Returns:
        Texto extraído de todas as páginas concatenado.

    Raises:
        ValueError: Se o base64 for inválido ou o arquivo não for um PDF válido.
    """
    try:
        raw = base64.b64decode(pdf_base64, validate=True)
    except Exception as e:
        logger.warning(f"Falha ao decodificar base64: {e}")
        raise ValueError("Conteúdo base64 inválido.") from e

    if not raw:
        raise ValueError("Conteúdo do PDF está vazio.")

    try:
        reader = PdfReader(BytesIO(raw))
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        result = "\n\n".join(parts).strip()
        if not result:
            raise ValueError("Nenhum texto extraído do PDF (pode ser um PDF apenas com imagens).")
        return result
    except ValueError:
        raise
    except Exception as e:
        logger.warning(f"Falha ao extrair texto do PDF: {e}")
        raise ValueError("Arquivo inválido ou não é um PDF suportado.") from e
