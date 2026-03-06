"""
Serviço LangGraph que encapsula o fluxo completo do agente conversacional.
"""
import asyncio
import logging
from functools import partial
from typing import Annotated, Dict, Any, TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from psycopg_pool import ConnectionPool

from core.config import config
from app.infrastructure.langgraph.tools import set_global_store
from app.infrastructure.vector_store import create_vector_store
from app.infrastructure.langgraph.state import GraphState
from app.infrastructure.langgraph.utils import get_chat_summary_from_db, _content_to_string
from app.infrastructure.langgraph.nodes import (
    #route_by_follow_up,
    create_chat_node,
    summarize_node,
    agent_node,
    #follow_up_llm_node,
    generate_followup_node,
    check_error_node,
    return_error_node,
    return_response_node,
    route_by_error,
    logger_node,
)

logger = logging.getLogger(__name__)

class LangGraphService:
    """Serviço que gerencia o fluxo LangGraph completo."""
    
    def __init__(self):
        self.llm = self._create_llm()
        self._pool = self._create_pool()
        self.checkpointer = self._create_checkpointer()
        self._store = None  # Será inicializado quando necessário
        self.app = None  # Grafo com checkpointer
        self.follow_up_app = None  # Grafo sem checkpointer para evitar persistência de follow-up
    
    async def _ensure_store(self):
        """Garante que as stores estão inicializadas."""
        # Inicializa o vector store (para busca de documentos)
        if self._store is None:
            logger.info("Inicializando Vector Store...")
            self._store = await create_vector_store()
            # Configura a store global para as tools
            set_global_store(self._store)
            logger.info("Vector Store inicializada com sucesso.")
        
        # Cria o grafo se ainda não foi criado
        if self.app is None:
            logger.info("Compilando grafos LangGraph...")
            # Cria as tabelas do checkpointer (checkpoints, checkpoint_blobs, etc.) se não existirem
            self.checkpointer.setup()
            self.app = self._create_graph(with_checkpointer=True)
            self.follow_up_app = self._create_graph(with_checkpointer=False)
            logger.info("Grafos compilados com sucesso.")
    
    def _create_llm(self) -> ChatGoogleGenerativeAI:
        """Cria a instância do LLM (Gemini 2.5 Flash) usando GOOGLE_API_KEY do .env."""
        return ChatGoogleGenerativeAI(
            model=config.GOOGLE_GEMINI_MODEL,
            api_key=config.GOOGLE_API_KEY,
            temperature=0.2,
        )
    
    def _create_pool(self) -> ConnectionPool:
        """Cria o pool de conexões PostgreSQL (usado pelo checkpointer e por consultas de leitura)."""
        def configure(conn):
            conn.autocommit = True
        return ConnectionPool(
            conninfo=config.DB_URI_SYNC,
            max_size=20,
            configure=configure,
        )

    def _create_checkpointer(self) -> PostgresSaver:
        """Cria o checkpointer para persistência de memória."""
        return PostgresSaver(self._pool)
    
    def _create_graph(self, with_checkpointer: bool = True):
        """Cria e compila o grafo LangGraph."""
        workflow = StateGraph(GraphState)
        
        # Nós que recebem llm via partial (LangGraph chama só com state)
        run_create_chat = partial(create_chat_node, llm=self.llm)
        run_summarize = partial(summarize_node, llm=self.llm)
        run_agent = partial(agent_node, llm=self.llm)
        run_follow_up_llm = partial(generate_followup_node, llm=self.llm)

        # Adiciona todos os nós do grafo
        workflow.add_node("create_chat", run_create_chat)
        workflow.add_node("summarize", run_summarize)
        workflow.add_node("run_agent", run_agent)
        workflow.add_node("check_error", check_error_node)
        workflow.add_node("return_error", return_error_node)
        workflow.add_node("return_response", return_response_node)
        workflow.add_node("run_follow_up_llm", run_follow_up_llm)

        # Define o ponto de entrada: START -> create_chat
        workflow.set_entry_point("create_chat")
        
        # Fluxo principal:
        # create_chat -> summarize -> run_agent -> check_error -> (return_error ou return_response) -> run_follow_up_llm -> END
        workflow.add_edge("create_chat", "summarize")
        workflow.add_edge("summarize", "run_agent")
        workflow.add_edge("run_agent", "check_error")
        
        # Roteamento condicional: se houver erro, vai para return_error, senão para return_response
        workflow.add_conditional_edges(
            "check_error",
            route_by_error,
            {
                "return_error_node": "return_error",
                "return_response_node": "return_response"
            }
        )
        
        # Após return_error ou return_response, vai para run_follow_up_llm (apenas se não houver erro)
        # Mas na verdade, se houver erro, não devemos gerar follow-ups
        # Vamos fazer: return_response -> run_follow_up_llm, return_error -> END
        workflow.add_edge("return_response", "run_follow_up_llm")
        workflow.add_edge("return_error", END)
        workflow.add_edge("run_follow_up_llm", END)
        
        #workflow.add_edge("logger_node", END) -> Caso seja melhor salvar em bancos de dados.
        
        if with_checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)
            
        return workflow.compile()
    
    async def invoke(self, chat_input: str, session_id: str, user_id: str, is_follow_up: bool = False) -> Dict[str, Any]:
        """
        Executa o fluxo completo do agente e retorna a resposta e as perguntas de follow-up.
        
        Args:
            chat_input: Mensagem do usuário
            session_id: ID da sessão
            user_id: ID do usuário
            is_follow_up: Se é um follow-up automático
        
        Returns:
            Dicionário com 'response' e 'followUpQuestions'
        """
        logger.info(f"LangGraphService.invoke - Session: {session_id} - User: {user_id} - isFollowUp: {is_follow_up}")
        
        # Garante que a store está inicializada
        await self._ensure_store()
        
        try:

            # Carrega o resumo do banco de dados
            loop = asyncio.get_event_loop()
            existing_summary = await loop.run_in_executor(
                None,
                lambda: get_chat_summary_from_db(session_id)
            )

            # Prepara o estado inicial
            initial_state: GraphState = {
                "chatInput": chat_input,
                "sessionId": session_id,
                "userId": user_id,
                "isFollowUp": is_follow_up,
                "systemPrompt": "",
                "messages": [],  # O checkpointer carregará o histórico automaticamente
                "response": "",
                "followUpQuestions": [],
                "summary": existing_summary,  # Resumo carregado do banco de dados
                "error": False,
                "errorMessage": "",
                "errorException": ""
            }

            logger.info(f"Executando grafo para sessão: {session_id} - User: {user_id}")
            # Executa o invoke síncrono em um thread pool para não bloquear o event loop
            # Isso permite que múltiplas requisições sejam processadas em paralelo
            loop = asyncio.get_event_loop()
            if is_follow_up:
                # Fluxo follow-up sem checkpointer para não persistir no histórico
                final_state = await loop.run_in_executor(
                    None,
                    lambda: self.follow_up_app.invoke(initial_state)
                )
            else:
                thread_config = {"configurable": {"thread_id": session_id, "user_id": user_id}}
                final_state = await loop.run_in_executor(
                    None,
                    lambda: self.app.invoke(initial_state, config=thread_config)
                )
            
            logger.info(f"Grafo finalizado com sucesso - Session: {session_id} - User: {user_id}")
            return {
                "response": final_state.get("response", ""),
                "followUpQuestions": final_state.get("followUpQuestions", [])
            }
        
        except Exception as e:
            logger.error(f"Erro no LangGraphService.invoke - Session: {session_id} - User: {user_id} - Erro: {str(e)}", exc_info=True)
            # Em caso de erro não tratado, retorna mensagem de erro genérica
            from app.chat.application.exception import BadRequestException
            return {
                "response": BadRequestException.message,
                "followUpQuestions": []
            }

    def _get_read_app(self):
        """Grafo mínimo para leitura de checkpoints (mensagens e histórico)."""
        class ReadState(TypedDict):
            messages: Annotated[list[BaseMessage], lambda x, y: x + y]

        def pass_through(state: ReadState) -> ReadState:
            return state

        workflow = StateGraph(ReadState)
        workflow.add_node("node", pass_through)
        workflow.set_entry_point("node")
        workflow.add_edge("node", END)
        return workflow.compile(checkpointer=self.checkpointer)

    def get_all_messages_from_checkpoint(self, session_id: str) -> list[BaseMessage]:
        """Retorna todas as mensagens do checkpoint para uma sessão."""
        try:
            read_app = self._get_read_app()
            thread_config = {"configurable": {"thread_id": session_id}}
            snapshot = read_app.get_state(thread_config)
            values = getattr(snapshot, "values", {}) or {}
            return values.get("messages", [])
        except Exception as e:
            logger.error(f"Erro ao buscar mensagens do checkpoint - Session: {session_id} - Erro: {str(e)}")
            return []

    def get_message_timestamps(self, session_id: str) -> dict[int, str]:
        """Retorna mapeamento índice da mensagem -> timestamp (ISO). Usa get_state_history."""
        timestamp_by_index: dict[int, str] = {}
        prev_len = 0
        try:
            read_app = self._get_read_app()
            thread_config = {"configurable": {"thread_id": session_id}}
            history = list(read_app.get_state_history(thread_config))
        except Exception as e:
            logger.error(f"Erro ao buscar histórico do checkpoint - Session: {session_id} - Erro: {str(e)}")
            return timestamp_by_index
        for snapshot in reversed(history):
            values = getattr(snapshot, "values", {}) or {}
            messages = values.get("messages", [])
            created_at = getattr(snapshot, "created_at", None)
            if created_at is None:
                continue
            ts_str = (
                created_at.isoformat()
                if hasattr(created_at, "isoformat")
                else str(created_at)
            )
            for i in range(prev_len, len(messages)):
                timestamp_by_index[i] = ts_str
            prev_len = len(messages)
        return timestamp_by_index

    def get_session_messages(self, session_id: str) -> list[dict]:
        """Retorna mensagens da sessão formatadas (user/assistant), com role, content e timestamp. Exclui ToolMessage e AIMessage vazios."""
        messages = self.get_all_messages_from_checkpoint(session_id)
        timestamps = self.get_message_timestamps(session_id)
        result: list[dict] = []
        for idx, msg in enumerate(messages):
            if isinstance(msg, ToolMessage):
                continue
            content = ""
            role = ""
            if isinstance(msg, HumanMessage):
                content = getattr(msg, "content", str(msg))
                role = "user"
            elif isinstance(msg, AIMessage):
                content = getattr(msg, "content", None) or ""
                role = "assistant"
            else:
                continue
            # Gemini pode retornar content como lista de blocos; normaliza para string
            content = _content_to_string(content)
            if not content.strip():
                continue
            result.append({
                "role": role,
                "content": content,
                "timestamp": timestamps.get(idx),
            })
        return result

    def get_session_ids_by_user(self, user_id: str) -> list[str]:
        """Retorna session_ids do usuário a partir da metadata do checkpoint."""
        session_ids = []
        try:
            with self._pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT thread_id
                        FROM checkpoints
                        WHERE metadata->>'user_id' = %s
                        ORDER BY thread_id
                        """,
                        (user_id,),
                    )
                    session_ids = [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Erro ao buscar session_ids por usuário - User: {user_id} - Erro: {str(e)}")
        return session_ids

    def get_messages_by_user(self, user_id: str) -> list[dict]:
        """Retorna todas as conversas do usuário (session_id, messages, message_count) filtradas por metadata."""
        filtered_sessions = self.get_session_ids_by_user(user_id)
        user_conversations = []
        for session_id in filtered_sessions:
            try:
                messages = self.get_all_messages_from_checkpoint(session_id)
                timestamps = self.get_message_timestamps(session_id)
                formatted_messages: list[dict] = []
                for idx, msg in enumerate(messages):
                    if isinstance(msg, ToolMessage):
                        continue
                    content = ""
                    role = ""
                    if isinstance(msg, HumanMessage):
                        content = getattr(msg, "content", str(msg))
                        role = "user"
                    elif isinstance(msg, AIMessage):
                        content = getattr(msg, "content", None) or ""
                        if not content.strip():
                            continue
                        role = "assistant"
                    else:
                        continue
                    if not isinstance(content, str):
                        content = str(content)
                    formatted_messages.append({
                        "role": role,
                        "content": content,
                        "timestamp": timestamps.get(idx),
                    })
                if formatted_messages:
                    user_conversations.append({
                        "session_id": session_id,
                        "messages": formatted_messages,
                        "message_count": len(formatted_messages),
                    })
            except Exception as e:
                logger.error(f"Erro ao processar session {session_id}: {e}")
                continue
        return user_conversations

