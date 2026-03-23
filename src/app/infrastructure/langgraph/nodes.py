import logging
from app.infrastructure.langgraph.state import GraphState
from app.infrastructure.prompts import load_prompt
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, RemoveMessage

from app.infrastructure.langgraph.tools import document_search_with_urls
from app.infrastructure.langgraph.utils import (
    generate_follow_up_questions,
    save_message_to_db,
    get_chat_summary_from_db,
    save_chat_summary_to_db,
    get_error_message_from_exception,
    check_chat_exists,
    generate_chat_title,
    create_chat_record,
    _content_to_string,
)
from langchain.agents import create_agent
from langchain_core.messages import trim_messages 
from langchain_core.messages.utils import count_tokens_approximately
#from app.infrastructure.slack.slack import send_message

logger = logging.getLogger(__name__)

# Notificações de erro para o Slack: desativadas; ative para reenviar no futuro.
ENABLE_SLACK_ERROR_NOTIFICATIONS = False


def create_chat_node(state: GraphState, llm) -> dict:
    """
    Cria um novo registro na tabela chat se o chat (sessão) não existir.
    Se o chat já existir, pula este nó sem fazer nada.
    
    Este nó deve ser executado no início do fluxo, antes de qualquer processamento.
    Nunca altera messages; retorna {} para não acionar operator.add no reducer.
    """
    session_id = state.get("sessionId")
    user_id = state.get("userId", "N/A")
    is_follow_up = state.get("isFollowUp", False)
    
    logger.info(f"Node: create_chat_node - Session: {session_id} - User: {user_id}")
    
    # Pula criação de chat para follow-ups (já existe)
    if is_follow_up:
        logger.debug("Pulando criação de chat para follow-up")
        return {}
    
    # Verifica se o chat já existe
    if check_chat_exists(session_id):
        logger.debug(f"Chat já existe no banco: {session_id}")
        return {}
    
    # Chat não existe, precisa criar
    logger.info(f"Criando novo registro de chat: {session_id} - User: {user_id}")
    
    try:
        # Gera título baseado na primeira mensagem do usuário
        user_message = state.get("chatInput", "")
        if not user_message:
            # Se não houver mensagem ainda, usa um título padrão
            title = "Nova Conversa"
        else:
            title = generate_chat_title(llm, user_message)
        
        # Cria o registro no banco
        create_chat_record(session_id, user_id, title)
        logger.info(f"Chat criado com sucesso: {session_id} - Título: {title}")
        
    except Exception as e:
        # Em caso de erro, loga mas não quebra o fluxo
        logger.error(f"Erro ao criar registro de chat: {e}")
        # Continua o fluxo mesmo com erro na criação do chat
    
    return {}


