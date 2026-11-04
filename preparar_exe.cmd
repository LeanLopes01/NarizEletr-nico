@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Gerador do Executável (.exe) — Nariz Eletrônico v0.4.3

:: Garante que o script rode a partir da pasta onde está localizado
cd /d "%~dp0"

echo ============================================================================
echo   GERADOR DO EXECUTÁVEL (.EXE) — NARIZ ELETRÔNICO v0.4.3
echo ============================================================================
echo.
echo Este comando executará a preparação e compilação do executável:
echo   [Passo 1/4] Verificação do ambiente Python
echo   [Passo 2/4] Verificação de dependências (PyQt6, pyqtgraph, etc.) e PyInstaller
echo   [Passo 3/4] Limpeza de arquivos temporários de compilações antigas
echo   [Passo 4/4] Compilação do executável (PyInstaller via NarizEletronico.spec)
echo ============================================================================
echo.

:: ----------------------------------------------------------------------------
:: [PASSO 1/4] VERIFICAÇÃO DO PYTHON
:: ----------------------------------------------------------------------------
echo [Passo 1/4] Verificando instalação do Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] O comando "python" não foi encontrado no PATH do sistema.
    echo Verifique a instalação do Python antes de continuar.
    goto :erro
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo [OK] Python detectado: !PY_VER!
echo.

:: ----------------------------------------------------------------------------
:: [PASSO 2/4] INSTALAÇÃO DE DEPENDÊNCIAS E PYINSTALLER
:: ----------------------------------------------------------------------------
echo [Passo 2/4] Verificando e instalando dependências necessárias...
python -m pip install -r requirements.txt pyinstaller
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependências via pip.
    goto :erro
)
echo [OK] Todas as bibliotecas e o PyInstaller estão prontos.
echo.

:: ----------------------------------------------------------------------------
:: [PASSO 3/4] LIMPEZA DE PASTAS TEMPORÁRIAS ANTERIORES
:: ----------------------------------------------------------------------------
echo [Passo 3/4] Limpando pastas temporárias de compilações anteriores...
if exist "build" (
    echo   - Removendo pasta temporária "build\"...
    rd /s /q "build"
)
if exist "dist\NarizEletronico" (
    echo   - Limpando compilação anterior em "dist\NarizEletronico\"...
    rd /s /q "dist\NarizEletronico"
)
echo [OK] Ambiente pronto para o build.
echo.

:: ----------------------------------------------------------------------------
:: [PASSO 4/4] GERAÇÃO DO .EXE COM PYINSTALLER
:: ----------------------------------------------------------------------------
echo [Passo 4/4] Compilando executável com PyInstaller...
echo [INFO] Aguarde... Isso leva cerca de 1 minuto enquanto empacota o Qt e os módulos.
echo.

python -m PyInstaller --noconfirm --clean NarizEletronico.spec
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Ocorreu uma falha durante o empacotamento com o PyInstaller.
    goto :erro
)

:: Validação de integridade do arquivo gerado
if not exist "dist\NarizEletronico\NarizEletronico.exe" (
    echo.
    echo [ERRO] O executável "dist\NarizEletronico\NarizEletronico.exe" não foi encontrado após o build.
    goto :erro
)

echo.
echo ============================================================================
echo   🎉 EXECUTÁVEL GERADO COM SUCESSO!
echo ============================================================================
echo   Localização: dist\NarizEletronico\NarizEletronico.exe
echo.
echo Agora o arquivo que o Inno Setup precisa JÁ EXISTE!
echo Você já pode dar dois cliques no seu arquivo "instalador_inno_setup.iss"
echo para abrir o Inno Setup e compilar o instalador sem erros.
echo ============================================================================
echo.

choice /C SN /N /M "Deseja que eu abra o 'instalador_inno_setup.iss' no Inno Setup agora? [S/N]: "
if !errorlevel! equ 1 (
    echo Abrindo instalador_inno_setup.iss...
    start "" "instalador_inno_setup.iss"
)

echo.
pause
exit /b 0

:erro
echo.
echo ============================================================================
echo   ❌ FALHA NA GERAÇÃO DO .EXE
echo ============================================================================
echo Revise as mensagens acima para verificar o motivo do erro.
echo.
pause
exit /b 1
