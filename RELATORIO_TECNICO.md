# Relatorio Tecnico — E-NOSE CONTROL & ANALYTICS v0.4.3 (Arduino UNO R3)

**Data:** 04/11/2026  
**Hardware-alvo:** Arduino UNO Rev3 (ATmega328P, 16 MHz)  
**Aplicacao Desktop:** Python 3.11+ com `PyQt6`/`PySide6`, `pyqtgraph`, `pyserial`, `pandas`, `numpy` e `SQLite`  
**Base de Diretrizes:** `Sistema gás/v0.4.3` (`MainTodosJunto.py`, `mainGraficos3por3.py`, `mainGraficosQuadrados.py`) + `Sistema gás/v0.4.2/megaPyhtonSerial/megaPyhtonSerial.ino`

---

## 1. Visao Geral das Atualizacoes

O projeto **Nariz Eletronico** foi integralmente atualizado para operar com o sistema de controle de 6 etapas do `v0.4.2/megaPyhtonSerial.ino` portado para **Arduino UNO R3** e com todas as diretrizes experimentais e analiticas do `Sistema gás/v0.4.3`:

1. **Sensores e Conversao Analitica (`v0.4.3`)**:
   - Tres canais de gases MOS: `MQ2(A0)`, `MQ3(A1)` e `MQ5(A2)`.
   - Conversao ADC 10 bits para Tensao:
     $$V = \frac{\text{ADC}}{1023.0} \times 5.0\text{ V}$$
   - Monitoramento ambiental sincronizado via I2C `ClosedCube_HDC1080` (`0x40`): `Temperatura(C)`, `Umidade(%)` e coluna `Pressao(hPa)` nos arquivos exportados.
2. **Diretrizes de Ensaio (`v0.4.3`)**:
   - **Gases (`GAS_INFO`)**:
     - `A`: Acetone (Acetona)
     - `E`: Ethyl Alcohol (Alcool Etilico)
     - `P`: Isopropyl Alcohol (Alcool Isopropilico)
     - `AR`: Clean Air (Ar Limpo / Referencia)
   - **Configuracoes de Camara / Aletas (`CONFIG_NAMES`)**:
     - `0`: `Default` (Sem Aleta)
     - `1`: `Config V`
     - `2`: `Config A`
     - `3`: `Config X`
     - `4`: `Config O`
   - **Repeticoes**: `R1`, `R2`, `R3`
   - **Concentracoes**: `100 ppm`, `200 ppm` (Volume do recipiente: `200 mL`).
   - **Padrao de Arquivo CSV (`v0.4.3`)**: `dados/<config>/<GAS><CONFIG>-<REP>-<CONC>.csv` (exemplo: `dados/0/A0-R1-100.csv`), delimitado por `;` com cabecalho:
     ```text
     Tempo(s);MQ2(A0);MQ3(A1);MQ5(A2);Temperatura(C);Umidade(%);Pressao(hPa)
     ```

---

## 2. Firmware do Arduino UNO R3 (`nariz_eletronico.ino`)

O código original `megaPyhtonSerial.ino` (desenvolvido para Arduino Mega 2560 com pinos `22, 24, 26, 28`) foi portado para o **Arduino UNO R3 (ATmega328P)**:

### 2.1 Mapeamento de Pinos no Arduino UNO R3

| Sinal | Pino UNO | Direcao | Descricao |
|---|---|---|---|
| `V1` | **D6** | `OUTPUT` | Relé 1 (Valvula 1) |
| `V2` | **D7** | `OUTPUT` | Relé 2 (Valvula 2) |
| `V3` | **D8** | `OUTPUT` | Relé 3 (Valvula 3) |
| `BOMBA` | **D9** | `OUTPUT` | Relé 4 (Bomba) |
| `MQ2` | **A0** | `INPUT` | Sensor MQ-2 |
| `MQ3` | **A1** | `INPUT` | Sensor MQ-3 |
| `MQ5` | **A2** | `INPUT` | Sensor MQ-5 |
| `SDA` | **A4** | `I2C` | HDC1080 SDA (`0x40`) |
| `SCL` | **A5** | `I2C` | HDC1080 SCL (`0x40`) |

### 2.2 Timer1 e Maquina de 6 Etapas

- **Timer1 em modo CTC**: Prescaler `64`, `OCR1A = 62499` → interrupcao exata a cada **250 ms** (`4 Hz`) em clock de `16 MHz`.
- **Correcao de bug de 16 bits no comando `SET`**: No AVR (UNO/Mega), `int` possui 16 bits (`-32768..32767`). O parser `sscanf(cmd.c_str(), "SET %d %lu", &etapa, &tempo)` agora utiliza `unsigned long` (`%lu`), permitindo configurar etapas de `60000 ms` (`60 s`) ou maiores sem overflow.
- **Driver I2C HDC1080 com Fallback Automatico**: Utiliza `ClosedCube_HDC1080.h` se instalada na Arduino IDE, ou comunica-se diretamente com o registrador `0x00`/`0x01` no endereco `0x40` via `<Wire.h>` caso a biblioteca externa nao esteja instalada.