def summarize_node(state: GraphState, llm) -> dict:
    """
    Controla a memória: se houver mais de 10 mensagens da IA, 
    gera um resumo e limpa o histórico.
    
    Regra Crítica: Conta apenas mensagens do tipo AIMessage.
    Gatilho: Se count(AIMessage) > 10, dispara a sumarização.
    """
    session_id = state.get("sessionId")
    user_id = state.get("userId", "N/A")
    logger.info(f"Node: summarize_node - Session: {session_id} - User: {user_id}")
    
    # Pula sumarização para follow-ups
    if state.get("isFollowUp", False):
        logger.debug("Pulando sumarização para follow-up")
        return {}
    
    messages = state.get("messages", [])
    
    # Log: Mensagens carregadas do estado (ANTES do filtro)
    logger.info(f"[SUMMARIZE_NODE] Mensagens carregadas do estado (ANTES do filtro): {len(messages)} mensagens")
    for idx, msg in enumerate(messages):
        msg_type = type(msg).__name__
        msg_id = getattr(msg, 'id', 'N/A')
        content_preview = str(getattr(msg, 'content', 'N/A'))[:100] if hasattr(msg, 'content') else 'N/A'
        logger.info(f"  [{idx}] Tipo: {msg_type} | ID: {msg_id} | Content: {content_preview}...")
    
    # Filtra RemoveMessage e outros tipos não suportados antes de processar
    # RemoveMessage não pode ser passado para o LLM
    # Também filtra mensagens inválidas ou sem conteúdo
    valid_messages = []
    for m in messages:
        # Ignora RemoveMessage
        if isinstance(m, RemoveMessage):
            continue
        # Aceita apenas tipos válidos de mensagem
        if not isinstance(m, (HumanMessage, AIMessage, SystemMessage, ToolMessage)):
            continue
        # Verifica se tem atributo content (todas as mensagens válidas têm)
        if not hasattr(m, 'content'):
            continue
        # Para ToolMessage, content pode ser vazio, mas ainda é válido
        # Para outros tipos (HumanMessage, AIMessage, SystemMessage), content não deve estar vazio
        if isinstance(m, ToolMessage):
            valid_messages.append(m)
        elif m.content:  # HumanMessage, AIMessage, SystemMessage devem ter conteúdo
            valid_messages.append(m)
    
    # Log: Mensagens após o filtro inicial
    logger.info(f"[SUMMARIZE_NODE] Mensagens após filtro inicial (válidas): {len(valid_messages)} mensagens")
    for idx, msg in enumerate(valid_messages):
        msg_type = type(msg).__name__
        msg_id = getattr(msg, 'id', 'N/A')
        content_preview = str(getattr(msg, 'content', 'N/A'))[:100] if hasattr(msg, 'content') else 'N/A'
        logger.info(f"  [{idx}] Tipo: {msg_type} | ID: {msg_id} | Content: {content_preview}...")
    
    # Conta apenas mensagens do tipo AIMessage
    ai_messages = [m for m in valid_messages if isinstance(m, AIMessage)]
    ai_count = len(ai_messages)
    
    logger.debug(f"Contagem de mensagens AI: {ai_count}")
    
    # Critério: Mais de 10 mensagens da IA
    if ai_count <= 10:
        logger.debug(f"Contagem de AI ({ai_count}) <= 10, não é necessário sumarizar")
        return {}
    
    logger.info(f"Disparando sumarização: {ai_count} mensagens AI encontradas")
    
    # Recupera resumo anterior do banco de dados
    existing_summary = get_chat_summary_from_db(session_id)
    
    # Prepara o prompt de sumarização
    if existing_summary:
        summary_prompt = (
            f"Este é o resumo atual da conversa: {existing_summary}\n\n"
            "Estenda o resumo acima integrando as novas mensagens abaixo. "
            "Mantenha as informações importantes do resumo anterior e adicione os novos detalhes relevantes.\n\n"
            "**IMPORTANTE: O resumo DEVE SEMPRE ser gerado em Português Brasileiro (PT-BR), independentemente do idioma da conversa.**"
        )
    else:
        summary_prompt = (
            "Crie um resumo conciso da conversa abaixo para ser usado como contexto futuro. "
            "Inclua os principais pontos, decisões tomadas e informações relevantes.\n\n"
            "**IMPORTANTE: O resumo DEVE SEMPRE ser gerado em Português Brasileiro (PT-BR), independentemente do idioma da conversa.**"
        )
    
    # Remove ToolMessages órfãos antes de passar para o LLM de sumarização
    # Isso evita erros como "No tool call found for function call output"
    tool_call_ids_in_valid_messages = set()
    for msg in valid_messages:
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if hasattr(tool_call, 'id'):
                    tool_call_ids_in_valid_messages.add(tool_call.id)
    
    # Filtra ToolMessages que não têm um tool_call_id correspondente
    valid_messages_for_summary = [
        m for m in valid_messages
        if not isinstance(m, ToolMessage) 
        or (hasattr(m, 'tool_call_id') and m.tool_call_id in tool_call_ids_in_valid_messages)
    ]
    
    # Log: Mensagens após filtro de ToolMessages órfãos
    logger.info(f"[SUMMARIZE_NODE] Mensagens após filtro de ToolMessages órfãos: {len(valid_messages_for_summary)} mensagens")
    for idx, msg in enumerate(valid_messages_for_summary):
        msg_type = type(msg).__name__
        msg_id = getattr(msg, 'id', 'N/A')
        content_preview = str(getattr(msg, 'content', 'N/A'))[:100] if hasattr(msg, 'content') else 'N/A'
        logger.info(f"  [{idx}] Tipo: {msg_type} | ID: {msg_id} | Content: {content_preview}...")
    
    # Prepara mensagens para o LLM de sumarização
    # Usa apenas mensagens válidas (sem RemoveMessage e sem ToolMessages órfãos)
    # Incluímos o histórico e o comando de sumarização
    messages_for_summary = valid_messages_for_summary + [HumanMessage(content=summary_prompt)]
    
    logger.info(f"Chamando LLM para gerar resumo - Session: {session_id} - User: {user_id}")
    # Chamada ao modelo para gerar o resumo
    try:
        response = llm.invoke(messages_for_summary)
        new_summary = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.error(f"Erro ao chamar LLM para sumarização - Session: {session_id} - User: {user_id} - Erro: {str(e)}")
        # Em caso de erro, retorna o estado com mensagem de erro (não gera resumo)
        error_message = get_error_message_from_exception(e)
        return {
            "response": error_message,
            "summary": state.get("summary", ""),  # Mantém resumo anterior
        }
    
    logger.info(f"Resumo gerado com sucesso ({len(new_summary)} caracteres) - Session: {session_id} - User: {user_id}")
    
    # Criar lista de mensagens para remover (todas menos as 2 últimas para manter fluidez)
    # CRÍTICO: Precisamos garantir que ToolMessage não fiquem órfãos
    # Se removemos um AIMessage com tool_calls, devemos remover também os ToolMessage correspondentes
    messages_to_keep = 2
    if len(valid_messages) > messages_to_keep:
        messages_to_remove = valid_messages[:-messages_to_keep]
        
        # Coleta IDs de tool_calls de AIMessages que serão removidos
        tool_call_ids_to_remove = set()
        for msg in messages_to_remove:
            if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if hasattr(tool_call, 'id'):
                        tool_call_ids_to_remove.add(tool_call.id)
        
        # Adiciona RemoveMessage para mensagens a serem removidas
        delete_messages = [RemoveMessage(id=m.id) for m in messages_to_remove]
        
        # Adiciona RemoveMessage para ToolMessage órfãos (cujos tool_call_ids estão sendo removidos)
        # Verifica em todas as mensagens válidas, não apenas nas que serão removidas
        messages_to_remove_ids = {m.id for m in messages_to_remove}
        for msg in valid_messages:
            if isinstance(msg, ToolMessage) and hasattr(msg, 'tool_call_id'):
                if msg.tool_call_id in tool_call_ids_to_remove:
                    # Só adiciona se a mensagem ainda não está na lista de remoção
                    if msg.id not in messages_to_remove_ids:
                        delete_messages.append(RemoveMessage(id=msg.id))
                        messages_to_remove_ids.add(msg.id)  # Evita duplicatas
        
        logger.info(f"Removendo {len(delete_messages)} mensagens antigas (incluindo ToolMessages associados), mantendo {messages_to_keep} mais recentes")
    else:
        delete_messages = []
        logger.debug("Não há mensagens suficientes para remover")
    
    return {
        "summary": new_summary,
        "messages": delete_messages
    }


