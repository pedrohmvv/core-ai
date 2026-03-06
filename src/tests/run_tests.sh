#!/bin/bash
# Script para executar todos os testes

echo "🧪 Executando Testes - Sileto LangGraph"
echo "========================================"
echo ""

# Verifica se está no diretório correto
if [ ! -d "src" ]; then
    echo "❌ Execute este script do diretório raiz do projeto"
    exit 1
fi

# Executa testes unitários
echo "📦 Testes Unitários..."
pytest src/tests/app/chat/test_chat_service.py -v

# Executa testes de API
echo ""
echo "🌐 Testes de API..."
pytest src/tests/app/chat/test_chat_api.py -v

# Executa todos os testes
echo ""
echo "✅ Todos os testes..."
pytest src/tests/ -v

echo ""
echo "✨ Testes concluídos!"