### 2.3 Protocolo Serial (`115200 bps`)

| Comando (Python → UNO) | Funcao | Resposta do UNO |
|---|---|---|
| `START` | Inicia o ciclo na Etapa 0 e zera o contador de tempo | `Etapa 0` / `CICLO STARTED` |
| `STOP` | Interrompe o ciclo e coloca o sistema na Etapa 5 | `Etapa 5 (final) - tudo desligado` / `CICLO STOPPED` |
| `RESET` | Reinicia o ciclo para inativo e zera `secondsCounter` | `Etapa 5 (final) - tudo desligado` / `RESET` |
| `SHOW` | Lista os tempos configurados para as Etapas `0..5` | `Tempos atuais (ms):` seguido de `Etapa 0: ...` a `Etapa 5: ...` |
| `SET <etapa> <ms>` | Altera a duracao da etapa `0..5` em milissegundos | `Etapa <n> tempo atualizado para <ms> ms` |

Durante a execucao (`cicloAtivo == true`), o UNO transmite a cada `1000 ms` (`1 Hz`):
```text
Tempo(s),MQ2(A0),MQ3(A1),MQ5(A2),Temperatura(C),Umidade(%)
0,218,438,352,29.24,52.96
1,218,438,352,29.24,52.96
```

---

## 3. Dashboard Controlador e Analisador Cientifico (`desktop/`)

### 3.1 Grafico em Tempo Real com Tempo Total no Eixo X (Aba 1)
- O eixo X do grafico em tempo real e fixado no **Tempo Total do Ciclo** ($0\text{ s}$ ate $T_{\text{total}} = \sum_{i=0}^{5} T_i$, por exemplo $190\text{ s}$ no protocolo oficial `v0.4.3`).
- As faixas coloridas das etapas (`E1: Baseline`, `E2: Exposicao`, `E3: Retencao`, `E4: Purga`, `E5: Final`) ficam visiveis ao fundo desde o inicio do ciclo.
- Conforme as leituras chegam a cada segundo do Arduino UNO (ou da Bancada Virtual), as curvas de `MQ2 (A0)`, `MQ3 (A1)` e `MQ5 (A2)` — junto com o grafico sincronizado de `Temperatura (°C)` e `Umidade (%)` — vao se formando visualmente da esquerda para a direita com marcadores luminosos na ponta ativa e cursor vertical de progresso.
- Ao concluir o ciclo (`CICLO FINALIZADO`), o ensaio e salvo automaticamente no padrao `v0.4.3` (`dados/<config>/<GAS><CONFIG>-<REP>-<CONC>.csv`).

### 3.2 Analisador Detalhado v0.4.3 (Aba 2)
- Reproduz e expande o `MainTodosJunto.py`:
  - **Repeticoes (`R1`, `R2`, `R3` + Media)**: Curvas individuais tracejadas e curva media solida com marcador de $V_{\max}$.
  - **Comparativo de Aletas (`Default`, `Config V`, `Config A`, `Config X`, `Config O`)**: Sobreposicao direta das 5 configuracoes para o gas e sensor selecionados.
  - **Comparativo de Gases (`A`, `E`, `P`, `AR`)**: Resposta comparada entre compostos para a mesma aleta.
  - **Derivada $dV/dt$ ($\text{V/s}$)**: Taxa instantanea de resposta dos sensores.
  - **Tabela Completa de Metricas Avancadas**: `V_baseline (V)`, `V_max Abs (V)`, `V_max Relativo (V)`, `Tempo V_max (s)`, `Taxa Max (V/s)`, `Tempo Subida (s)`, `Tempo Descida (s)`, `AUC (V·s)` e `Erro Mult. (%)`.

### 3.3 Matriz 3×3 & Tabelas Comparativas `% vs Default` (Aba 3)
- Reproduz `mainGraficos3por3.py` e `mainGraficosQuadrados.py`:
  - **Grade 3×3 de Graficos**: Linhas = Gases (`Ethyl Alcohol`, `Isopropyl Alcohol`, `Acetone`) × Colunas = Sensores (`MQ2`, `MQ3`, `MQ5`), comparando simultaneamente as 5 configuracoes de aletas (`0..4`).
  - **Tabelas Comparativas por Sensor**: Exibem $\Delta V_{\max}\text{ Relativo (V)}$ e a eficiencia percentual relativa a configuracao `Default` (`100.0%`).