def agent_node(state: GraphState, llm) -> dict:
    """Executa o agente utilizando a memória carregada pelo checkpointer."""
    session_id = state.get("sessionId")
    user_id = state.get("userId", "N/A")
    logger.info(f"Node: agent_node (start) - Session: {session_id} - User: {user_id}")

    # Renderiza o system_prompt com o resumo e informações do paciente
    existing_summary = state.get("summary", "")
    if existing_summary:
        logger.info(f"Resumo histórico disponível ({len(existing_summary)} caracteres) - será renderizado no system_prompt")

    patient_info = state.get("patientInfo") or {}
    system_prompt = load_prompt("agent.jinja2").render(
        chat_summary=existing_summary,
        patient_sexo=patient_info.get("sexo") or "",
        patient_idade=patient_info.get("idade"),
        patient_alergias=patient_info.get("alergias") or [],
        patient_remedios=patient_info.get("remedios") or [],
    )
    
    messages_from_state = state.get("messages", [])
    
    # Log: Mensagens carregadas do estado (ANTES do filtro)
    logger.info(f"[AGENT_NODE] Mensagens carregadas do estado (ANTES do filtro): {len(messages_from_state)} mensagens")
    for idx, msg in enumerate(messages_from_state):
        msg_type = type(msg).__name__
        msg_id = getattr(msg, 'id', 'N/A')
        content_preview = str(getattr(msg, 'content', 'N/A'))[:100] if hasattr(msg, 'content') else 'N/A'
        logger.info(f"  [{idx}] Tipo: {msg_type} | ID: {msg_id} | Content: {content_preview}...")
    
    # Filtra RemoveMessage antes de processar
    # RemoveMessage não pode ser passado para trim_messages ou LLM
    # Também filtra mensagens inválidas ou sem conteúdo
    current_messages = []
    for m in messages_from_state:
        # Ignora RemoveMessage
        if isinstance(m, RemoveMessage):
            continue
        # Aceita apenas tipos válidos de mensagem
        if not isinstance(m, (HumanMessage, AIMessage, SystemMessage, ToolMessage)):
            continue
        # Verifica se tem atributo content (todas as mensagens válidas têm)
        if not hasattr(m, 'content'):
            continue
        # Para ToolMessage, content pode ser vazio, mas ainda é válido
        # Para outros tipos (HumanMessage, AIMessage, SystemMessage), content não deve estar vazio
        if isinstance(m, ToolMessage):
            current_messages.append(m)
        elif m.content:  # HumanMessage, AIMessage, SystemMessage devem ter conteúdo
            current_messages.append(m)
    
    # Log: Mensagens após filtro inicial
    logger.info(f"[AGENT_NODE] Mensagens após filtro inicial (válidas): {len(current_messages)} mensagens")
    for idx, msg in enumerate(current_messages):
        msg_type = type(msg).__name__
        msg_id = getattr(msg, 'id', 'N/A')
        content_preview = str(getattr(msg, 'content', 'N/A'))[:100] if hasattr(msg, 'content') else 'N/A'
        logger.info(f"  [{idx}] Tipo: {msg_type} | ID: {msg_id} | Content: {content_preview}...")
    
    # Remove ToolMessages órfãos (sem AIMessage correspondente com tool_call)
    # Isso evita erros como "No tool call found for function call output"
    tool_call_ids_in_history = set()
    for msg in current_messages:
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if hasattr(tool_call, 'id'):
                    tool_call_ids_in_history.add(tool_call.id)
    
    # Filtra ToolMessages que não têm um tool_call_id correspondente
    current_messages = [
        m for m in current_messages
        if not isinstance(m, ToolMessage) 
        or (hasattr(m, 'tool_call_id') and m.tool_call_id in tool_call_ids_in_history)
    ]
    
    # Log: Mensagens após filtro de ToolMessages órfãos
    logger.info(f"[AGENT_NODE] Mensagens após filtro de ToolMessages órfãos: {len(current_messages)} mensagens")
    for idx, msg in enumerate(current_messages):
        msg_type = type(msg).__name__
        msg_id = getattr(msg, 'id', 'N/A')
        content_preview = str(getattr(msg, 'content', 'N/A'))[:100] if hasattr(msg, 'content') else 'N/A'
        logger.info(f"  [{idx}] Tipo: {msg_type} | ID: {msg_id} | Content: {content_preview}...")
    
    new_messages_to_add = []

    if state.get("chatInput") and not state.get("isFollowUp"):
        if not current_messages or (hasattr(current_messages[-1], 'content') and current_messages[-1].content != state["chatInput"]):
            logger.debug(f"Adicionando nova mensagem do usuário ao estado: {state['chatInput'][:50]}...")
            human_msg = HumanMessage(content=state["chatInput"])
            current_messages.append(human_msg)
            new_messages_to_add.append(human_msg)

    logger.debug(f"Trimming mensagens. Total antes: {len(current_messages)}")
    trimmed_messages = trim_messages(
        current_messages,
        max_tokens=20000,
        token_counter=count_tokens_approximately,
        strategy="last",
        include_system=False,
    )
    logger.debug(f"Total após trim: {len(trimmed_messages)}")
    
    # O system_prompt já contém o resumo renderizado pelo template
    # Não é necessário adicionar um SystemMessage extra
    messages_for_agent = trimmed_messages

    # IDs das mensagens passadas ao agente (para calcular delta de forma confiável)
    ids_before = {id(m) for m in messages_for_agent}

    agent_executor = create_agent(
        model=llm,
        tools=[document_search_with_urls],
        system_prompt=system_prompt
    )
    logger.info(f"Invocando agente - Session: {session_id} - User: {user_id}")
    try:
        result = agent_executor.invoke({"messages": messages_for_agent})
    except Exception as e:
        logger.error(f"Erro ao invocar agente - Session: {session_id} - User: {user_id} - Erro: {str(e)}")
        # Em caso de erro, retorna o estado com mensagem de erro
        error_message = get_error_message_from_exception(e)
        return {
            "error": True,
            "errorException": str(e),
            "errorMessage": error_message,
            "messages": new_messages_to_add,  # Mantém mensagens já adicionadas
        }

    messages_after_invoke = result["messages"]
    # Delta: mensagens retornadas pelo agente que NÃO estavam no input.
    # Usa id() pois o executor pode re-incluir as mensagens de entrada; só as novas têm IDs diferentes.
    agent_new_messages = [m for m in messages_after_invoke if id(m) not in ids_before]
    new_messages_to_add.extend(agent_new_messages)
    logger.info(f"Agente finalizado. Novas mensagens: {len(agent_new_messages)}")

    tool_contents = []
    for msg in agent_new_messages:
        if isinstance(msg, ToolMessage) and getattr(msg, "content", None):
            tool_contents.append(msg.content)
    last_source_documents = "\n---\n".join(tool_contents) if tool_contents else ""
    if last_source_documents:
        logger.debug(f"Documentos RAG encontrados: {len(tool_contents)}")

    # Resposta = conteúdo da última AIMessage com texto (evita usar ToolMessage ou AIMessage vazia)
    # Gemini pode retornar content como lista de blocos; _content_to_string normaliza
    response_content = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            raw = getattr(msg, "content", None)
            response_content = _content_to_string(raw)
            if response_content.strip():
                break
    if not response_content.strip():
        logger.warning("Nenhuma AIMessage com conteúdo encontrada no resultado do agente; response vazio.")

    return {
        "lastSourceDocuments": last_source_documents,
        "response": response_content,
        "messages": new_messages_to_add,
        "error": False,
        "errorMessage": "",
        "errorException": "",
    }


