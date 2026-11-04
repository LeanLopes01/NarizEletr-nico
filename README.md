# E-NOSE CONTROL & ANALYTICS v0.4.3 — Nariz Eletrônico (Arduino UNO R3)

Sistema integrado de controle de bancada, aquisição em tempo real, análise científica e auto-update para o **Nariz Eletrônico (Python + Arduino UNO R3 / ATmega328P)**:

1. **Diretrizes e Analisadores do `Sistema gás/v0.4.3`** (`MainTodosJunto.py`, `mainGraficos3por3.py`, `mainGraficosQuadrados.py`).
2. **Firmware do `Sistema gás/v0.4.2/megaPyhtonSerial/megaPyhtonSerial.ino`** adaptado para **Arduino UNO R3**.
3. **Dashboard Controlador Científico/Industrial em Tempo Real** (`PyQt6`/`PySide6` + `pyqtgraph`), com **Tempo Total no eixo X**, formação visual progressiva das curvas (`MQ2`, `MQ3`, `MQ5`, `Temperatura`, `Umidade`), divisórias móveis redimensionáveis (`QSplitter`) e ícones `?` com explicações instantâneas em cada opção.
4. **Sistema de Auto-Update via GitHub Releases (`LeanLopes01/NarizEletr-nico`)** tolerante a modo offline (avisa se não houver internet sem bloquear o uso do software).
5. **Preparado para PyInstaller (`.exe`) e Inno Setup (`instalador_inno_setup.iss`)**.

---

## Arquitetura de Arquivos

- `nariz_eletronico.ino` e `arduino/nariz_eletronico/nariz_eletronico.ino` — Firmware do **Arduino UNO R3** baseado no `megaPyhtonSerial.ino` (Timer1 250 ms, 6 etapas `Etapa 0..5`, 4 relés `V1, V2, V3, BOMBA`, 3 sensores `MQ2(A0), MQ3(A1), MQ5(A2)`, I2C `HDC1080` em `A4/A5` `0x40`, saída CSV a 1 Hz).
- `desktop/main.py` — Dashboard Controlador & Analisador Científico v0.4.3 com tooltips `?` instantâneos, botão **◫ Ajustar Proporções** e verificação de atualização.
- `desktop/analysis.py` — Classe `AnalisadorGases` e diretrizes completas do `v0.4.3`.
- `desktop/protocol.py` — Parser serial compatível com `megaPyhtonSerial.ino` (`START`, `STOP`, `RESET`, `SHOW`, `SET <etapa> <tempo_ms>`).
- `desktop/workers.py` — Threads de comunicação serial (`SerialWorker`) e bancada virtual (`SimulationWorker`).
- `desktop/storage.py` — Persistência local em SQLite e exportação direta no formato oficial do `v0.4.3` (`dados/<config>/<GAS><CONFIG>-<REP>-<CONC>.csv`, separador `;`).
- `desktop/updater.py` e `desktop/version.py` — Verificador e instalador automático de novas versões via GitHub Releases com suporte total a operação offline.
- `NarizEletronico.spec` e `gerar_exe_pyinstaller.bat` — Configuração pronta para gerar o `.exe` com PyInstaller quando desejar lançar uma versão.
- `instalador_inno_setup.iss` — Script do **Inno Setup** preparado para empacotar o instalador Windows (`nariz-eletronico-<versao>-setup.exe`).
- `automacao_release/` (`novaVersao.py`, `atualizacao.py`, `notas_utils.py`, `NotasAtualizacao.md`) — Automação de deploy para o GitHub Releases e atualização de `version.json`.

---

## Como Executar em Modo Desenvolvimento

```powershell
cd "d:\Programação\Projetos Python USP\IC\Nariz Eletronico"
python -m pip install -r requirements.txt
python -m desktop.main
```

---

## Como Gerar o `.exe` e Publicar Instalador (Inno Setup + Auto-Update)

> **Nota:** Os scripts abaixo já estão configurados e prontos, devendo ser executados apenas quando você finalizar seus ajustes e quiser lançar uma versão oficial:

1. **Atualizar a versão** em `version.json` (ex.: `"version": "0.4.3"`).
2. **Gerar o executável (`.exe`) com PyInstaller**:
   ```powershell
   .\gerar_exe_pyinstaller.bat
   ```
   *(Gera a pasta `dist\NarizEletronico\NarizEletronico.exe` sem compilar antes da hora).*
3. **Compilar o Instalador no Inno Setup e Publicar Release no GitHub**:
   - Manualmente: abra `instalador_inno_setup.iss` no **Inno Setup** e clique em **Compile**.
   - Automaticamente (compila via Inno Setup + cria Release no GitHub + envia `.exe` + atualiza `version.json`):
     ```powershell
     python automacao_release\novaVersao.py
     ```
