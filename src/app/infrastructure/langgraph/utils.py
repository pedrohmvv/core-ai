import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Union
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.messages import message_to_dict
import psycopg
from core.config import config
from app.infrastructure.prompts import load_prompt
from app.chat.application.exception import BadRequestException, RateLimitException

logger = logging.getLogger(__name__)


def _content_to_string(content: Union[str, List[Any], Any]) -> str:
    """
    Normaliza o conteúdo de uma mensagem (ex.: AIMessage.content) para string.
    O Gemini pode retornar content como lista de blocos [{"type": "text", "text": "..."}]
    ou com "parts" aninhados; aceita também blocos que são só strings.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if "text" in block:
                    parts.append(str(block["text"]))
                elif "parts" in block:
                    parts.append(_content_to_string(block["parts"]))
                elif "inline_data" in block:
                    continue
            else:
                parts.append(str(block))
        return "\n".join(p for p in parts if p) if parts else ""
    return str(content)


def get_error_message_from_exception(exception: Exception) -> str:
    """
    Mapeia exceções do LLM para mensagens de erro amigáveis.
    
    Args:
        exception: Exceção original
        
    Returns:
        Mensagem de erro amigável para exibir no chat
    """
    error_str = str(exception).lower()
    error_type = type(exception).__name__.lower()
    
    # Verifica se é erro de rate limit
    rate_limit_indicators = [
        "rate limit",
        "rate_limit",
        "429",
        "too many requests",
        "quota exceeded",
        "requests per minute",
        "throttle"
    ]
    
    if any(indicator in error_str for indicator in rate_limit_indicators) or "ratelimit" in error_type:
        logger.warning(f"Rate limit detectado: {exception}")
        return RateLimitException.message
    
    # Para outros erros relacionados ao modelo/API, usa BadRequest
    logger.error(f"Erro no modelo LLM: {exception}")
    return BadRequestException.message

def generate_follow_up_questions(
    llm,
    last_agent_message: str,
    last_user_message: str = "",
    source_documents: str = "",
) -> List[str]:
    """
    Gera perguntas de follow-up baseadas na resposta do agente principal.
    
    Args:
        llm: Instância do LLM para gerar as perguntas
        last_agent_message: Última resposta do agente
        last_user_message: Última mensagem do usuário para contexto
        source_documents: Documentos RAG associados à última resposta
    
    Returns:
        Lista de perguntas de follow-up
    """
    try:
        # Renderiza o prompt de follow-up com a resposta do agente e documentos fonte
        follow_up_system_prompt = load_prompt("follow_up.jinja2").render(
            last_agent_message=last_agent_message,
            user_message=last_user_message,
            source_documents=source_documents,
        )
        
        # Prepara as mensagens (Gemini exige conteúdo não vazio no HumanMessage)
        messages = [
            SystemMessage(content=follow_up_system_prompt),
            HumanMessage(content="Retorne apenas o JSON com as perguntas de follow-up (campo follow_ups), conforme as instruções do sistema. Sem texto antes ou depois do JSON.")
        ]
        
        # Invoca o LLM diretamente (sem agente, já que não há ferramentas)
        try:
            response = llm.invoke(messages)
            # Extrai o conteúdo da resposta (Gemini pode retornar lista de blocos)
            raw = response.content if hasattr(response, 'content') else str(response)
            response_content = _content_to_string(raw)
        except Exception as e:
            logger.error(f"Erro ao chamar LLM para follow-up questions: {str(e)}")
            # Em caso de erro, retorna lista vazia de follow-ups (não quebra o fluxo)
            # O erro principal já foi tratado no agent_node
            return []
        
        # Tenta parsear o JSON da resposta
        try:
            # Remove markdown code blocks se houver
            if "```json" in response_content:
                response_content = response_content.split("```json")[1].split("```")[0].strip()
            elif "```" in response_content:
                response_content = response_content.split("```")[1].split("```")[0].strip()
            
            # Parse do JSON
            follow_ups_data = json.loads(response_content)
            # Extrai a lista de follow_ups do dicionário, ou retorna diretamente se já for lista
            if isinstance(follow_ups_data, dict):
                return follow_ups_data.get("follow_ups", [])
            elif isinstance(follow_ups_data, list):
                return follow_ups_data
            else:
                return []
        except json.JSONDecodeError as e:
            logger.warning(f"Follow-up: JSON inválido na resposta do LLM: {e}")
            return []
    
    except Exception as e:
        # Em caso de erro, retorna lista vazia
        logger.error(f"Erro ao gerar follow-up questions: {str(e)}")
        return []


def get_chat_summary_from_db(session_id: str) -> str:
    """
    Busca o resumo da conversa da tabela chat_summaries.
    
    Args:
        session_id: ID da sessão
        
    Returns:
        Resumo da conversa ou string vazia se não existir
    """
    try:
        conn = psycopg.connect(config.DB_URI_SYNC)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT chat_summary FROM chat_summaries WHERE session_id = %s",
                    (session_id,)
                )
                result = cur.fetchone()
                if result:
                    return result[0] or ""
                return ""
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Erro ao buscar resumo do banco: {e}")
        return ""


def save_chat_summary_to_db(session_id: str, summary: str):
    """
    Salva ou atualiza o resumo da conversa na tabela chat_summaries.
    
    Args:
        session_id: ID da sessão
        summary: Resumo da conversa a ser salvo
    """
    try:
        conn = psycopg.connect(config.DB_URI_SYNC)
        try:
            with conn.cursor() as cur:
                # Usa UPSERT (INSERT ... ON CONFLICT UPDATE)
                cur.execute(
                    """
                    INSERT INTO chat_summaries (session_id, chat_summary)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id) 
                    DO UPDATE SET chat_summary = EXCLUDED.chat_summary
                    """,
                    (session_id, summary)
                )
            conn.commit()
            logger.debug(f"Resumo salvo/atualizado para sessão: {session_id}")
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Erro ao salvar resumo no banco: {e}")


def save_message_to_db(session_id: str, message_obj: BaseMessage, has_summary: bool = False):
    """
    Serializa o objeto de mensagem e insere na tabela chat_history.
    
    Args:
        session_id: ID da sessão
        message_obj: Objeto de mensagem a ser salvo
        has_summary: Se True, salva summary como True na tabela chat_history
    """
    try:
        # message_to_dict gera exatamente a estrutura {"type": "...", "content": "...", ...}
        msg_dict = message_to_dict(message_obj)
        
        # Cria uma conexão direta para inserir na tabela chat_history
        conn = psycopg.connect(config.DB_URI_SYNC)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO chat_history (session_id, message, summary, sent_at) VALUES (%s, %s, %s, %s)",
                    (session_id, json.dumps(msg_dict), has_summary, datetime.now())
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"! Erro ao salvar histórico: {e}")


def check_chat_exists(session_id: str) -> bool:
    """
    Verifica se um chat (sessão) já existe na tabela chat.
    
    Args:
        session_id: ID da sessão (chat)
        
    Returns:
        True se o chat existe, False caso contrário
    """
    try:
        conn = psycopg.connect(config.DB_URI_SYNC)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM chat WHERE id = %s::uuid",
                    (session_id,)
                )
                result = cur.fetchone()
                return result is not None
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Erro ao verificar se chat existe: {e}")
        return False


def generate_chat_title(llm, user_message: str) -> str:
    """
    Gera um título breve para o chat baseado na primeira mensagem do usuário.
    
    Args:
        llm: Instância do LLM para gerar o título
        user_message: Primeira mensagem do usuário
        
    Returns:
        Título gerado para o chat (máximo 100 caracteres)
    """
    try:
        system_prompt = """Você é um assistente que gera títulos breves e descritivos para conversas.