def generate_followup_node(state: GraphState, llm) -> dict:
    """Gera perguntas de follow-up baseadas na resposta do agente."""
    session_id = state.get("sessionId")
    user_id = state.get("userId", "N/A")
    logger.info(f"Node: generate_followup_node - Session: {session_id} - User: {user_id}")

    user_message = state.get("chatInput", "")
    agent_message = state.get("response", "")
    source_documents = state.get("lastSourceDocuments", "")

    follow_up_questions = (
        generate_follow_up_questions(
                            llm=llm,
                            last_agent_message=agent_message,
                            last_user_message=user_message,
                            source_documents=source_documents,
        )
    )       
    logger.info(f"Follow-ups gerados: {len(follow_up_questions)}")
    
    return {"followUpQuestions": follow_up_questions}

def check_error_node(state: GraphState) -> dict:
    """
    Verifica se ocorreu um erro no estado.
    
    Este node apenas verifica e passa o estado adiante.
    O roteamento condicional (route_by_error) decide para qual node ir.
    Não altera estado; retorna {} para não acionar reducers.
    """
    session_id = state.get("sessionId")
    user_id = state.get("userId", "N/A")
    logger.info(f"Node: check_error_node - Session: {session_id} - User: {user_id}")
    
    has_error = state.get("error", False)
    if has_error:
        logger.warning(f"Erro detectado no estado - Session: {session_id} - User: {user_id} - Error: {state.get('errorMessage', 'Unknown')}")
    else:
        logger.debug(f"Nenhum erro detectado - Session: {session_id} - User: {user_id}")
    
    return {}


