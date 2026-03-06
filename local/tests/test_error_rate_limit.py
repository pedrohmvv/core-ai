"""
Script para testar o tratamento de erros RateLimit.

Este script envia múltiplas requisições rápidas para tentar forçar um rate limit.
Os erros devem aparecer como mensagens no chat, não como exceções HTTP.

Uso:
    python local_tests/test_error_rate_limit.py
    python local_tests/test_error_rate_limit.py --count 20 --delay 0.1
"""
import sys
import time
import threading
from pathlib import Path
from typing import List, Dict
import uuid

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()

API_URL = "http://localhost:8000/api/v1/chat"

# Mensagem esperada para RateLimit
RATE_LIMIT_MESSAGE = (
    "We detected a high volume of messages in a short period of time. "
    "To ensure stability, please wait around 1 minute before continuing."
)


def send_request(chat_input: str, session_id: str, user_id: str, result_list: List[Dict], index: int):
    """
    Envia uma requisição e armazena o resultado.
    
    Args:
        chat_input: Mensagem do usuário
        session_id: ID da sessão
        user_id: ID do usuário
        result_list: Lista para armazenar resultados
        index: Índice da requisição
    """
    try:
        start_time = time.time()
        response = requests.post(
            API_URL,
            json={"chat_input": f"{chat_input} (Request #{index})", "session_id": session_id, "user_id": user_id, "metadata": {}},
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        elapsed = time.time() - start_time
        
        result = {
            "index": index,
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else None,
            "elapsed": elapsed,
            "success": response.status_code == 200
        }
        
        if response.status_code == 200:
            response_text = result["response"].get("response", "")
            result["has_rate_limit_message"] = RATE_LIMIT_MESSAGE in response_text
            result["has_bad_request_message"] = "currently experiencing an issue with the model" in response_text
        
        result_list.append(result)
        
    except Exception as e:
        result_list.append({
            "index": index,
            "status_code": None,
            "response": None,
            "elapsed": 0,
            "success": False,
            "error": str(e)
        })


def test_rate_limit(
    chat_input: str = "Hello, how are you?",
    count: int = 10,
    delay: float = 0.1,
    session_id: str = None,
    user_id: str = "test-user-rate-limit",
    parallel: bool = True
) -> Dict:
    """
    Testa rate limit enviando múltiplas requisições.
    
    Args:
        chat_input: Mensagem do usuário
        count: Número de requisições para enviar
        delay: Delay entre requisições (em segundos)
        session_id: ID da sessão (gerado automaticamente se não fornecido)
        user_id: ID do usuário
        parallel: Se True, envia requisições em paralelo; se False, sequencialmente
        
    Returns:
        Dicionário com resultados dos testes
    """
    if not session_id:
        session_id = str(uuid.uuid4())
    
    print(f"\n{'='*70}")
    print(f"🧪 TESTE: RateLimit Error Handling")
    print(f"{'='*70}")
    print(f"📤 Mensagem: {chat_input}")
    print(f"🆔 Session: {session_id} - User: {user_id}")
    print(f"📊 Número de requisições: {count}")
    print(f"⏱️  Delay entre requisições: {delay}s")
    print(f"🔄 Modo: {'Paralelo' if parallel else 'Sequencial'}")
    print(f"⏰ Início: {time.strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")
    
    results = []
    start_time = time.time()
    
    if parallel:
        # Envia requisições em paralelo usando threads
        threads = []
        for i in range(count):
            thread = threading.Thread(
                target=send_request,
                args=(chat_input, session_id, user_id, results, i + 1)
            )
            threads.append(thread)
            thread.start()
            if delay > 0:
                time.sleep(delay)
        
        # Aguarda todas as threads terminarem
        for thread in threads:
            thread.join()
    else:
        # Envia requisições sequencialmente
        for i in range(count):
            send_request(chat_input, session_id, user_id, results, i + 1)
            if i < count - 1 and delay > 0:
                time.sleep(delay)
    
    total_time = time.time() - start_time
    
    # Ordena resultados por índice
    results.sort(key=lambda x: x.get("index", 0))
    
    # Análise dos resultados
    successful = sum(1 for r in results if r.get("success", False))
    rate_limit_detected = sum(1 for r in results if r.get("has_rate_limit_message", False))
    bad_request_detected = sum(1 for r in results if r.get("has_bad_request_message", False))
    
    print(f"\n{'='*70}")
    print(f"📊 RESULTADOS")
    print(f"{'='*70}")
    print(f"⏱️  Tempo total: {total_time:.2f}s")
    print(f"✅ Requisições bem-sucedidas (HTTP 200): {successful}/{count}")
    print(f"🚦 RateLimit detectado: {rate_limit_detected}/{count}")
    print(f"⚠️  BadRequest detectado: {bad_request_detected}/{count}")
    print(f"{'='*70}\n")
    
    # Exibe detalhes das requisições
    print(f"{'─'*70}")
    print(f"📋 DETALHES DAS REQUISIÇÕES")
    print(f"{'─'*70}")
    for result in results:
        status = "✅" if result.get("success") else "❌"
        index = result.get("index", "?")
        status_code = result.get("status_code")
        status_code_str = str(status_code) if status_code is not None else "N/A"
        elapsed = result.get("elapsed", 0)
        
        print(f"{status} Request #{index:2d}: Status {status_code_str:>3s} | Tempo: {elapsed:.2f}s", end="")
        
        if result.get("has_rate_limit_message"):
            print(" | 🚦 RateLimit detectado!")
        elif result.get("has_bad_request_message"):
            print(" | ⚠️  BadRequest detectado!")
        elif result.get("success"):
            print(" | ✅ Sucesso")
        else:
            error = result.get("error", "Erro desconhecido")
            print(f" | ❌ Erro: {error}")
    
    print(f"{'─'*70}\n")
    
    # Verifica se rate limit foi detectado corretamente
    test_passed = False
    if rate_limit_detected > 0:
        print(f"✅ SUCESSO: RateLimit foi detectado em {rate_limit_detected} requisição(ões)!")
        print(f"   A mensagem de erro foi retornada como parte da resposta do chat (HTTP 200).")
        test_passed = True
    elif successful == count:
        print(f"⚠️  ATENÇÃO: Todas as requisições foram bem-sucedidas.")
        print(f"   Isso pode significar que:")
        print(f"   - O rate limit não foi atingido (tente aumentar o número de requisições)")
        print(f"   - O sistema está lidando bem com a carga")
        print(f"   - O delay entre requisições é muito alto")
    else:
        print(f"⚠️  ATENÇÃO: Algumas requisições falharam, mas RateLimit não foi detectado.")
        print(f"   Verifique os erros acima.")
    
    return {
        "total": count,
        "successful": successful,
        "rate_limit_detected": rate_limit_detected,
        "bad_request_detected": bad_request_detected,
        "total_time": total_time,
        "test_passed": test_passed,
        "results": results
    }


def main():
    """Executa os testes de RateLimit."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Testa o tratamento de erros RateLimit"
    )
    parser.add_argument(
        "--message", "-m",
        type=str,
        default="Hello, how are you?",
        help="Mensagem para enviar ao chat"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=10,
        help="Número de requisições para enviar (padrão: 10)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0.1,
        help="Delay entre requisições em segundos (padrão: 0.1)"
    )
    parser.add_argument(
        "--session-id", "-s",
        type=str,
        default=None,
        help="ID da sessão (gerado automaticamente se não fornecido)"
    )
    parser.add_argument(
        "--sequential", "-seq",
        action="store_true",
        help="Envia requisições sequencialmente ao invés de em paralelo"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🧪 TESTE DE ERRO RATE LIMIT")
    print("="*70)
    print("\nEste teste envia múltiplas requisições rápidas para tentar forçar")
    print("um rate limit e verifica se o erro é tratado corretamente.")
    print("\n💡 DICA: Para aumentar a chance de rate limit:")
    print("   - Aumente o número de requisições: --count 20")
    print("   - Reduza o delay: --delay 0.05")
    print("   - Use modo paralelo (padrão)")
    print("="*70)
    
    result = test_rate_limit(
        chat_input=args.message,
        count=args.count,
        delay=args.delay,
        session_id=args.session_id,
        user_id="test-user-rate-limit",
        parallel=not args.sequential
    )
    
    # Resumo final
    print("\n" + "="*70)
    print("📊 RESUMO FINAL")
    print("="*70)
    if result["test_passed"]:
        print("🎉 TESTE PASSOU: RateLimit foi detectado e tratado corretamente!")
    else:
        print("⚠️  TESTE NÃO CONCLUÍDO: RateLimit não foi detectado.")
        print("   Tente aumentar o número de requisições ou reduzir o delay.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

