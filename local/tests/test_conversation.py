"""
Script para conversar com o agente mantendo memória na mesma sessão.

Uso:
    python local_tests/conversa.py
    python local_tests/conversa.py --session-id minha-sessao

O mesmo session_id mantém o histórico (checkpointer).
"""
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

API_URL = "http://localhost:8000/api/v1/chat"


def chat(chat_input: str, session_id: str, user_id: str = "test-user-conversation") -> dict:
    """Envia mensagem e retorna a resposta."""
    try:
        r = requests.post(
            API_URL,
            json={"chat_input": chat_input, "session_id": session_id, "user_id": user_id, "metadata": {}},
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        print("❌ Servidor não está rodando. Inicie com: python -m src.main --env local")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro: {e}")
        return {}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Conversa com o agente (memória por sessão)")
    parser.add_argument("--session-id", "-s", default=None, help="ID da sessão (default: gera UUID)")
    parser.add_argument("--user-id", "-u", default="test-user-conversation", help="ID do usuário")
    parser.add_argument("--message", "-m", default=None, help="Enviar uma mensagem e sair")
    args = parser.parse_args()

    import uuid
    session_id = args.session_id or str(uuid.uuid4())
    user_id = args.user_id

    if args.message:
        # Modo single-shot
        result = chat(args.message, session_id, user_id)
        if result:
            print(result.get("response", ""))
            # Exibe follow-up questions se disponíveis
            follow_up_data = result.get("followUpQuestions", {})
            follow_ups = follow_up_data.get("follow_ups", []) if isinstance(follow_up_data, dict) else []
            if follow_ups:
                print("\n💡 Perguntas de follow-up:")
                for i, q in enumerate(follow_ups, 1):
                    print(f"   {i}. {q}")
        return

    # Modo interativo
    print(f"\n💬 Conversa com o agente | Session: {session_id} - User: {user_id}")
    print("   Digite 'sair' ou 'quit' para encerrar.\n")

    while True:
        try:
            user_input = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("sair", "quit", "exit"):
            print("Até logo!")
            break

        result = chat(user_input, session_id, user_id)
        if not result:
            continue

        # Exibe a resposta principal
        response = result.get('response', '')
        print(f"\n🤖 {response}")
        
        # Exibe follow-up questions se disponíveis
        follow_up_data = result.get("followUpQuestions", {})
        follow_ups = follow_up_data.get("follow_ups", []) if isinstance(follow_up_data, dict) else []
        if follow_ups:
            print("\n💡 Perguntas de follow-up:")
            for i, q in enumerate(follow_ups, 1):
                print(f"   {i}. {q}")
        
        print()  # Linha em branco para separar


if __name__ == "__main__":
    main()