def route_by_error(state: GraphState) -> str:
    """
    Função de roteamento: retorna o nome do próximo nó baseado na presença de erro.
    
    Returns:
        "return_error_node" se houver erro, "return_response_node" caso contrário
    """
    has_error = state.get("error", False)
    route = "return_error_node" if has_error else "return_response_node"
    session_id = state.get("sessionId", "unknown")
    user_id = state.get("userId", "N/A")
    logger.info(f"Roteamento: error={has_error} -> Indo para: {route} - Session: {session_id} - User: {user_id}")
    return route

def return_response_node(state: GraphState) -> dict:
    """Retorna o estado com a resposta (sem erros)."""
    session_id = state.get("sessionId")
    user_id = state.get("userId", "N/A")
    logger.info(f"Node: return_response_node - Session: {session_id} - User: {user_id}")
    
    # Preserva todo o estado, mas garante que error está False
    return {
        "error": False,
        "errorMessage": "",
        "errorException": "",
        "response": state.get("response", ""),
        "followUpQuestions": state.get("followUpQuestions", [])
    }

def return_error_node(state: GraphState) -> dict:
    """Retorna o estado com o erro. Notificação ao Slack opcional (ENABLE_SLACK_ERROR_NOTIFICATIONS)."""
    session_id = state.get("sessionId")
    user_id = state.get("userId", "N/A")
    logger.info(f"Node: return_error_node - Session: {session_id} - User: {user_id}")
    
    error_message = state.get("errorMessage", "")
    error_exception = state.get("errorException", "")
    
    logger.error(f"Erro: {error_message} - Exception: {error_exception} - Session: {session_id} - User: {user_id}")
    
    # Envio ao Slack desativado; ative ENABLE_SLACK_ERROR_NOTIFICATIONS para reativar.
    if ENABLE_SLACK_ERROR_NOTIFICATIONS:
        try:
            #send_message(error_exception)
            pass
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para Slack: {str(e)}")
    
    # Preserva todo o estado, mas garante que error está True e response contém a mensagem de erro
    return {
        "error": True,
        "errorMessage": error_message,
        "errorException": error_exception,
        "response": error_message,
        "followUpQuestions": []  # Não gera follow-ups em caso de erro
    }

