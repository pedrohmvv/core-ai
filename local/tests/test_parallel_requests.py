"""
Script para testar processamento paralelo de requisições.

Uso:
    python test_parallel_requests.py <IP_DO_SERVIDOR> [num_requests]
    
Exemplo:
    python test_parallel_requests.py 192.168.0.46
    python test_parallel_requests.py 192.168.0.46 5

Dependência:
    pip install aiohttp
"""
import asyncio
import time
import sys
from typing import List

try:
    import aiohttp
except ImportError:
    print("❌ Erro: aiohttp não está instalado")
    print("💡 Instale com: pip install aiohttp")
    sys.exit(1)


async def send_request(
    session: aiohttp.ClientSession,
    url: str,
    message: str,
    request_id: int
) -> tuple[int, float, dict]:
    """
    Envia uma requisição e mede o tempo de resposta.
    
    Returns:
        Tupla (request_id, tempo_decorrido, resultado)
    """
    start = time.time()
    try:
        async with session.post(
            url,
            json={
                "chat_input": message,
                "session_id": f"parallel-test-{request_id}",
                "user_id": f"test-user-{request_id}",
                "metadata": {}
            },
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            result = await response.json()
            elapsed = time.time() - start
            
            status = "✅" if response.status == 200 else "❌"
            preview = result.get('response', '')[:60].replace('\n', ' ')
            
            print(f"{status} Request {request_id}: {elapsed:.2f}s - {preview}...")
            
            return (request_id, elapsed, result)
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        print(f"❌ Request {request_id}: TIMEOUT após {elapsed:.2f}s")
        return (request_id, elapsed, {"error": "timeout"})
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Request {request_id}: ERRO após {elapsed:.2f}s - {str(e)}")
        return (request_id, elapsed, {"error": str(e)})


async def test_parallel(server_ip: str, num_requests: int = 3):
    """
    Testa múltiplas requisições em paralelo.
    
    Args:
        server_ip: IP do servidor
        num_requests: Número de requisições simultâneas
    """
    url = f"http://{server_ip}:8000/api/v1/chat"
    
    print(f"\n{'='*70}")
    print(f"🧪 Teste de Processamento Paralelo")
    print(f"{'='*70}")
    print(f"🌐 Servidor: {url}")
    print(f"📊 Requisições simultâneas: {num_requests}")
    print(f"{'='*70}\n")
    
    # Mensagens diferentes para cada requisição
    message_templates = [
        "Hello, how are you?",
        "How are you doing?",
        "Como funciona o sistema?",
        "Quais são as funcionalidades?",
        "Explique sobre o produto",
    ]
    
    async with aiohttp.ClientSession() as session:
        # Cria tarefas para todas as requisições
        tasks = [
            send_request(
                session,
                url,
                f"{message_templates[i % len(message_templates)]} (req {i+1})",
                i + 1
            )
            for i in range(num_requests)
        ]
        
        # Executa todas em paralelo e mede o tempo total
        print("🚀 Enviando requisições simultaneamente...\n")
        start_total = time.time()
        
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_total
        
        # Análise dos resultados
        print(f"\n{'='*70}")
        print(f"📊 Resultados")
        print(f"{'='*70}")
        
        successful = [r for r in results if "error" not in r[2]]
        failed = [r for r in results if "error" in r[2]]
        
        if successful:
            times = [r[1] for r in successful]
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            
            print(f"✅ Sucesso: {len(successful)}/{num_requests}")
            print(f"⏱️  Tempo total (paralelo): {total_time:.2f}s")
            print(f"⏱️  Tempo médio por requisição: {avg_time:.2f}s")
            print(f"⏱️  Tempo mínimo: {min_time:.2f}s")
            print(f"⏱️  Tempo máximo: {max_time:.2f}s")
            
            # Calcula o ganho teórico se fosse sequencial
            sequential_time = sum(times)
            if total_time > 0:
                speedup = sequential_time / total_time
                print(f"\n💡 Se fosse sequencial: {sequential_time:.2f}s")
                print(f"💡 Ganho de paralelismo: {speedup:.2f}x")
                
                if speedup > 1.5:
                    print(f"✅ Processamento paralelo funcionando corretamente!")
                elif speedup > 1.1:
                    print(f"⚠️  Processamento parcialmente paralelo (pode haver bloqueios)")
                else:
                    print(f"❌ Processamento ainda está sequencial (verifique o código)")
        
        if failed:
            print(f"\n❌ Falhas: {len(failed)}/{num_requests}")
            for req_id, elapsed, result in failed:
                print(f"   Request {req_id}: {result.get('error', 'unknown error')}")
        
        print(f"{'='*70}\n")


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        print("❌ Uso: python test_parallel_requests.py <IP_DO_SERVIDOR> [num_requests]")
        print("\nExemplos:")
        print("  python test_parallel_requests.py 192.168.0.46")
        print("  python test_parallel_requests.py 192.168.0.46 5")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    num_requests = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    try:
        asyncio.run(test_parallel(server_ip, num_requests))
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

