"""
Script para testar o tratamento de erros BadRequest do modelo.

Este script testa como o sistema responde quando há erros no modelo LLM.
Os erros devem aparecer como mensagens no chat, não como exceções HTTP.

Uso:
    python local_tests/test_error_bad_request.py
    
Nota: Para forçar um erro BadRequest, você pode:
1. Desligar temporariamente o servidor do LLM
2. Usar uma API key inválida
3. Usar um endpoint inválido
4. Aguardar que ocorra naturalmente um erro do modelo
"""
import sys
import time
from pathlib import Path
import uuid

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

API_URL = "http://localhost:8000/api/v1/chat"

# Mensagem esperada para BadRequest
BAD_REQUEST_MESSAGE = (
    "We apologize for the inconvenience, but we're currently experiencing "
    "an issue with the model. Our engineering team is already on the case "
    "and working to resolve it as quickly as possible."
)


def test_bad_request_error(chat_input: str, session_id: str = None, user_id: str = "test-user-bad-request") -> bool:
    """
    Testa se o erro BadRequest é tratado corretamente.
    
    Args:
        chat_input: Mensagem do usuário
        session_id: ID da sessão (gerado automaticamente se não fornecido)
        user_id: ID do usuário
        
    Returns:
        True se o teste passou, False caso contrário
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    
    print(f"\n{'='*70}")
    print(f"🧪 TESTE: BadRequest Error Handling")
    print(f"{'='*70}")
    print(f"📤 Enviando: {chat_input}")
    print(f"🆔 Session: {session_id} - User: {user_id}")
    print(f"⏰ Horário: {time.strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")
    
    try:
        response = requests.post(
            API_URL,
            json={"chat_input": chat_input, "session_id": session_id, "user_id": user_id, "metadata": {}},
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        
        print(f"📥 Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "")
            
            print(f"✅ Resposta recebida (HTTP 200)")
            print(f"\n{'─'*70}")
            print(f"🤖 MENSAGEM DO CHAT:")
            print(f"{'─'*70}")
            print(response_text)
            print(f"{'─'*70}\n")
            
            # Verifica se a mensagem de erro BadRequest está presente
            if BAD_REQUEST_MESSAGE in response_text:
                print(f"✅ SUCESSO: Mensagem de erro BadRequest detectada corretamente!")
                print(f"   A mensagem de erro foi retornada como parte da resposta do chat.")
                return True
            else:
                print(f"⚠️  ATENÇÃO: Resposta recebida, mas não contém mensagem de erro BadRequest.")
                print(f"   Isso pode significar que:")
                print(f"   - O modelo funcionou corretamente (não houve erro)")
                print(f"   - Ou o erro foi tratado de forma diferente")
                print(f"\n   Mensagem esperada (parcial):")
                print(f"   '{BAD_REQUEST_MESSAGE[:50]}...'")
                return False
        else:
            print(f"❌ ERRO: Status code {response.status_code}")
            print(f"   Resposta: {response.text}")
            print(f"\n   ⚠️  O erro foi retornado como HTTP error, não como mensagem no chat.")
            print(f"   Isso não está de acordo com o comportamento esperado.")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ ERRO: Servidor não está rodando.")
        print(f"   Inicie com: python -m src.main --env local")
        return False
    except Exception as e:
        print(f"❌ ERRO INESPERADO: {str(e)}")
        return False


def main():
    """Executa os testes de BadRequest."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Testa o tratamento de erros BadRequest do modelo"
    )
    parser.add_argument(
        "--message", "-m",
        type=str,
        default="What is Sileto?",
        help="Mensagem para enviar ao chat"
    )
    parser.add_argument(
        "--session-id", "-s",
        type=str,
        default=None,
        help="ID da sessão (gerado automaticamente se não fornecido)"
    )
    parser.add_argument(
        "--multiple", "-n",
        type=int,
        default=1,
        help="Número de requisições para enviar (útil para testar múltiplas vezes)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🧪 TESTE DE ERRO BAD REQUEST")
    print("="*70)
    print("\nEste teste verifica se erros do modelo são tratados corretamente")
    print("e retornados como mensagens no chat (HTTP 200) ao invés de exceções HTTP.")
    print("\n💡 DICA: Para forçar um erro BadRequest:")
    print("   1. Desligue temporariamente o servidor do LLM")
    print("   2. Use uma API key inválida no código")
    print("   3. Use um endpoint inválido")
    print("   4. Aguarde que ocorra naturalmente um erro do modelo")
    print("="*70)
    
    results = []
    for i in range(args.multiple):
        if args.multiple > 1:
            print(f"\n\n🔄 Teste {i+1}/{args.multiple}")
        result = test_bad_request_error(args.message, args.session_id, "test-user-bad-request")
        results.append(result)
        
        if i < args.multiple - 1:
            time.sleep(2)  # Aguarda 2 segundos entre requisições
    
    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO DOS TESTES")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"✅ Testes passados: {passed}/{total}")
    print(f"❌ Testes falhados: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 Todos os testes passaram!")
    elif passed > 0:
        print("\n⚠️  Alguns testes falharam. Verifique os logs acima.")
    else:
        print("\n❌ Nenhum teste passou. Verifique:")
        print("   - Se o servidor está rodando")
        print("   - Se há erros no modelo LLM")
        print("   - Se a mensagem de erro está sendo retornada corretamente")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

