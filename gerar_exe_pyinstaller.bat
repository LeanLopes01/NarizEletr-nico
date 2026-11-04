@echo off
chcp 65001 >nul
echo ============================================================================
echo   PREPARACAO DO EXECUTAVEL (.EXE) — NARIZ ELETRONICO v0.4.3
echo   (Execute este script apenas quando quiser gerar a pasta dist\NarizEletronico)
echo ============================================================================
echo.

python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean NarizEletronico.spec

echo.
echo [CONCLUIDO] O executavel foi gerado em: dist\NarizEletronico\NarizEletronico.exe
echo Agora voce pode abrir o arquivo "instalador_inno_setup.iss" no Inno Setup
echo ou rodar "python automacao_release\novaVersao.py" para publicar a Release.
pause
