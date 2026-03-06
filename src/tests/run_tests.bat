@echo off
REM Script para executar todos os testes (Windows)

echo 🧪 Executando Testes - Sileto LangGraph
echo ========================================
echo.

REM Verifica se está no diretório correto
if not exist "src" (
    echo ❌ Execute este script do diretório raiz do projeto
    exit /b 1
)

REM Executa testes unitários
echo 📦 Testes Unitários...
pytest src/tests/app/chat/test_chat_service.py -v

REM Executa testes de API
echo.
echo 🌐 Testes de API...
pytest src/tests/app/chat/test_chat_api.py -v

REM Executa todos os testes
echo.
echo ✅ Todos os testes...
pytest src/tests/ -v

echo.
echo ✨ Testes concluídos!
pause