def logger_node(state: GraphState) -> dict:
    """Nó final para gravar a interação na tabela chat_history. Não altera estado; retorna {}."""
    session_id = state["sessionId"]
    user_id = state.get("userId", "N/A")
    logger.info(f"Node: logger_node (DB persist) - Session: {session_id} - User: {user_id}")
    
    # Verifica se existe resumo para salvar
    summary = state.get("summary", "")
    has_summary = bool(summary)
    
    # Salva o resumo na tabela chat_summaries se existir
    if has_summary:
        logger.debug(f"Salvando resumo na tabela chat_summaries para sessão: {session_id} - User: {user_id}")
        save_chat_summary_to_db(session_id, summary)
    
    # 1. Persistir Mensagem Humana (Input do Chat)
    if state.get("chatInput") and not state.get("isFollowUp"):
        logger.debug(f"Persistindo mensagem do usuário no DB para sessão: {session_id} - User: {user_id}")
        human_msg = HumanMessage(content=state["chatInput"])
        save_message_to_db(session_id, human_msg, has_summary=has_summary)
    
    ## 2. Persistir Mensagem da IA (Resposta + Follow-ups)
    #if state.get("response"):
    #    response_text = state["response"]
    #    
    #    # Formata os follow-ups como parte do conteúdo da mensagem da IA
    #    follow_ups = state.get("followUpQuestions", {}).get("follow_ups", [])
    #    if follow_ups:
    #        questions_formatted = "\n\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(follow_ups)])
    #        response_text += questions_formatted
    #    
    #    logger.debug(f"Persistindo resposta da IA no DB para sessão: {session_id}")
    #    ai_msg = AIMessage(
    #        content=response_text,
    #        tool_calls=[],
    #        additional_kwargs={},
    #        response_metadata={}
    #    )
#
    #    save_message_to_db(session_id, ai_msg, has_summary=has_summary)
    
    return {}


#def route_by_follow_up(state: GraphState) -> str:
#    """Função de roteamento: retorna o nome do próximo nó (agente ou LLM de follow-up)."""
#    is_follow_up = state.get("isFollowUp", False)
#    route = "run_follow_up_llm" if is_follow_up else "run_agent"
#    logger.info(f"Roteamento: isFollowUp={is_follow_up} -> Indo para: {route}")
#    return route
#
#
#def follow_up_llm_node(state: GraphState, llm) -> GraphState:
#    """Invoca o LLM diretamente para follow-up (sem agente, sem tools)."""
#    session_id = state.get("sessionId")
#    logger.info(f"Node: follow_up_llm_node - Session: {session_id}")
#    system_prompt = load_prompt("follow_up.jinja2").render(
#        last_agent_message=state.get("lastAgentMessage", ""),
#        user_message=state.get("lastUserMessage", ""),
#        source_documents=state.get("lastSourceDocuments", ""),
#    )
#    user_content = state.get("chatInput", "").strip() or state.get("lastUserMessage", "")
#    messages = [
#        SystemMessage(content=system_prompt),
#        HumanMessage(content=user_content),
#    ]
#    response = llm.invoke(messages)
#    content = response.content if hasattr(response, "content") else str(response)
#    return {**state, "response": content}