Gere um título curto (máximo 10 palavras) baseado na primeira mensagem do usuário.
O título deve ser claro, conciso e refletir o assunto principal da conversa.
Retorne APENAS o título, sem aspas, sem formatação adicional, sem explicações."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Primeira mensagem do usuário: {user_message}")
        ]
        
        response = llm.invoke(messages)
        title = response.content if hasattr(response, 'content') else str(response)
        
        # Remove aspas e espaços extras, limita a 100 caracteres
        title = title.strip().strip('"').strip("'")
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title if title else "Nova Conversa"
    except Exception as e:
        logger.error(f"Erro ao gerar título do chat: {e}")
        # Em caso de erro, retorna um título padrão
        return "Nova Conversa"


def create_chat_record(session_id: str, user_id: str, title: str):
    """
    Cria um novo registro na tabela chat.
    
    Args:
        session_id: ID da sessão (chat) - será usado como id na tabela
        user_id: ID do usuário (pode ser UUID ou string qualquer)
        title: Título do chat
    """
    import uuid as uuid_lib
    
    try:
        conn = psycopg.connect(config.DB_URI_SYNC)
        try:
            with conn.cursor() as cur:
                # Verifica se user_id é um UUID válido
                is_uuid = False
                try:
                    uuid_lib.UUID(user_id)
                    is_uuid = True
                except (ValueError, AttributeError):
                    is_uuid = False
                
                # Tenta inserir: primeiro como UUID se for válido, senão como texto
                # Nota: Se a coluna for UUID e user_id não for UUID válido, vai falhar
                # e sugerir a migração
                if is_uuid:
                    cur.execute(
                        """
                        INSERT INTO chat (id, title, user_id, created_at)
                        VALUES (%s::uuid, %s, %s::uuid, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (session_id, title, user_id)
                    )
                else:
                    # Tenta inserir sem cast (assumindo que a coluna foi alterada para VARCHAR/TEXT)
                    # Se falhar, o erro será capturado abaixo
                    cur.execute(
                        """
                        INSERT INTO chat (id, title, user_id, created_at)
                        VALUES (%s::uuid, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (session_id, title, user_id)
                    )
            conn.commit()
            logger.info(f"Registro de chat criado: session_id={session_id}, user_id={user_id}, title={title}")
        finally:
            conn.close()
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Erro ao criar registro de chat: {e}")
        # Se o erro for relacionado ao tipo UUID, sugere alterar o schema
        if "invalid input syntax for type uuid" in error_msg.lower():
            logger.error(
                f"\n{'='*80}\n"
                f"ERRO: A coluna 'user_id' na tabela 'chat' está como UUID, mas o valor '{user_id}' não é um UUID válido.\n"
                f"SOLUÇÃO: Execute a migração no notebook 'new_table.ipynb' para alterar a coluna 'user_id' para VARCHAR/TEXT.\n"
                f"{'='*80}\n"
            )
        raise


def get_user_chats(user_id: str) -> List[Dict[str, Any]]:
    """
    Busca todos os chats de um usuário ordenados por data de criação (mais recentes primeiro).
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Lista de dicionários com chat_id, title e created_at
    """
    try:
        conn = psycopg.connect(config.DB_URI_SYNC)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, created_at
                    FROM chat
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id,)
                )
                rows = cur.fetchall()
                
                # Converte para lista de dicionários
                chats = []
                for row in rows:
                    chats.append({
                        "id": str(row[0]),  # UUID convertido para string
                        "title": row[1] or "Sem título",
                        "created_at": row[2].isoformat() if row[2] else None
                    })
                
                logger.info(f"Encontrados {len(chats)} chat(s) para user_id: {user_id}")
                return chats
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Erro ao buscar chats do usuário: {e}")
        raise