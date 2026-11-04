"""Dashboard Controlador e Analisador Cientifico/Industrial do Nariz Eletronico v0.4.3.

Execucao:
    python -m desktop.main
"""
from __future__ import annotations

import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyqtgraph as pg
from serial.tools import list_ports

from .analysis import (
    CONCENTRACOES,
    CONFIG_IDS,
    CONFIG_NAMES,
    CORES_CONFIG,
    CORES_GASES,
    CORES_NEON,
    CORES_SENSORES,
    GAS_CODES_3X3,
    GAS_CODES_ALL,
    GAS_INFO,
    GAS_LABELS_PT,
    REPETICOES,
    SENSORES,
    AnalisadorGases,
    default_v043_data_dir,
    format_v043_filename,
    realtime_metrics,
)
from .protocol import (
    DEFAULT_STAGE_DURATIONS_FAST_MS,
    DEFAULT_STAGE_DURATIONS_INO_MS,
    DEFAULT_STAGE_DURATIONS_V043_MS,
    STAGE_NAMES,
    STAGE_RELAY_LEVELS,
    STAGE_SHORT_NAMES,
)
from .qt_compat import (
    QApplication,
    QCheckBox,
    QComboBox,
    QCursor,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimer,
    QToolTip,
    QVBoxLayout,
    QWidget,
    Qt,
)
from .storage import Storage
from .updater import UpdateCheckWorker, UpdateDownloadWorker, apply_downloaded_update
from .version import GITHUB_RELEASES_URL, GITHUB_REPO_URL, get_local_version
from .workers import SerialWorker, SimulationWorker

# Paleta de faixa de etapas no fundo do grafico em tempo real
STAGE_SHADE_COLORS = {
    0: (148, 163, 184, 18),
    1: (56, 189, 248, 20),   # E1: Limpeza / Baseline (Azul)
    2: (244, 63, 94, 26),    # E2: Exposicao ao Gas (Vermelho/Rosa)
    3: (245, 158, 11, 22),   # E3: Camara Fechada (Ambar)
    4: (16, 185, 129, 20),   # E4: Purga / Recuperacao (Verde)
    5: (148, 163, 184, 18),  # E5: Final
}

INDUSTRIAL_STYLE = """
QWidget {
    background-color: #0b101b;
    color: #e2e8f0;
    font: 9pt 'Segoe UI', sans-serif;
}
QMainWindow {
    background-color: #0b101b;
}
QToolTip {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #38bdf8;
    border-radius: 6px;
    padding: 8px 10px;
    font: 9pt 'Segoe UI';
}
QFrame#topHeader {
    background-color: #111827;
    border: 1px solid #1f2d42;
    border-radius: 8px;
}
QLabel#brandTitle {
    font: 700 13.5pt 'Segoe UI';
    color: #f8fafc;
    letter-spacing: 0.4px;
}
QLabel#brandSubtitle {
    font: 8.5pt 'Consolas', monospace;
    color: #38bdf8;
}
QLabel#helpBadge {
    background-color: #162238;
    color: #38bdf8;
    border: 1px solid #2b4c7e;
    border-radius: 9px;
    font: 700 8.5pt 'Segoe UI';
    min-width: 18px;
    max-width: 18px;
    min-height: 18px;
    max-height: 18px;
}
QLabel#helpBadge:hover {
    background-color: #0284c7;
    color: #ffffff;
    border-color: #7dd3fc;
}
QFrame#telemetryCard {
    background-color: #131c2e;
    border: 1px solid #23324a;
    border-radius: 6px;
}
QLabel#telemetryTitle {
    font: 700 7.5pt 'Segoe UI';
    color: #94a3b8;
    letter-spacing: 0.5px;
}
QLabel#telemetryValue {
    font: 700 11.5pt 'Consolas', monospace;
    color: #f8fafc;
}
QLabel#telemetrySub {
    font: 8pt 'Consolas', monospace;
    color: #64748b;
}
QFrame#relayBadgeOff {
    background-color: #162032;
    border: 1px solid #2b3b55;
    border-radius: 6px;
    padding: 2px 6px;
}
QFrame#relayBadgeOn {
    background-color: #064e3b;
    border: 1px solid #10b981;
    border-radius: 6px;
    padding: 2px 6px;
}
QGroupBox {
    background-color: #111927;
    border: 1px solid #223147;
    border-radius: 8px;
    margin-top: 9px;
    padding: 10px 8px 8px 8px;
    font-weight: 700;
    color: #cbd5e1;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #38bdf8;
    font: 700 8.5pt 'Segoe UI';
}
QPushButton {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 5px 9px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #28364d;
    border-color: #38bdf8;
}
QPushButton:disabled {
    background-color: #131b29;
    color: #475569;
    border-color: #1e293b;
}
QPushButton#btnStart {
    background-color: #059669;
    border: 1px solid #10b981;
    color: #ffffff;
    font: 700 10pt 'Segoe UI';
    padding: 9px 12px;
}
QPushButton#btnStart:hover {
    background-color: #10b981;
}
QPushButton#btnStart:disabled {
    background-color: #132a25;
    border-color: #1b3b33;
    color: #4b6b63;
}
QPushButton#btnStop {
    background-color: #be123c;
    border: 1px solid #f43f5e;
    color: #ffffff;
    font: 700 10pt 'Segoe UI';
    padding: 9px 12px;
}
QPushButton#btnStop:hover {
    background-color: #e11d48;
}
QPushButton#btnStop:disabled {
    background-color: #2c151e;
    border-color: #3f1d2b;
    color: #6e4756;
}
QPushButton#btnReset {
    background-color: #b45309;
    border: 1px solid #f59e0b;
    color: #ffffff;
    font-weight: 700;
    padding: 7px 10px;
}
QPushButton#btnReset:hover {
    background-color: #d97706;
}
QPushButton#btnAction {
    background-color: #1d4ed8;
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 700;
}
QPushButton#btnAction:hover {
    background-color: #2563eb;
}
QPushButton#btnSim {
    background-color: #312e81;
    border: 1px solid #6366f1;
    color: #e0e7ff;
    font-weight: 700;
}
QPushButton#btnSim:hover {
    background-color: #3730a3;
}
QPushButton#btnUpdateReady {
    background-color: #059669;
    border: 1px solid #34d399;
    color: #ffffff;
    font-weight: 700;
}
QPushButton#btnUpdateReady:hover {
    background-color: #10b981;
}
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTableWidget {
    background-color: #090e17;
    border: 1px solid #283852;
    border-radius: 5px;
    padding: 4px 6px;
    color: #f1f5f9;
    selection-background-color: #2563eb;
}
QSpinBox, QLineEdit {
    font-family: 'Consolas', monospace;
}
QTableWidget {
    gridline-color: #1e293b;
    alternate-background-color: #0f172a;
}
QHeaderView::section {
    background-color: #162235;
    color: #38bdf8;
    border: none;
    border-right: 1px solid #23324a;
    border-bottom: 1px solid #23324a;
    padding: 5px;
    font-weight: 700;
}
QTabWidget::pane {
    border: 1px solid #223147;
    border-radius: 6px;
    background-color: #0e1525;
}
QTabBar::tab {
    background-color: #131c2e;
    color: #94a3b8;
    border: 1px solid #223147;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 14px;
    margin-right: 4px;
    font-weight: 700;
}
QTabBar::tab:selected {
    background-color: #1e293b;
    color: #38bdf8;
    border-color: #38bdf8;
}
QProgressBar {
    background-color: #090e17;
    border: 1px solid #283852;
    border-radius: 4px;
    text-align: center;
    color: #f8fafc;
    font: 700 8pt 'Consolas', monospace;
    max-height: 15px;
    min-height: 15px;
}
QProgressBar::chunk {
    background-color: #0284c7;
    border-radius: 3px;
}
QSplitter::handle {
    background-color: #162238;
    border: 1px solid #263854;
    border-radius: 3px;
}
QSplitter::handle:horizontal {
    width: 8px;
    margin: 2px 1px;
}
QSplitter::handle:vertical {
    height: 8px;
    margin: 1px 2px;
}
QSplitter::handle:hover {
    background-color: #0284c7;
    border-color: #38bdf8;
}
QScrollBar:vertical {
    background: #0b101b;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar:horizontal {
    background: #0b101b;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #334155;
    border-radius: 5px;
    min-width: 24px;
}
"""


class HelpBadge(QLabel):
    """Icone '?' interativo que exibe a explicacao detalhada imediatamente ao passar o mouse."""

    def __init__(self, tooltip_html: str, parent: QWidget | None = None):
        super().__init__("?", parent)
        self.setObjectName("helpBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.setToolTip(tooltip_html)

    def enterEvent(self, event):
        if self.toolTip():
            QToolTip.showText(QCursor.pos(), self.toolTip(), self)
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if self.toolTip():
            QToolTip.showText(QCursor.pos(), self.toolTip(), self)
        super().mousePressEvent(event)


def make_help_badge(tooltip_html: str) -> HelpBadge:
    return HelpBadge(tooltip_html)


def label_with_help(text: str, tooltip_html: str, bold: bool = False) -> QWidget:
    """Cria um par [Texto + icone '?'] alinhado horizontalmente com tooltip instantaneo."""
    container = QWidget()
    lay = QHBoxLayout(container)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    lbl = QLabel(f"<b>{text}</b>" if bold else text)
    lbl.setToolTip(tooltip_html)
    badge = HelpBadge(tooltip_html)
    lay.addWidget(lbl)
    lay.addWidget(badge)
    lay.addStretch()
    return container


def widget_with_help(widget: QWidget, tooltip_html: str, stretch: int = 1) -> QWidget:
    """Anexa um icone '?' ao lado direito de qualquer controle e configura o tooltip em ambos."""
    widget.setToolTip(tooltip_html)
    container = QWidget()
    lay = QHBoxLayout(container)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    lay.addWidget(widget, stretch)
    lay.addWidget(HelpBadge(tooltip_html), 0)
    return container


def make_compact_combo(min_width: int = 85) -> QComboBox:
    """Cria QComboBox que nao forca largura minima gigante no QSplitter."""
    cmb = QComboBox()
    cmb.setMinimumWidth(min_width)
    cmb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    cmb.setMinimumContentsLength(6)
    return cmb


def make_telemetry_card(
    title: str, initial_val: str, initial_sub: str = "", tooltip_html: str = ""
) -> tuple[QFrame, QLabel, QLabel]:
    card = QFrame()
    card.setObjectName("telemetryCard")
    if tooltip_html:
        card.setToolTip(tooltip_html)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(8, 5, 8, 5)
    lay.setSpacing(1)

    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    top_row.setSpacing(4)
    lbl_title = QLabel(title)
    lbl_title.setObjectName("telemetryTitle")
    top_row.addWidget(lbl_title)
    top_row.addStretch()
    if tooltip_html:
        top_row.addWidget(HelpBadge(tooltip_html))

    lbl_val = QLabel(initial_val)
    lbl_val.setObjectName("telemetryValue")
    lbl_sub = QLabel(initial_sub)
    lbl_sub.setObjectName("telemetrySub")

    lay.addLayout(top_row)
    lay.addWidget(lbl_val)
    lay.addWidget(lbl_sub)
    return card, lbl_val, lbl_sub


class UpdateDialog(QDialog):
    """Janela de atualizacao automatica via GitHub Releases (LeanLopes01/NarizEletr-nico)."""

    def __init__(self, update_info: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.update_info = update_info
        self.download_worker: UpdateDownloadWorker | None = None
        self.setWindowTitle(f"Atualização Disponível — v{update_info.get('remote_version')}")
        self.setMinimumSize(540, 380)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lbl_head = QLabel(
            f"<span style='font-size:13pt; font-weight:700; color:#38bdf8;'>"
            f"Nova versão disponível: v{update_info.get('remote_version')}</span><br>"
            f"<span style='color:#94a3b8;'>Versão instalada: v{update_info.get('local_version')}  |  "
            f"Título: {update_info.get('title', '')}</span>"
        )
        lay.addWidget(lbl_head)

        lbl_notes_title = QLabel("<b>Notas da Versão / Release Notes:</b>")
        lay.addWidget(lbl_notes_title)

        self.txt_notes = QPlainTextEdit()
        self.txt_notes.setReadOnly(True)
        self.txt_notes.setPlainText(update_info.get("notes") or "Sem notas adicionais na release.")
        lay.addWidget(self.txt_notes, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        lay.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #34d399; font-family: 'Consolas';")
        lay.addWidget(self.lbl_status)

        btn_row = QHBoxLayout()
        self.btn_install = QPushButton("⬇  Baixar e Instalar Atualização Agora")
        self.btn_install.setObjectName("btnStart")
        self.btn_install.clicked.connect(self._start_download)

        self.btn_browser = QPushButton("🌐  Abrir Página no GitHub")
        self.btn_browser.clicked.connect(
            lambda: webbrowser.open(str(self.update_info.get("html_url") or GITHUB_RELEASES_URL))
        )

        self.btn_later = QPushButton("Lembrar Depois")
        self.btn_later.clicked.connect(self.reject)

        btn_row.addWidget(self.btn_install, 2)
        btn_row.addWidget(self.btn_browser, 1)
        btn_row.addWidget(self.btn_later, 1)
        lay.addLayout(btn_row)

    def _start_download(self):
        dl_url = self.update_info.get("download_url")
        asset_name = self.update_info.get("asset_name")
        if not dl_url:
            webbrowser.open(str(self.update_info.get("html_url") or GITHUB_RELEASES_URL))
            self.accept()
            return

        self.btn_install.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Iniciando download pelo GitHub Releases...")

        self.download_worker = UpdateDownloadWorker(str(dl_url), str(asset_name or ""))
        self.download_worker.progress.connect(self._on_progress)
        self.download_worker.download_finished.connect(self._on_finished)
        self.download_worker.download_failed.connect(self._on_failed)
        self.download_worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_finished(self, file_path: str):
        ok, msg = apply_downloaded_update(file_path)
        self.lbl_status.setText(msg)
        if ok and file_path.lower().endswith(".exe"):
            QMessageBox.information(
                self,
                "Instalador Iniciado",
                f"{msg}\n\nO programa será fechado para que o Inno Setup atualize os arquivos.",
            )
            self.accept()
            QApplication.quit()
        elif ok:
            QMessageBox.information(self, "Atualização Baixada", msg)
            self.accept()
        else:
            self.btn_install.setEnabled(True)
            QMessageBox.warning(self, "Aviso na Instalação", msg)

    def _on_failed(self, err_msg: str):
        self.btn_install.setEnabled(True)
        self.lbl_status.setStyleSheet("color: #f43f5e;")
        self.lbl_status.setText(err_msg)
        QMessageBox.warning(self, "Erro no Download", err_msg)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.local_version = get_local_version()
        self.setWindowTitle(
            f"E-NOSE CONTROL & ANALYTICS v{self.local_version}  |  Arduino UNO R3 — Nariz Eletronico"
        )
        self._configure_initial_window_geometry()

        self.worker = None
        self.update_worker: UpdateCheckWorker | None = None
        self.latest_update_info: dict | None = None
        self.online = False
        self.running = False
        self.mode = "SERIAL"
        self.session_id: int | None = None
        self.last_session_id: int | None = None
        self.current_stage: int = 5

        # Buffers de aquisicao em tempo real (eixo X = Tempo Total em segundos)
        self.rt_times: list[float] = []
        self.rt_adc: dict[str, list[int]] = {"MQ2": [], "MQ3": [], "MQ5": []}
        self.rt_temp: list[float] = []
        self.rt_hum: list[float] = []
        self.rt_press: list[float] = []
        self.stage_regions: list[pg.LinearRegionItem] = []
        self.stage_lines: list[pg.InfiniteLine] = []

        # Pasta de dados v0.4.3 e armazenamento SQLite
        self.v043_data_dir = default_v043_data_dir()
        self.local_data_dir = Path(__file__).resolve().parent.parent / "dados"
        self.local_data_dir.mkdir(parents=True, exist_ok=True)
        self.storage = Storage(Path.home() / "NarizEletronico" / "experimentos.sqlite3")

        self._build_ui()
        self.refresh_ports()
        self._update_file_preview()
        self._rebuild_stage_overlays()
        self._set_ui_state()

        # Ajusta proporcoes iniciais dos splitters e carrega dados v0.4.3
        QTimer.singleShot(60, self.reset_layout_proportions)
        QTimer.singleShot(250, self.refresh_v043_analysis)
        # Verificacao automatica de atualizacao no GitHub em segundo plano (nao bloqueia modo offline)
        QTimer.singleShot(900, lambda: self.check_for_updates(manual=False))

    def _configure_initial_window_geometry(self):
        self.setMinimumSize(940, 580)
        screen = QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            w = min(1500, max(1024, int(avail.width() * 0.94)))
            h = min(880, max(640, int(avail.height() * 0.92)))
            self.resize(w, h)
        else:
            self.resize(1360, 800)

    # =========================================================================
    # CONSTRUCAO DA INTERFACE CIENTIFICA / INDUSTRIAL
    # =========================================================================
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(6)

        # 1. TOP BAR INDUSTRIAL + TELEMETRIA + SINOPTICO DE RELES + AUTO-UPDATE
        main_layout.addWidget(self._build_top_header(), 0)

        # 2. SPLITTER PRINCIPAL: PAINEL DE COMANDO (ESQUERDA) <-> ABAS (DIREITA)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setOpaqueResize(True)
        main_layout.addWidget(self.main_splitter, 1)

        self.left_scroll = self._build_left_control_panel()
        self.main_splitter.addWidget(self.left_scroll)

        self.tabs = QTabWidget()
        # Ignored horizontal size policy evita que o QTabWidget force 1600px de largura minima no QSplitter
        self.tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.tabs.setMinimumWidth(420)
        self.tabs.addTab(self._build_tab_realtime(), "1. AQUISIÇÃO E GRÁFICO EM TEMPO REAL")
        self.tabs.addTab(self._build_tab_analyzer(), "2. ANALISADOR DETALHADO v0.4.3 (R1/R2/R3 + ALETAS)")
        self.tabs.addTab(self._build_tab_matrix3x3(), "3. MATRIZ 3x3 + TABELAS COMPARATIVAS (% vs DEFAULT)")
        self.tabs.setTabToolTip(
            0,
            "<b>Aba 1 — Aquisição em Tempo Real:</b><br>"
            "Plota a formação das curvas de MQ2(A0), MQ3(A1), MQ5(A2) e HDC1080 (Temperatura/Umidade) "
            "ao vivo sobre o eixo X do Tempo Total do Ciclo.",
        )
        self.tabs.setTabToolTip(
            1,
            "<b>Aba 2 — Analisador Detalhado v0.4.3:</b><br>"
            "Analisa os arquivos CSV de ensaios: Repetições (R1, R2, R3 + Média), Comparativo de Aletas "
            "(Default, V, A, X, O), Comparativo de Gases, Derivada dV/dt e tabela completa de métricas.",
        )
        self.tabs.setTabToolTip(
            2,
            "<b>Aba 3 — Matriz 3×3 e Tabelas Comparativas:</b><br>"
            "Exibe a grade 3×3 (3 Gases × 3 Sensores) e as matrizes comparativas de eficiência (% vs Default).",
        )
        self.main_splitter.addWidget(self.tabs)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        self.statusBar().showMessage(
            f"Sistema Pronto (v{self.local_version})  |  Arduino UNO R3 (D6=V1, D7=V2, D8=V3, D9=Bomba | A0=MQ2, A1=MQ3, A2=MQ5 | I2C=HDC1080)  |  Dados v0.4.3: {self.v043_data_dir}"
        )

    def reset_layout_proportions(self):
        """Restaura todas as divisoes moveis (QSplitters) para proporcoes equilibradas."""
        total_w = max(960, self.width())
        left_w = min(385, max(310, int(total_w * 0.27)))
        right_w = max(500, total_w - left_w - 28)
        self.main_splitter.setSizes([left_w, right_w])

        total_h = max(480, self.tabs.height() - 70)
        self.rt_v_splitter.setSizes([int(total_h * 0.46), int(total_h * 0.23), int(total_h * 0.31)])
        self.rt_bottom_h_splitter.setSizes([int(right_w * 0.58), int(right_w * 0.42)])
        self.ana_v_splitter.setSizes([int(total_h * 0.68), int(total_h * 0.32)])
        self.m3_v_splitter.setSizes([int(total_h * 0.68), int(total_h * 0.32)])

    def _build_top_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("topHeader")
        v_lay = QVBoxLayout(header)
        v_lay.setContentsMargins(10, 6, 10, 6)
        v_lay.setSpacing(5)

        # Linha 1: Titulo, Botoes de Layout/Update e Sinoptico dos 4 Reles
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        title = QLabel(f"E-NOSE INDUSTRIAL CONTROLLER  //  v{self.local_version}")
        title.setObjectName("brandTitle")
        subtitle = QLabel("ARDUINO UNO R3  •  SENSORES: MQ2(A0) | MQ3(A1) | MQ5(A2) | HDC1080(I2C)  •  4 RELES: V1..V3 + BOMBA")
        subtitle.setObjectName("brandSubtitle")
        brand_col.addWidget(title)
        brand_col.addWidget(subtitle)
        top_row.addLayout(brand_col)
        top_row.addStretch()

        # Botao de restaurar proporcoes das janelas/splitters
        self.btn_reset_layout = QPushButton("◫ Ajustar Proporções")
        self.btn_reset_layout.setToolTip(
            "<b>Restaurar Proporções das Janelas:</b><br>"
            "Reorganiza automaticamente todas as barras divisórias móveis (painel lateral, gráficos e tabelas) "
            "para o tamanho padrão ideal da sua tela."
        )
        self.btn_reset_layout.clicked.connect(self.reset_layout_proportions)
        top_row.addWidget(self.btn_reset_layout)

        # Botao e status de Auto-Update (GitHub LeanLopes01/NarizEletr-nico)
        self.btn_check_update = QPushButton(f"🔄 v{self.local_version} (Verificar Atualização)")
        self.btn_check_update.setToolTip(
            f"<b>Sistema de Auto-Update (GitHub Releases):</b><br>"
            f"Repositório: <code>{GITHUB_REPO_URL}</code><br>"
            f"Verifica se há uma nova versão publicada nas Releases do GitHub.<br>"
            f"• Se não houver internet, o sistema avisa e continua funcionando 100% offline."
        )
        self.btn_check_update.clicked.connect(self._on_update_button_clicked)
        top_row.addWidget(
            widget_with_help(
                self.btn_check_update,
                f"<b>Auto-Update e Releases:</b><br>"
                f"Consulta <code>{GITHUB_REPO_URL}</code> para baixar novas versões compiladas no Inno Setup.<br>"
                f"Funciona normalmente mesmo sem acesso à internet (modo offline).",
                stretch=0,
            )
        )

        # Sinoptico dos 4 reles (D6..D9)
        relays_box = QHBoxLayout()
        relays_box.setSpacing(5)
        self.relay_badges: dict[str, tuple[QFrame, QLabel]] = {}
        relay_titles = [
            (
                "V1",
                "V1 (D6)",
                "<b>Relé V1 — Pino Digital D6 do Arduino UNO:</b><br>"
                "Controla a Válvula 1 conforme a tabela das 6 etapas do <code>megaPyhtonSerial.ino</code>.",
            ),
            (
                "V2",
                "V2 (D7)",
                "<b>Relé V2 — Pino Digital D7 do Arduino UNO:</b><br>"
                "Controla a Válvula 2 (linha de gás/ar conforme etapa ativa E0..E5).",
            ),
            (
                "V3",
                "V3 (D8)",
                "<b>Relé V3 — Pino Digital D8 do Arduino UNO:</b><br>"
                "Controla a Válvula 3 (retenção/exaustão nas etapas E3 e E4).",
            ),
            (
                "BOMBA",
                "BOMBA (D9)",
                "<b>Relé BOMBA — Pino Digital D9 do Arduino UNO:</b><br>"
                "Controla a bomba de fluxo/vácuo durante o ciclo de amostragem e limpeza.",
            ),
        ]
        for key, label_txt, tip in relay_titles:
            badge = QFrame()
            badge.setObjectName("relayBadgeOff")
            badge.setToolTip(tip)
            b_lay = QVBoxLayout(badge)
            b_lay.setContentsMargins(6, 2, 6, 2)
            b_lay.setSpacing(0)
            lbl_name = QLabel(label_txt)
            lbl_name.setStyleSheet("font: 700 7.5pt 'Segoe UI'; color: #cbd5e1;")
            lbl_state = QLabel("Pino: LOW")
            lbl_state.setStyleSheet("font: 700 8pt 'Consolas'; color: #94a3b8;")
            b_lay.addWidget(lbl_name)
            b_lay.addWidget(lbl_state)
            relays_box.addWidget(badge)
            self.relay_badges[key] = (badge, lbl_state)

        top_row.addLayout(relays_box)
        v_lay.addLayout(top_row)

        # Linha 2: Cartoes de Telemetria Instantanea com icones '?'
        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(6)
        cards_grid.setVerticalSpacing(3)

        c0, self.lbl_conn_val, self.lbl_conn_sub = make_telemetry_card(
            "CONEXÃO / MODO",
            "DESCONECTADO",
            "UART 115200 8N1",
            "<b>Status da Conexão:</b><br>"
            "Indica se o software está conectado ao Arduino UNO R3 via porta USB Serial (115200 bps) "
            "ou operando na Bancada Virtual (Modo Simulação v0.4.3).",
        )
        c1, self.lbl_stage_val, self.lbl_stage_sub = make_telemetry_card(
            "ETAPA ATUAL (0..5)",
            "AGUARDANDO",
            "Relés em espera",
            "<b>Etapa Atual da Máquina de Estados (Timer1 250ms):</b><br>"
            "• <b>E0:</b> Preparação inicial<br>"
            "• <b>E1:</b> Limpeza / Baseline (60s padrão v0.4.3)<br>"
            "• <b>E2:</b> Exposição ao Gás / Amostra (30s)<br>"
            "• <b>E3:</b> Câmara Fechada / Retenção (30s)<br>"
            "• <b>E4:</b> Purga / Recuperação (60s)<br>"
            "• <b>E5:</b> Finalização — tudo desligado (10s)",
        )
        c2, self.lbl_time_val, self.lbl_time_sub = make_telemetry_card(
            "TEMPO / TOTAL",
            "000s / 190s",
            "Progresso: 0%",
            "<b>Cronômetro do Ciclo:</b><br>"
            "Mostra o tempo decorrido em segundos (enviado a 1 Hz pelo Arduino UNO) em relação "
            "ao Tempo Total planejado (soma das etapas E0 a E5).",
        )
        c3, self.lbl_mq2_val, self.lbl_mq2_sub = make_telemetry_card(
            "MQ2 (A0)",
            "--- V",
            "ADC: ---",
            "<b>Sensor MQ-2 (Pino Analógico A0):</b><br>"
            "Sensível a gases combustíveis, GLP, propano, hidrogênio, álcool e fumaça.<br>"
            "Conversão v0.4.3: <code>V = (ADC / 1023.0) * 5.0 V</code>.",
        )
        c4, self.lbl_mq3_val, self.lbl_mq3_sub = make_telemetry_card(
            "MQ3 (A1)",
            "--- V",
            "ADC: ---",
            "<b>Sensor MQ-3 (Pino Analógico A1):</b><br>"
            "Alta sensibilidade a vapores de álcool (etanol/isopropanol) e solventes orgânicos voláteis (acetona).<br>"
            "Conversão v0.4.3: <code>V = (ADC / 1023.0) * 5.0 V</code>.",
        )
        c5, self.lbl_mq5_val, self.lbl_mq5_sub = make_telemetry_card(
            "MQ5 (A2)",
            "--- V",
            "ADC: ---",
            "<b>Sensor MQ-5 (Pino Analógico A2):</b><br>"
            "Sensível a gases naturais, GLP e resposta cruzada complementar para discriminação na matriz 3×3.<br>"
            "Conversão v0.4.3: <code>V = (ADC / 1023.0) * 5.0 V</code>.",
        )
        c6, self.lbl_env_val, self.lbl_env_sub = make_telemetry_card(
            "AMBIENTAL (HDC1080)",
            "--.- °C  |  --.- %",
            "Pressão: 942.5 hPa",
            "<b>Sensor Ambiental I2C ClosedCube HDC1080 (Endereço 0x40):</b><br>"
            "Conectado aos pinos <b>A4 (SDA)</b> e <b>A5 (SCL)</b> do Arduino UNO R3.<br>"
            "Monitora Temperatura (°C) e Umidade Relativa (%) em tempo real dentro da câmara.",
        )

        self.lbl_mq2_val.setStyleSheet(f"font: 700 11.5pt 'Consolas'; color: {CORES_SENSORES['MQ2']};")
        self.lbl_mq3_val.setStyleSheet(f"font: 700 11.5pt 'Consolas'; color: {CORES_SENSORES['MQ3']};")
        self.lbl_mq5_val.setStyleSheet(f"font: 700 11.5pt 'Consolas'; color: {CORES_SENSORES['MQ5']};")

        for idx, card in enumerate((c0, c1, c2, c3, c4, c5, c6)):
            cards_grid.addWidget(card, 0, idx)

        v_lay.addLayout(cards_grid)

        # Barra de progresso do Tempo Total do Ciclo
        self.cycle_progress = QProgressBar()
        self.cycle_progress.setRange(0, 190)
        self.cycle_progress.setValue(0)
        self.cycle_progress.setFormat("Progresso do Ciclo no Eixo X: %v s / %m s (%p%)")
        self.cycle_progress.setToolTip(
            "<b>Progresso do Ensaio:</b> Acompanha visualmente o preenchimento do eixo X de Tempo Total."
        )
        v_lay.addWidget(self.cycle_progress)

        return header

    def _build_left_control_panel(self) -> QScrollArea:
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)

        # --- GRUPO 1: CONEXAO ARDUINO UNO / SIMULADOR ---
        grp_conn = QGroupBox("1. CONEXÃO HARDWARE (ARDUINO UNO)")
        conn_lay = QVBoxLayout(grp_conn)
        conn_lay.setSpacing(5)

        port_row = QHBoxLayout()
        port_row.setSpacing(4)
        self.cmb_port = make_compact_combo(95)
        tip_port = (
            "<b>Porta Serial USB (COM):</b><br>"
            "Selecione a porta COM onde o Arduino UNO R3 está conectado (ex.: COM3, COM4).<br>"
            "Velocidade de comunicação do firmware: <b>115200 bps</b>."
        )
        self.btn_refresh_ports = QPushButton("Atualizar")
        self.btn_refresh_ports.setToolTip(
            "<b>Atualizar Portas USB:</b><br>Recarrega a lista de portas seriais COM disponíveis no Windows."
        )
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)

        port_row.addWidget(label_with_help("Porta:", tip_port))
        port_row.addWidget(self.cmb_port, 1)
        port_row.addWidget(self.btn_refresh_ports)
        conn_lay.addLayout(port_row)

        btn_conn_row = QHBoxLayout()
        btn_conn_row.setSpacing(4)
        self.btn_connect = QPushButton("Conectar UNO")
        self.btn_connect.setObjectName("btnAction")
        self.btn_connect.clicked.connect(self.toggle_serial_connection)
        tip_connect = (
            "<b>Conectar / Desconectar Arduino UNO R3:</b><br>"
            "Abre a comunicação serial a 115200 bps com o firmware <code>nariz_eletronico.ino</code>.<br>"
            "Ao abrir a porta, o UNO reinicia e aguarda os comandos <code>SET</code> e <code>START</code>."
        )

        self.btn_sim = QPushButton("Bancada Virtual")
        self.btn_sim.setObjectName("btnSim")
        self.btn_sim.clicked.connect(self.start_simulation_mode)
        tip_sim = (
            "<b>Modo Simulação (Bancada Virtual v0.4.3):</b><br>"
            "Permite testar todo o sistema sem o Arduino conectado.<br>"
            "Simula as 6 etapas (E0..E5) e gera curvas sintéticas realistas para Acetona, Álcool Etílico, "
            "Álcool Isopropílico e Ar Limpo a 1 Hz."
        )

        btn_conn_row.addWidget(widget_with_help(self.btn_connect, tip_connect))
        btn_conn_row.addWidget(widget_with_help(self.btn_sim, tip_sim))
        conn_lay.addLayout(btn_conn_row)
        left_layout.addWidget(grp_conn)

        # --- GRUPO 2: PARAMETROS DO ENSAIO (DIRETRIZES v0.4.3) ---
        grp_params = QGroupBox("2. DIRETRIZES DO ENSAIO (PADRÃO v0.4.3)")
        form_params = QFormLayout(grp_params)
        form_params.setSpacing(5)

        self.cmb_gas = make_compact_combo(120)
        for code in GAS_CODES_ALL:
            self.cmb_gas.addItem(GAS_LABELS_PT.get(code, f"{code} — {GAS_INFO.get(code, code)}"), code)
        self.cmb_gas.currentIndexChanged.connect(self._on_experiment_params_changed)
        tip_gas = (
            "<b>Gás / Composto Volátil Analisado (GAS_INFO v0.4.3):</b><br>"
            "• <b>A (Acetone):</b> Acetona<br>"
            "• <b>E (Ethyl Alcohol):</b> Álcool Etílico (Etanol)<br>"
            "• <b>P (Isopropyl Alcohol):</b> Álcool Isopropílico (Isopropanol)<br>"
            "• <b>AR (Clean Air):</b> Ar Limpo (ensaio de referência/branco)<br>"
            "Define o prefixo do arquivo CSV (ex.: <code>A0-R1-100.csv</code>)."
        )

        self.cmb_config = make_compact_combo(120)
        for cid in CONFIG_IDS:
            self.cmb_config.addItem(f"{cid} — {CONFIG_NAMES[cid]}", cid)
        self.cmb_config.currentIndexChanged.connect(self._on_experiment_params_changed)
        tip_cfg = (
            "<b>Configuração Geometria / Aleta da Câmara (CONFIG_NAMES v0.4.3):</b><br>"
            "• <b>0 — Default:</b> Câmara padrão sem aleta interna (referência 100% nas tabelas comparativas)<br>"
            "• <b>1 — Config V:</b> Aleta em formato V<br>"
            "• <b>2 — Config A:</b> Aleta em formato A<br>"
            "• <b>3 — Config X:</b> Aleta em formato X<br>"
            "• <b>4 — Config O:</b> Aleta em formato O<br>"
            "Define a subpasta <code>dados/&lt;config&gt;/</code> onde o CSV será salvo."
        )

        self.cmb_rep = make_compact_combo(120)
        for rep in REPETICOES:
            self.cmb_rep.addItem(f"{rep} (Repetição {rep[1:]})", rep)
        self.cmb_rep.currentIndexChanged.connect(self._on_experiment_params_changed)
        tip_rep = (
            "<b>Repetição Experimental (Triplicata v0.4.3):</b><br>"
            "Seleciona qual repetição da triplicata está sendo executada (<b>R1</b>, <b>R2</b> ou <b>R3</b>).<br>"
            "O Analisador v0.4.3 calcula a curva média e o Erro Multiplicativo (%) no pico entre R1, R2 e R3."
        )

        conc_vol_row = QHBoxLayout()
        conc_vol_row.setSpacing(4)
        self.spn_conc = QSpinBox()
        self.spn_conc.setRange(1, 100000)
        self.spn_conc.setSingleStep(50)
        self.spn_conc.setValue(100)
        self.spn_conc.setSuffix(" ppm")
        self.spn_conc.valueChanged.connect(self._on_experiment_params_changed)
        tip_conc = (
            "<b>Concentração Alvo (ppm) e Volume do Recipiente (mL):</b><br>"
            "• <b>Concentração:</b> Padrões do v0.4.3 são <b>100 ppm</b> e <b>200 ppm</b>.<br>"
            "• <b>Volume:</b> Volume da câmara/recipiente de medição (padrão v0.4.3 = <b>200 mL</b>)."
        )

        self.spn_vol = QSpinBox()
        self.spn_vol.setRange(10, 10000)
        self.spn_vol.setSingleStep(50)
        self.spn_vol.setValue(200)
        self.spn_vol.setSuffix(" mL")
        self.spn_conc.setToolTip(tip_conc)
        self.spn_vol.setToolTip(tip_conc)
        conc_vol_row.addWidget(self.spn_conc, 1)
        conc_vol_row.addWidget(QLabel("Vol:"))
        conc_vol_row.addWidget(self.spn_vol, 1)

        self.edt_operator = QLineEdit()
        self.edt_operator.setPlaceholderText("Operador / Pesquisador")
        tip_op = (
            "<b>Operador / Pesquisador:</b><br>"
            "Identificação registrada no banco de dados local SQLite junto à sessão do experimento."
        )

        self.lbl_file_preview = QLabel("dados/0/A0-R1-100.csv")
        self.lbl_file_preview.setStyleSheet("font: 700 9pt 'Consolas'; color: #34d399;")
        tip_file = (
            "<b>Caminho Automático do Arquivo CSV (Padrão v0.4.3):</b><br>"
            "Formato oficial: <code>dados/&lt;Config&gt;/&lt;Gas&gt;&lt;Config&gt;-&lt;Rep&gt;-&lt;Conc&gt;.csv</code><br>"
            "Separador <code>;</code> com colunas:<br>"
            "<code>Tempo(s);MQ2(A0);MQ3(A1);MQ5(A2);Temperatura(C);Umidade(%);Pressao(hPa)</code>"
        )

        self.chk_autosave_v043 = QCheckBox("Auto-salvar CSV padrão v0.4.3 ao concluir")
        self.chk_autosave_v043.setChecked(True)
        tip_autosave = (
            "<b>Salvamento Automático v0.4.3:</b><br>"
            "Quando marcado, assim que o Arduino envia <code>CICLO FINALIZADO</code> ao término da Etapa 5, "
            "o arquivo CSV é gravado automaticamente na pasta <code>dados/&lt;config&gt;/</code>."
        )

        form_params.addRow(label_with_help("Gás / Amostra:", tip_gas), self.cmb_gas)
        form_params.addRow(label_with_help("Aleta (Config):", tip_cfg), self.cmb_config)
        form_params.addRow(label_with_help("Repetição:", tip_rep), self.cmb_rep)
        form_params.addRow(label_with_help("Conc. / Vol.:", tip_conc), conc_vol_row)
        form_params.addRow(label_with_help("Operador:", tip_op), self.edt_operator)
        form_params.addRow(label_with_help("Arquivo Alvo:", tip_file), self.lbl_file_preview)
        form_params.addRow(widget_with_help(self.chk_autosave_v043, tip_autosave))
        left_layout.addWidget(grp_params)

        # --- GRUPO 3: TEMPORIZACAO DAS 6 ETAPAS (SET 0..5) ---
        grp_stages = QGroupBox("3. TEMPOS DAS 6 ETAPAS (ARDUINO UNO)")
        stages_lay = QVBoxLayout(grp_stages)
        stages_lay.setSpacing(5)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        btn_p_v043 = QPushButton("v0.4.3 (190s)")
        btn_p_v043.setToolTip(
            "<b>Preset Oficial de Bancada v0.4.3 (190 s total):</b><br>"
            "• E0 = 0 s (Preparação)<br>"
            "• E1 = 60 s (Baseline / Limpeza inicial)<br>"
            "• E2 = 30 s (Exposição ao gás)<br>"
            "• E3 = 30 s (Câmara fechada / Retenção)<br>"
            "• E4 = 60 s (Exaustão / Recuperação)<br>"
            "• E5 = 10 s (Finalização)"
        )
        btn_p_v043.clicked.connect(lambda: self.apply_stage_preset(DEFAULT_STAGE_DURATIONS_V043_MS))

        btn_p_ino = QPushButton("Padrão INO (50s)")
        btn_p_ino.setToolTip(
            "<b>Preset Padrão do Firmware megaPyhtonSerial.ino (50 s total):</b><br>"
            "• E0 = 0 s<br>• E1 a E5 = 10 s cada (10000 ms)."
        )
        btn_p_ino.clicked.connect(lambda: self.apply_stage_preset(DEFAULT_STAGE_DURATIONS_INO_MS))

        btn_p_fast = QPushButton("Rápido (15s)")
        btn_p_fast.setToolTip(
            "<b>Preset de Teste Rápido (15 s total):</b><br>"
            "• E0 = 0 s<br>• E1 a E5 = 3 s cada (3000 ms). Ideal para testar válvulas e gráficos rapidamente."
        )
        btn_p_fast.clicked.connect(lambda: self.apply_stage_preset(DEFAULT_STAGE_DURATIONS_FAST_MS))

        preset_row.addWidget(btn_p_v043)
        preset_row.addWidget(btn_p_ino)
        preset_row.addWidget(btn_p_fast)
        preset_row.addWidget(
            make_help_badge(
                "<b>Presets de Temporização das 6 Etapas:</b><br>"
                "Preenchem automaticamente os tempos de E0 a E5 e reajustam o Eixo X de Tempo Total do gráfico."
            )
        )
        stages_lay.addLayout(preset_row)

        grid_stages = QGridLayout()
        grid_stages.setHorizontalSpacing(6)
        grid_stages.setVerticalSpacing(4)
        self.stage_spinboxes: list[QSpinBox] = []
        stage_meta = [
            (
                "E0 — Preparação (V1=L, V2=L, V3=L, B=L):",
                "<b>Etapa 0 — Preparação Inicial:</b><br>"
                "Estado dos pinos no UNO: <code>D6(V1)=LOW, D7(V2)=LOW, D8(V3)=LOW, D9(BOMBA)=LOW</code>.<br>"
                "Tempo inicial antes de abrir o fluxo de limpeza (normalmente 0 s).",
            ),
            (
                "E1 — Baseline / Ar (V1=L, V2=H, V3=L, B=L):",
                "<b>Etapa 1 — Limpeza Inicial / Baseline (Ar Limpo):</b><br>"
                "Estado dos pinos no UNO: <code>D6(V1)=LOW, D7(V2)=HIGH, D8(V3)=LOW, D9(BOMBA)=LOW</code>.<br>"
                "Estabiliza a linha de base (<code>V_baseline</code> nos primeiros 60 s do ensaio v0.4.3).",
            ),
            (
                "E2 — Exposição Gás (V1=H, V2=L, V3=L, B=L):",
                "<b>Etapa 2 — Exposição ao Gás / Amostra:</b><br>"
                "Estado dos pinos no UNO: <code>D6(V1)=HIGH, D7(V2)=LOW, D8(V3)=LOW, D9(BOMBA)=LOW</code>.<br>"
                "Injeta o composto volátil na câmara de sensores provocando a subida do sinal.",
            ),
            (
                "E3 — Câmara Fechada (V1=H, V2=H, V3=H, B=H):",
                "<b>Etapa 3 — Câmara Fechada / Retenção:</b><br>"
                "Estado dos pinos no UNO: <code>D6(V1)=HIGH, D7(V2)=HIGH, D8(V3)=HIGH, D9(BOMBA)=HIGH</code>.<br>"
                "Mantém o gás confinado na câmara para interação com a superfície dos sensores MQ2, MQ3 e MQ5.",
            ),
            (
                "E4 — Purga / Exaustão (V1=L, V2=H, V3=H, B=H):",
                "<b>Etapa 4 — Purga / Exaustão e Recuperação:</b><br>"
                "Estado dos pinos no UNO: <code>D6(V1)=LOW, D7(V2)=HIGH, D8(V3)=HIGH, D9(BOMBA)=HIGH</code>.<br>"
                "Remove o gás da câmara permitindo a dessorção e descida da curva de tensão.",
            ),
            (
                "E5 — Final Desligado (V1=L, V2=L, V3=L, B=L):",
                "<b>Etapa 5 — Finalização / Tudo Desligado:</b><br>"
                "Estado dos pinos no UNO: <code>D6(V1)=LOW, D7(V2)=LOW, D8(V3)=LOW, D9(BOMBA)=LOW</code>.<br>"
                "Ao concluir esta etapa, o Arduino emite <code>CICLO FINALIZADO</code>.",
            ),
        ]
        for i, (desc_txt, tip_stage) in enumerate(stage_meta):
            lbl_w = label_with_help(desc_txt, tip_stage)
            spn = QSpinBox()
            spn.setRange(0, 3600)
            spn.setValue(DEFAULT_STAGE_DURATIONS_V043_MS[i] // 1000)
            spn.setSuffix(" s")
            spn.setToolTip(tip_stage)
            spn.valueChanged.connect(self._on_stage_durations_changed)
            self.stage_spinboxes.append(spn)
            grid_stages.addWidget(lbl_w, i, 0)
            grid_stages.addWidget(spn, i, 1)

        stages_lay.addLayout(grid_stages)

        self.lbl_total_planned = QLabel("Tempo Total Planejado (Eixo X): 190 s (190000 ms)")
        self.lbl_total_planned.setStyleSheet("font: 700 8.5pt 'Consolas'; color: #38bdf8;")
        stages_lay.addWidget(self.lbl_total_planned)

        cmd_stages_row = QHBoxLayout()
        cmd_stages_row.setSpacing(4)
        self.btn_send_stages = QPushButton("Enviar (SET 0..5)")
        self.btn_send_stages.setObjectName("btnAction")
        self.btn_send_stages.clicked.connect(self.send_stage_times_to_arduino)
        tip_set = (
            "<b>Enviar Tempos ao Arduino UNO (Comando SET):</b><br>"
            "Envia os 6 comandos <code>SET 0 &lt;ms&gt;</code> até <code>SET 5 &lt;ms&gt;</code> pela porta serial.<br>"
            "Nota: Os tempos também são sincronizados automaticamente ao clicar em <b>START</b>."
        )

        self.btn_show_stages = QPushButton("Consultar (SHOW)")
        self.btn_show_stages.clicked.connect(lambda: self.send_raw_command("SHOW"))
        tip_show = (
            "<b>Consultar Tempos no Arduino UNO (Comando SHOW):</b><br>"
            "Solicita ao Arduino que imprima no Terminal Serial os valores de <code>tempos[0..5]</code> "
            "atualmente gravados na memória RAM do microcontrolador."
        )

        cmd_stages_row.addWidget(widget_with_help(self.btn_send_stages, tip_set))
        cmd_stages_row.addWidget(widget_with_help(self.btn_show_stages, tip_show))
        stages_lay.addLayout(cmd_stages_row)
        left_layout.addWidget(grp_stages)

        # --- GRUPO 4: BOTOES DE COMANDO DE OPERACAO ---
        grp_ops = QGroupBox("4. COMANDO DE OPERAÇÃO DO CICLO")
        ops_lay = QVBoxLayout(grp_ops)
        ops_lay.setSpacing(6)

        self.btn_start = QPushButton("▶  START — INICIAR ENSAIO EM TEMPO REAL")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self.start_measurement)
        tip_start = (
            "<b>Iniciar Ciclo de Amostragem (Comando START):</b><br>"
            "1. Sincroniza os tempos das 6 etapas (<code>SET 0..5</code>) com o Arduino UNO.<br>"
            "2. Envia <code>START</code> para iniciar a máquina de estados no Timer1.<br>"
            "3. Plota a curva ao vivo da esquerda para a direita sobre o Tempo Total no Eixo X."
        )

        stop_reset_row = QHBoxLayout()
        stop_reset_row.setSpacing(4)
        self.btn_stop = QPushButton("■  STOP — PARAR")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.clicked.connect(self.stop_measurement)
        tip_stop = (
            "<b>Parada Imediata (Comando STOP):</b><br>"
            "Interrompe o ciclo no Arduino UNO e leva o sistema imediatamente para a <b>Etapa 5</b> "
            "(desligando válvulas e bomba)."
        )

        self.btn_reset = QPushButton("↺  RESET")
        self.btn_reset.setObjectName("btnReset")
        self.btn_reset.clicked.connect(self.reset_measurement)
        tip_reset = (
            "<b>Reiniciar Contador e Estado (Comando RESET):</b><br>"
            "Envia <code>RESET</code> ao Arduino UNO, zerando o contador de segundos (<code>secondsCounter = 0</code>) "
            "e colocando todas as saídas na Etapa 5."
        )

        stop_reset_row.addWidget(widget_with_help(self.btn_stop, tip_stop), 2)
        stop_reset_row.addWidget(widget_with_help(self.btn_reset, tip_reset), 1)

        self.btn_export_csv = QPushButton("💾  Exportar Ensaio Atual (CSV Padrão v0.4.3)")
        self.btn_export_csv.clicked.connect(self.export_current_csv)
        tip_export = (
            "<b>Exportar CSV Manualmente (Padrão v0.4.3):</b><br>"
            "Salva os dados do último ensaio em arquivo CSV delimitado por <code>;</code> com as colunas "
            "exatas exigidas pelos scripts do <code>Sistema gás/v0.4.3</code>."
        )

        ops_lay.addWidget(widget_with_help(self.btn_start, tip_start))
        ops_lay.addLayout(stop_reset_row)
        ops_lay.addWidget(widget_with_help(self.btn_export_csv, tip_export))
        left_layout.addWidget(grp_ops)

        left_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Sem setMaximumWidth para permitir redimensionar livremente no QSplitter sem bugar!
        scroll.setMinimumWidth(280)
        scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        scroll.setWidget(left_widget)
        return scroll

    # =========================================================================
    # ABA 1: AQUISICAO E GRAFICO EM TEMPO REAL (TEMPO TOTAL NO EIXO X)
    # =========================================================================
    def _build_tab_realtime(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        # Barra de controle visual do grafico em tempo real (compacta e responsiva)
        toolbar = QFrame()
        toolbar.setObjectName("telemetryCard")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(8, 5, 8, 5)
        tb_lay.setSpacing(8)

        tip_ymode = (
            "<b>Grandeza do Eixo Vertical (Eixo Y):</b><br>"
            "• <b>Tensão Absoluta (V):</b> Tensão convertida de 0.0 a 5.0 V (<code>ADC * 5.0 / 1023</code>).<br>"
            "• <b>Tensão Relativa ΔV:</b> Subtrai automaticamente a linha de base (<code>V - V_baseline</code>).<br>"
            "• <b>Leitura Bruta ADC:</b> Valor digital de 10 bits lido pelo Arduino UNO (0 a 1023).<br>"
            "• <b>Taxa de Variação dV/dt (V/s):</b> Velocidade instantânea de subida/descida do sinal."
        )
        tb_lay.addWidget(label_with_help("Eixo Y:", tip_ymode, bold=True))
        self.cmb_rt_ymode = make_compact_combo(150)
        self.cmb_rt_ymode.addItem("Tensão Absoluta (V) [0.0 – 5.0 V]", "V")
        self.cmb_rt_ymode.addItem("Tensão Relativa ΔV (V - V_base)", "REL_V")
        self.cmb_rt_ymode.addItem("Leitura Bruta ADC [0 – 1023]", "ADC")
        self.cmb_rt_ymode.addItem("Taxa de Variação dV/dt (V/s)", "RATE")
        self.cmb_rt_ymode.setToolTip(tip_ymode)
        self.cmb_rt_ymode.currentIndexChanged.connect(self.update_realtime_plots)
        tb_lay.addWidget(self.cmb_rt_ymode, 1)

        tip_smooth = (
            "<b>Janela de Suavização (Média Móvel Centrada):</b><br>"
            "• <b>1:</b> Sinal puro em tempo real sem filtro.<br>"
            "• <b>5:</b> Média móvel centrada de 5 pontos (padrão oficial do <code>AnalisadorGases v0.4.3</code>)."
        )
        tb_lay.addWidget(label_with_help("Suavização:", tip_smooth, bold=True))
        self.spn_rt_smooth = QSpinBox()
        self.spn_rt_smooth.setRange(1, 25)
        self.spn_rt_smooth.setValue(1)
        self.spn_rt_smooth.setToolTip(tip_smooth)
        self.spn_rt_smooth.valueChanged.connect(self.update_realtime_plots)
        tb_lay.addWidget(self.spn_rt_smooth)

        self.chk_rt_sensors: dict[str, QCheckBox] = {}
        for idx, s in enumerate(SENSORES):
            cb = QCheckBox(f"{s}(A{idx})")
            cb.setChecked(True)
            cb.setToolTip(f"<b>Exibir/Ocultar curva do sensor {s} (Pino A{idx})</b> no gráfico em tempo real.")
            cb.setStyleSheet(f"QCheckBox {{ color: {CORES_SENSORES[s]}; font-weight: 700; }}")
            cb.toggled.connect(self.update_realtime_plots)
            self.chk_rt_sensors[s] = cb
            tb_lay.addWidget(cb)

        self.chk_show_stages = QCheckBox("Divisões E1..E5")
        self.chk_show_stages.setChecked(True)
        tip_div = (
            "<b>Faixas de Etapas no Gráfico:</b><br>"
            "Mostra as regiões coloridas de E1 (Baseline), E2 (Exposição), E3 (Retenção), E4 (Purga) e E5 (Final) "
            "ao longo do Tempo Total do Ciclo no Eixo X."
        )
        self.chk_show_stages.toggled.connect(self._rebuild_stage_overlays)
        tb_lay.addWidget(widget_with_help(self.chk_show_stages, tip_div, stretch=0))

        btn_clear_rt = QPushButton("Limpar")
        btn_clear_rt.setToolTip("<b>Limpar Gráfico:</b> Zera os pontos visuais da tela sem apagar os ensaios já salvos.")
        btn_clear_rt.clicked.connect(self.clear_realtime_buffers)
        tb_lay.addWidget(btn_clear_rt)
        lay.addWidget(toolbar, 0)

        # SPLITTER VERTICAL DE 3 NIVEIS:
        # 1. Grafico Sensores MQ2/MQ3/MQ5
        # 2. Grafico Ambiental HDC1080
        # 3. Painel Inferior (Tabela de Metricas <-> Terminal Serial)
        self.rt_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.rt_v_splitter.setHandleWidth(8)
        self.rt_v_splitter.setChildrenCollapsible(False)
        self.rt_v_splitter.setOpaqueResize(True)
        lay.addWidget(self.rt_v_splitter, 1)

        # Grafico 1: Sensores de Gas MQ2, MQ3, MQ5 ao longo do Tempo Total
        self.rt_gas_plot = pg.PlotWidget(
            title="Formação da Resposta em Tempo Real — Sensores MQ2 (A0), MQ3 (A1), MQ5 (A2)"
        )
        self.rt_gas_plot.setMinimumHeight(130)
        self.rt_gas_plot.setBackground("#090e17")
        self.rt_gas_plot.showGrid(x=True, y=True, alpha=0.22)
        self.rt_gas_plot.setLabel("bottom", "Tempo Total do Ciclo", units="s")
        self.rt_gas_plot.setLabel("left", "Tensão (V)")
        self.rt_gas_plot.addLegend(offset=(12, 10))

        self.rt_curves: dict[str, pg.PlotDataItem] = {}
        self.rt_heads: dict[str, pg.ScatterPlotItem] = {}
        for idx, s in enumerate(SENSORES):
            color = CORES_SENSORES[s]
            curve = self.rt_gas_plot.plot(
                [],
                [],
                pen=pg.mkPen(color, width=2.6),
                name=f"{s} (A{idx})",
            )
            head = pg.ScatterPlotItem(
                size=10,
                brush=pg.mkBrush(color),
                pen=pg.mkPen("#ffffff", width=1.5),
            )
            self.rt_gas_plot.addItem(head)
            self.rt_curves[s] = curve
            self.rt_heads[s] = head

        # Cursor vertical indicando o instante atual de leitura no eixo de Tempo Total
        self.rt_cursor_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen("#f8fafc", width=1.5, style=Qt.PenStyle.DashLine),
        )
        self.rt_gas_plot.addItem(self.rt_cursor_line)
        self.rt_v_splitter.addWidget(self.rt_gas_plot)

        # Grafico 2: Ambiental (Temperatura e Umidade) sincronizado no mesmo Eixo X de Tempo Total
        self.rt_env_plot = pg.PlotWidget(
            title="Monitoramento Ambiental Sincronizado — HDC1080 (Temperatura °C e Umidade %)"
        )
        self.rt_env_plot.setMinimumHeight(85)
        self.rt_env_plot.setBackground("#090e17")
        self.rt_env_plot.showGrid(x=True, y=True, alpha=0.22)
        self.rt_env_plot.setLabel("bottom", "Tempo Total do Ciclo", units="s")
        self.rt_env_plot.setLabel("left", "Temp (°C) / Umid (%)")
        self.rt_env_plot.addLegend(offset=(12, 8))
        self.rt_env_plot.setXLink(self.rt_gas_plot)

        self.rt_temp_curve = self.rt_env_plot.plot(
            [], [], pen=pg.mkPen("#ef4444", width=2.2), name="Temperatura (°C)"
        )
        self.rt_hum_curve = self.rt_env_plot.plot(
            [], [], pen=pg.mkPen("#38bdf8", width=2.2, style=Qt.PenStyle.DotLine), name="Umidade (%)"
        )
        self.rt_v_splitter.addWidget(self.rt_env_plot)

        # Painel inferior com SPLITTER HORIZONTAL: Tabela de Metricas <-> Terminal Serial
        self.rt_bottom_h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.rt_bottom_h_splitter.setHandleWidth(8)
        self.rt_bottom_h_splitter.setChildrenCollapsible(False)
        self.rt_bottom_h_splitter.setOpaqueResize(True)
        self.rt_bottom_h_splitter.setMinimumHeight(105)

        # Tabela de metricas ao vivo (diretrizes v0.4.3)
        grp_metrics = QGroupBox("MÉTRICAS CIENTÍFICAS EM TEMPO REAL (DIRETRIZES v0.4.3)")
        grp_metrics.setMinimumWidth(240)
        m_lay = QVBoxLayout(grp_metrics)
        m_lay.setContentsMargins(6, 8, 6, 6)
        self.tbl_rt_metrics = QTableWidget(3, 8)
        rt_headers = [
            ("Sensor", "Canal do sensor MOS no Arduino UNO: MQ2(A0), MQ3(A1), MQ5(A2)."),
            ("ADC Atual", "Última leitura digital bruta de 10 bits (0 a 1023)."),
            ("V Atual (V)", "Tensão instantânea atual convertida: V = (ADC / 1023.0) * 5.0."),
            ("V_baseline (V)", "Tensão mínima de linha de base medida durante a Etapa 1 (Baseline)."),
            ("V_max Abs (V)", "Pico máximo absoluto de tensão (V) atingido pelo sensor no ciclo."),
            ("ΔV Relativo (V)", "Amplitude máxima de resposta relativa à baseline: ΔV = V_max - V_baseline."),
            ("Taxa Max (V/s)", "Derivada máxima de subida max(dV/dt) em Volts por segundo (np.gradient)."),
            ("AUC (V·s)", "Área sob a curva relativa à baseline integrada por trapézios (Volts × segundo)."),
        ]
        self.tbl_rt_metrics.setHorizontalHeaderLabels([h[0] for h in rt_headers])
        for col_idx, (_, col_tip) in enumerate(rt_headers):
            item_h = self.tbl_rt_metrics.horizontalHeaderItem(col_idx)
            if item_h is not None:
                item_h.setToolTip(f"<b>{rt_headers[col_idx][0]}:</b><br>{col_tip}")
        self.tbl_rt_metrics.verticalHeader().setVisible(False)
        self.tbl_rt_metrics.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_rt_metrics.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for i, s in enumerate(SENSORES):
            self.tbl_rt_metrics.setItem(i, 0, QTableWidgetItem(f"{s} (A{i})"))
        m_lay.addWidget(self.tbl_rt_metrics)
        self.rt_bottom_h_splitter.addWidget(grp_metrics)

        # Terminal Serial e Log de Eventos (sem '&' simples para nao virar sublinhado)
        grp_log = QGroupBox("TERMINAL SERIAL + LOG DE EVENTOS (115200 BPS)")
        grp_log.setMinimumWidth(200)
        log_lay = QVBoxLayout(grp_log)
        log_lay.setContentsMargins(6, 8, 6, 6)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(600)
        self.txt_log.setStyleSheet("font: 8.5pt 'Consolas', monospace;")
        self.txt_log.setToolTip(
            "<b>Console Serial / Log de Eventos:</b><br>"
            "Registra todas as mensagens enviadas e recebidas do Arduino UNO R3 (mudanças de etapa, "
            "respostas de <code>SHOW</code> e <code>SET</code>, início/fim de ciclo e salvamento CSV)."
        )
        log_lay.addWidget(self.txt_log)

        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(4)
        self.edt_manual_cmd = QLineEdit()
        self.edt_manual_cmd.setPlaceholderText("Comando serial (ex.: SHOW, SET 1 60000, START, STOP, RESET)")
        self.edt_manual_cmd.returnPressed.connect(self._send_manual_command)
        tip_manual = (
            "<b>Envio de Comando Serial Direto:</b><br>"
            "Comandos aceitos pelo firmware <code>nariz_eletronico.ino</code>:<br>"
            "• <code>START</code> — Inicia o ciclo na Etapa 0<br>"
            "• <code>STOP</code> — Para o ciclo e desliga saídas (Etapa 5)<br>"
            "• <code>RESET</code> — Reinicia estado e zera tempo<br>"
            "• <code>SHOW</code> — Lista os tempos das Etapas 0..5 em ms<br>"
            "• <code>SET &lt;etapa&gt; &lt;tempo_ms&gt;</code> — Altera a duração da etapa 0..5"
        )
        btn_send_cmd = QPushButton("Enviar")
        btn_send_cmd.clicked.connect(self._send_manual_command)
        cmd_row.addWidget(self.edt_manual_cmd, 1)
        cmd_row.addWidget(widget_with_help(btn_send_cmd, tip_manual, stretch=0))
        log_lay.addLayout(cmd_row)
        self.rt_bottom_h_splitter.addWidget(grp_log)

        self.rt_v_splitter.addWidget(self.rt_bottom_h_splitter)
        self.rt_v_splitter.setStretchFactor(0, 4)
        self.rt_v_splitter.setStretchFactor(1, 2)
        self.rt_v_splitter.setStretchFactor(2, 2)
        return tab

    # =========================================================================
    # ABA 2: ANALISADOR DETALHADO v0.4.3 (REPETICOES R1..R3, ALETAS, GASES)
    # =========================================================================
    def _build_tab_analyzer(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        # Barra de filtros em 2 linhas (QGridLayout) para nunca estourar a largura minima da janela
        filter_bar = QFrame()
        filter_bar.setObjectName("telemetryCard")
        fb_grid = QGridLayout(filter_bar)
        fb_grid.setContentsMargins(8, 6, 8, 6)
        fb_grid.setHorizontalSpacing(8)
        fb_grid.setVerticalSpacing(5)

        # Linha 0: Pasta de dados v0.4.3 + Modo de Visualizacao + Botao Processar
        tip_dir = (
            "<b>Diretório Raiz de Dados (Padrão v0.4.3):</b><br>"
            "Pasta contendo as subpastas <code>0/</code>, <code>1/</code>, <code>2/</code>, <code>3/</code>, <code>4/</code> "
            "com os arquivos CSV (ex.: <code>Sistema gás/v0.4.3/dados</code> ou a pasta local <code>./dados</code>)."
        )
        fb_grid.addWidget(label_with_help("Pasta v0.4.3:", tip_dir, bold=True), 0, 0)
        self.edt_data_dir = QLineEdit(str(self.v043_data_dir))
        self.edt_data_dir.setMinimumWidth(120)
        self.edt_data_dir.setToolTip(tip_dir)
        fb_grid.addWidget(self.edt_data_dir, 0, 1, 1, 2)

        btn_browse = QPushButton("Procurar...")
        btn_browse.setToolTip("Selecionar outra pasta de dados CSV do padrão v0.4.3.")
        btn_browse.clicked.connect(self.browse_v043_data_dir)
        fb_grid.addWidget(btn_browse, 0, 3)

        tip_ana_mode = (
            "<b>Modo de Análise Científica (MainTodosJunto.py v0.4.3):</b><br>"
            "• <b>1. Repetições (Tensão V):</b> Plota R1, R2, R3 e a curva Média em Volts.<br>"
            "• <b>2. Repetições (ΔV Relativa):</b> Plota R1, R2, R3 e Média descontando o valor mínimo inicial.<br>"
            "• <b>3. Comparativo de Aletas (Configs 0..4):</b> Sobrepõe Default, Config V, A, X e O.<br>"
            "• <b>4. Comparativo de Gases (A, E, P, AR):</b> Sobrepõe Acetona, Etanol, Isopropanol e Ar.<br>"
            "• <b>5. Taxa de Variação / Derivada (V/s):</b> Plota dV/dt para análise cinética.<br>"
            "• <b>6. Ambiental:</b> Plota Temperatura (°C) e Umidade (%) do ensaio."
        )
        fb_grid.addWidget(label_with_help("Modo:", tip_ana_mode, bold=True), 0, 4)
        self.cmb_ana_mode = make_compact_combo(160)
        self.cmb_ana_mode.addItem("1. Repetições (R1, R2, R3 + Média) — Tensão (V)", "REP_V")
        self.cmb_ana_mode.addItem("2. Repetições (R1, R2, R3 + Média) — ΔV Relativa", "REP_REL")
        self.cmb_ana_mode.addItem("3. Comparativo de Aletas (Configs 0..4) — ΔV", "COMP_ALETAS")
        self.cmb_ana_mode.addItem("4. Comparativo de Gases (A, E, P, AR) — ΔV", "COMP_GASES")
        self.cmb_ana_mode.addItem("5. Taxa de Variação / Derivada (V/s)", "DERIVADA")
        self.cmb_ana_mode.addItem("6. Ambiental (Temperatura e Umidade)", "AMBIENTAL")
        self.cmb_ana_mode.setToolTip(tip_ana_mode)
        self.cmb_ana_mode.currentIndexChanged.connect(self.refresh_v043_analysis)
        fb_grid.addWidget(self.cmb_ana_mode, 0, 5, 1, 2)

        btn_refresh_ana = QPushButton("🔄 Processar Dados")
        btn_refresh_ana.setObjectName("btnAction")
        btn_refresh_ana.setToolTip("Recarrega os arquivos CSV da pasta e recalcula todos os gráficos e métricas.")
        btn_refresh_ana.clicked.connect(self.refresh_v043_analysis)
        fb_grid.addWidget(btn_refresh_ana, 0, 7)

        # Linha 1: Gas, Aleta, Concentracao, Sensor, Janela
        tip_f_gas = "<b>Filtro de Gás:</b> Seleciona o composto (A=Acetona, E=Etanol, P=Isopropanol, AR=Ar Limpo)."
        fb_grid.addWidget(label_with_help("Gás:", tip_f_gas, bold=True), 1, 0)
        self.cmb_ana_gas = make_compact_combo(100)
        for g in GAS_CODES_ALL:
            self.cmb_ana_gas.addItem(f"{g} ({GAS_INFO[g]})", g)
        self.cmb_ana_gas.setToolTip(tip_f_gas)
        self.cmb_ana_gas.currentIndexChanged.connect(self.refresh_v043_analysis)
        fb_grid.addWidget(self.cmb_ana_gas, 1, 1)

        tip_f_cfg = "<b>Filtro de Aleta / Configuração:</b> Seleciona a geometria da câmara (0=Default a 4=Config O)."
        fb_grid.addWidget(label_with_help("Aleta:", tip_f_cfg, bold=True), 1, 2)
        self.cmb_ana_cfg = make_compact_combo(95)
        for cid in CONFIG_IDS:
            self.cmb_ana_cfg.addItem(f"{cid} - {CONFIG_NAMES[cid]}", cid)
        self.cmb_ana_cfg.setToolTip(tip_f_cfg)
        self.cmb_ana_cfg.currentIndexChanged.connect(self.refresh_v043_analysis)
        fb_grid.addWidget(self.cmb_ana_cfg, 1, 3)

        tip_f_conc = "<b>Filtro de Concentração:</b> Filtra os arquivos CSV pelo sufixo de concentração (100 ou 200 ppm)."
        fb_grid.addWidget(label_with_help("Conc.:", tip_f_conc, bold=True), 1, 4)
        self.cmb_ana_conc = make_compact_combo(80)
        for c in CONCENTRACOES:
            self.cmb_ana_conc.addItem(f"{c} ppm", c)
        self.cmb_ana_conc.setToolTip(tip_f_conc)
        self.cmb_ana_conc.currentIndexChanged.connect(self.refresh_v043_analysis)
        fb_grid.addWidget(self.cmb_ana_conc, 1, 5)

        tip_f_sen = "<b>Filtro de Sensor:</b> Exibe todos os 3 sensores simultaneamente ou foca em MQ2, MQ3 ou MQ5."
        fb_grid.addWidget(label_with_help("Sensor:", tip_f_sen, bold=True), 1, 6)
        sensor_win_box = QHBoxLayout()
        sensor_win_box.setContentsMargins(0, 0, 0, 0)
        sensor_win_box.setSpacing(4)
        self.cmb_ana_sensor = make_compact_combo(95)
        self.cmb_ana_sensor.addItem("TODOS (MQ2/3/5)", "TODOS")
        for s in SENSORES:
            self.cmb_ana_sensor.addItem(s, s)
        self.cmb_ana_sensor.setToolTip(tip_f_sen)
        self.cmb_ana_sensor.currentIndexChanged.connect(self.refresh_v043_analysis)

        tip_f_win = "<b>Janela da Média Móvel (Suavização v0.4.3):</b> Padrão = 5 pontos centrados."
        self.spn_ana_window = QSpinBox()
        self.spn_ana_window.setRange(1, 31)
        self.spn_ana_window.setValue(5)
        self.spn_ana_window.setPrefix("Jan: ")
        self.spn_ana_window.setToolTip(tip_f_win)
        self.spn_ana_window.valueChanged.connect(self.refresh_v043_analysis)

        sensor_win_box.addWidget(self.cmb_ana_sensor, 1)
        sensor_win_box.addWidget(self.spn_ana_window, 0)
        fb_grid.addLayout(sensor_win_box, 1, 7)

        lay.addWidget(filter_bar, 0)

        # Splitter Vertical: Grafico Principal (topo) <-> Tabela de Metricas Avancadas (base)
        self.ana_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.ana_v_splitter.setHandleWidth(8)
        self.ana_v_splitter.setChildrenCollapsible(False)
        self.ana_v_splitter.setOpaqueResize(True)
        lay.addWidget(self.ana_v_splitter, 1)

        self.ana_plot = pg.PlotWidget(title="Analisador de Dados do Nariz Eletrônico v0.4.3")
        self.ana_plot.setMinimumHeight(160)
        self.ana_plot.setBackground("#090e17")
        self.ana_plot.showGrid(x=True, y=True, alpha=0.25)
        self.ana_plot.addLegend(offset=(14, 14))
        self.ana_v_splitter.addWidget(self.ana_plot)

        # Tabela de Metricas Avancadas do v0.4.3
        grp_ana_tbl = QGroupBox("TABELA DE MÉTRICAS AVANÇADAS (AnalisadorGases v0.4.3)")
        grp_ana_tbl.setMinimumHeight(105)
        tbl_lay = QVBoxLayout(grp_ana_tbl)
        tbl_lay.setContentsMargins(6, 8, 6, 6)
        self.tbl_ana_metrics = QTableWidget(0, 11)
        ana_headers = [
            ("Gas", "Composto analisado (Ethyl Alcohol, Isopropyl Alcohol, Acetone, Clean Air)."),
            ("Config", "Configuração de aleta da câmara (Default, Config V, Config A, Config X, Config O)."),
            ("Sensor", "Sensor avaliado (MQ2, MQ3 ou MQ5)."),
            ("V_baseline (V)", "Tensão mínima na fase de limpeza/baseline (t ≤ 60 s)."),
            ("V_max Abs (V)", "Tensão máxima absoluta atingida na curva média (V)."),
            ("V_max Relativo (V)", "Diferencial máximo de tensão: ΔV = V_max Abs - V_baseline (V)."),
            ("Tempo V_max (s)", "Instante de tempo (s) em que ocorreu o pico máximo V_max."),
            ("Taxa Max (V/s)", "Velocidade máxima de resposta max(dV/dt) calculada via np.gradient."),
            ("Tempo Subida (s)", "Tempo de resposta entre 10% e 90% da amplitude diferencial ΔV."),
            ("Tempo Descida (s)", "Tempo de recuperação pós-pico entre 90% e 10% da amplitude ΔV."),
            ("Erro Mult. (%)", "Desvio padrão relativo (%) entre as repetições R1, R2 e R3 no instante de pico."),
        ]
        self.tbl_ana_metrics.setHorizontalHeaderLabels([h[0] for h in ana_headers])
        for col_idx, (h_title, h_tip) in enumerate(ana_headers):
            item_h = self.tbl_ana_metrics.horizontalHeaderItem(col_idx)
            if item_h is not None:
                item_h.setToolTip(f"<b>{h_title}:</b><br>{h_tip}")
        self.tbl_ana_metrics.verticalHeader().setVisible(False)
        self.tbl_ana_metrics.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_ana_metrics.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl_lay.addWidget(self.tbl_ana_metrics)
        self.ana_v_splitter.addWidget(grp_ana_tbl)
        self.ana_v_splitter.setStretchFactor(0, 4)
        self.ana_v_splitter.setStretchFactor(1, 2)

        return tab

    # =========================================================================
    # ABA 3: MATRIZ 3x3 (GASES x SENSORES) + MATRIZES COMPARATIVAS (% vs DEFAULT)
    # =========================================================================
    def _build_tab_matrix3x3(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        # Controles da Matriz 3x3 em grade compacta para redimensionamento livre
        ctrl_bar = QFrame()
        ctrl_bar.setObjectName("telemetryCard")
        cb_grid = QGridLayout(ctrl_bar)
        cb_grid.setContentsMargins(8, 5, 8, 5)
        cb_grid.setHorizontalSpacing(8)
        cb_grid.setVerticalSpacing(4)

        tip_m3_mode = (
            "<b>Modo da Matriz 3×3 (mainGraficos3por3.py / mainGraficosQuadrados.py):</b><br>"
            "Cruza os 3 Gases (<b>Ethyl Alcohol, Isopropyl Alcohol, Acetone</b>) nas linhas com os "
            "3 Sensores (<b>MQ2, MQ3, MQ5</b>) nas colunas:<br>"
            "• <b>1. Tensão Absoluta (V):</b> Repetições R1, R2, R3 + Média para a aleta selecionada.<br>"
            "• <b>2. Tensão Relativa (ΔV):</b> Desconta a baseline inicial.<br>"
            "• <b>3. Comparativo de Todas as Aletas:</b> Sobrepõe Default, Config V, A, X e O em cada célula.<br>"
            "• <b>4. Taxa de Variação / Derivada (V/s):</b> Cinética dV/dt nos 9 gráficos."
        )
        cb_grid.addWidget(label_with_help("Visão Matriz 3×3:", tip_m3_mode, bold=True), 0, 0)
        self.cmb_m3_mode = make_compact_combo(180)
        self.cmb_m3_mode.addItem("1. Tensão Absoluta (V) — Repetições R1..R3 + Média", "ABS_V")
        self.cmb_m3_mode.addItem("2. Tensão Relativa (ΔV) — Repetições R1..R3 + Média", "REL_V")
        self.cmb_m3_mode.addItem("3. Comparativo de Todas as Aletas (Default, V, A, X, O) — ΔV", "ALETAS")
        self.cmb_m3_mode.addItem("4. Taxa de Variação / Derivada (V/s)", "DERIV")
        self.cmb_m3_mode.setToolTip(tip_m3_mode)
        self.cmb_m3_mode.currentIndexChanged.connect(self.refresh_matrix_3x3)
        cb_grid.addWidget(self.cmb_m3_mode, 0, 1)

        tip_m3_cfg = "<b>Aleta selecionada:</b> Usada nos modos 1, 2 e 4 da Matriz 3×3."
        cb_grid.addWidget(label_with_help("Aleta:", tip_m3_cfg, bold=True), 0, 2)
        self.cmb_m3_cfg = make_compact_combo(95)
        for cid in CONFIG_IDS:
            self.cmb_m3_cfg.addItem(f"{cid} - {CONFIG_NAMES[cid]}", cid)
        self.cmb_m3_cfg.setToolTip(tip_m3_cfg)
        self.cmb_m3_cfg.currentIndexChanged.connect(self.refresh_matrix_3x3)
        cb_grid.addWidget(self.cmb_m3_cfg, 0, 3)

        tip_m3_conc = "<b>Concentração da Matriz 3×3 e das Tabelas Comparativas:</b> 100 ppm ou 200 ppm."
        cb_grid.addWidget(label_with_help("Conc.:", tip_m3_conc, bold=True), 0, 4)
        self.cmb_m3_conc = make_compact_combo(80)
        for c in CONCENTRACOES:
            self.cmb_m3_conc.addItem(f"{c} ppm", c)
        self.cmb_m3_conc.setToolTip(tip_m3_conc)
        self.cmb_m3_conc.currentIndexChanged.connect(self.refresh_matrix_3x3)
        cb_grid.addWidget(self.cmb_m3_conc, 0, 5)

        btn_gen_m3 = QPushButton("🔄 Atualizar Matriz")
        btn_gen_m3.setObjectName("btnAction")
        btn_gen_m3.setToolTip("Recalcula os 9 gráficos da Matriz 3×3 e as 3 Tabelas Comparativas (% vs Default).")
        btn_gen_m3.clicked.connect(self.refresh_matrix_3x3)
        cb_grid.addWidget(btn_gen_m3, 0, 6)

        btn_exp_matrix = QPushButton("💾 Exportar Matriz CSV")
        btn_exp_matrix.setToolTip("Exporta a tabela pivô completa (Config × Sensor × Gás) para arquivo CSV.")
        btn_exp_matrix.clicked.connect(self.export_full_matrix_csv)
        cb_grid.addWidget(btn_exp_matrix, 0, 7)
        cb_grid.setColumnStretch(1, 1)
        lay.addWidget(ctrl_bar, 0)

        self.m3_v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.m3_v_splitter.setHandleWidth(8)
        self.m3_v_splitter.setChildrenCollapsible(False)
        self.m3_v_splitter.setOpaqueResize(True)
        lay.addWidget(self.m3_v_splitter, 1)

        # Grade 3x3 de Graficos (3 Gases: E, P, A x 3 Sensores: MQ2, MQ3, MQ5)
        grid_frame = QFrame()
        grid_frame.setMinimumHeight(190)
        grid_lay = QGridLayout(grid_frame)
        grid_lay.setContentsMargins(2, 2, 2, 2)
        grid_lay.setSpacing(4)

        self.plots_3x3: dict[tuple[str, str], pg.PlotWidget] = {}
        for i, gas_code in enumerate(GAS_CODES_3X3):
            for j, sensor in enumerate(SENSORES):
                pw = pg.PlotWidget(title=f"{GAS_INFO[gas_code]}  •  {sensor}")
                pw.setBackground("#090e17")
                pw.showGrid(x=True, y=True, alpha=0.2)
                if i == 2:
                    pw.setLabel("bottom", "Tempo (s)")
                if j == 0:
                    pw.setLabel("left", GAS_INFO[gas_code])
                grid_lay.addWidget(pw, i, j)
                self.plots_3x3[(gas_code, sensor)] = pw

        self.m3_v_splitter.addWidget(grid_frame)

        # Matrizes Comparativas por Sensor (Aba 14 do MainTodosJunto.py: Vmax Relativo e % vs Default)
        grp_comp = QGroupBox("MATRIZES DE COMPARAÇÃO POR SENSOR — Vmax Relativo (V) e Eficiência (% vs Default)")
        grp_comp.setMinimumHeight(105)
        comp_lay = QHBoxLayout(grp_comp)
        comp_lay.setContentsMargins(6, 8, 6, 6)
        self.tbl_comp_by_sensor: dict[str, QTableWidget] = {}
        tip_comp_tbl = (
            "<b>Matriz Comparativa de Eficiência das Aletas (% vs Default):</b><br>"
            "Mostra o <code>V_max Relativo (V)</code> de cada configuração de aleta e sua porcentagem "
            "em relação à câmara sem aleta (<code>Default = 100.0%</code>).<br>"
            "Valores acima de 100% indicam que a aleta aumentou a resposta do sensor para aquele gás."
        )
        for s in SENSORES:
            sub_box = QVBoxLayout()
            sub_box.addWidget(
                label_with_help(
                    f"Matriz Comparativa — {s}",
                    tip_comp_tbl,
                    bold=True,
                )
            )
            tbl = QTableWidget(0, 6)
            tbl.setHorizontalHeaderLabels(["Gas", "Default", "Config V", "Config A", "Config X", "Config O"])
            tbl.setToolTip(tip_comp_tbl)
            tbl.verticalHeader().setVisible(False)
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            sub_box.addWidget(tbl)
            comp_lay.addLayout(sub_box)
            self.tbl_comp_by_sensor[s] = tbl

        self.m3_v_splitter.addWidget(grp_comp)
        self.m3_v_splitter.setStretchFactor(0, 4)
        self.m3_v_splitter.setStretchFactor(1, 2)
        return tab

    # =========================================================================
    # SISTEMA DE AUTO-UPDATE (GITHUB RELEASES + MODO OFFLINE TOLERANTE)
    # =========================================================================
    def check_for_updates(self, manual: bool = False):
        if self.update_worker is not None and self.update_worker.isRunning():
            return
        self.btn_check_update.setText("🔄 Verificando GitHub...")
        self.update_worker = UpdateCheckWorker(self.local_version, manual=manual)
        self.update_worker.finished_check.connect(self._on_update_check_finished)
        self.update_worker.start()

    def _on_update_button_clicked(self):
        if self.latest_update_info and self.latest_update_info.get("status") == "update_available":
            dlg = UpdateDialog(self.latest_update_info, self)
            dlg.exec()
        else:
            self.check_for_updates(manual=True)

    def _on_update_check_finished(self, result: dict):
        status = result.get("status")
        manual = bool(result.get("manual"))
        msg = str(result.get("message", ""))

        if status == "update_available":
            self.latest_update_info = result
            r_ver = result.get("remote_version")
            self.btn_check_update.setText(f"⬇ Atualizar para v{r_ver}")
            self.btn_check_update.setObjectName("btnUpdateReady")
            self.btn_check_update.style().unpolish(self.btn_check_update)
            self.btn_check_update.style().polish(self.btn_check_update)
            self.log(f"AUTO-UPDATE >> {msg}")
            self.statusBar().showMessage(f"🔔 {msg} — Clique em 'Atualizar para v{r_ver}' no topo para instalar.")
            dlg = UpdateDialog(result, self)
            dlg.exec()

        elif status == "offline":
            self.latest_update_info = None
            self.btn_check_update.setText(f"⚠ Offline (v{self.local_version})")
            self.log(f"AUTO-UPDATE >> {msg}")
            self.statusBar().showMessage(f"⚠ {msg}")
            if manual:
                QMessageBox.information(
                    self,
                    "Sem Acesso à Internet (Modo Offline Ativo)",
                    f"{msg}\n\nVocê pode utilizar todas as funções de controle do Arduino UNO, "
                    f"gráficos em tempo real e analisadores locais sem nenhuma restrição.",
                )

        else:
            self.latest_update_info = None
            self.btn_check_update.setText(f"✓ Atualizado (v{self.local_version})")
            self.log(f"AUTO-UPDATE >> {msg}")
            if manual:
                QMessageBox.information(
                    self,
                    "Sistema Atualizado",
                    f"Você já está utilizando a versão mais recente (v{self.local_version}).\n\n"
                    f"Repositório oficial: {GITHUB_REPO_URL}",
                )

    # =========================================================================
    # LOGICA DE CONTROLE, CONEXAO E TEMPORIZACAO DAS ETAPAS
    # =========================================================================
    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_log.appendPlainText(f"[{ts}] {message}")

    def get_planned_stage_durations_ms(self) -> list[int]:
        return [spn.value() * 1000 for spn in self.stage_spinboxes]

    def get_planned_total_seconds(self) -> int:
        total_s = sum(spn.value() for spn in self.stage_spinboxes)
        return max(10, total_s)

    def apply_stage_preset(self, durations_ms: list[int]):
        for i, ms in enumerate(durations_ms[:6]):
            self.stage_spinboxes[i].blockSignals(True)
            self.stage_spinboxes[i].setValue(ms // 1000)
            self.stage_spinboxes[i].blockSignals(False)
        self._on_stage_durations_changed()
        self.log(f"Preset de etapas carregado: {[d // 1000 for d in durations_ms]} s")

    def _on_stage_durations_changed(self):
        total_s = sum(spn.value() for spn in self.stage_spinboxes)
        self.lbl_total_planned.setText(f"Tempo Total Planejado (Eixo X): {total_s} s ({total_s * 1000} ms)")
        self.cycle_progress.setRange(0, max(1, total_s))
        self._rebuild_stage_overlays()

    def _on_experiment_params_changed(self):
        self._update_file_preview()
        if isinstance(self.worker, SimulationWorker):
            self.worker.set_gas_profile(self.cmb_gas.currentData())

    def _update_file_preview(self):
        gas = self.cmb_gas.currentData() or "A"
        cfg = self.cmb_config.currentData()
        if cfg is None:
            cfg = 0
        rep = self.cmb_rep.currentData() or "R1"
        conc = self.spn_conc.value()
        fname = format_v043_filename(gas, cfg, rep, conc)
        self.lbl_file_preview.setText(f"dados/{cfg}/{fname}")

    def _rebuild_stage_overlays(self):
        """Desenha as faixas das Etapas E0..E5 e ajusta o Eixo X para o Tempo Total do Ciclo."""
        for reg in self.stage_regions:
            self.rt_gas_plot.removeItem(reg)
        for ln in self.stage_lines:
            self.rt_gas_plot.removeItem(ln)
        self.stage_regions.clear()
        self.stage_lines.clear()

        total_planned_s = self.get_planned_total_seconds()
        max_x = max(total_planned_s, int(self.rt_times[-1]) + 2 if self.rt_times else total_planned_s)
        self.rt_gas_plot.setXRange(0, max_x, padding=0.01)

        if not self.chk_show_stages.isChecked():
            return

        t_cursor = 0.0
        for stage_idx, spn in enumerate(self.stage_spinboxes):
            dur_s = float(spn.value())
            if dur_s <= 0:
                continue
            t_next = t_cursor + dur_s
            rgba = STAGE_SHADE_COLORS.get(stage_idx, (148, 163, 184, 15))
            region = pg.LinearRegionItem(
                values=(t_cursor, t_next),
                brush=pg.mkBrush(*rgba),
                pen=pg.mkPen(None),
                movable=False,
            )
            region.setZValue(-10)
            self.rt_gas_plot.addItem(region)
            self.stage_regions.append(region)

            line = pg.InfiniteLine(
                pos=t_cursor,
                angle=90,
                pen=pg.mkPen("#334155", width=1, style=Qt.PenStyle.DotLine),
                label=STAGE_SHORT_NAMES.get(stage_idx, f"E{stage_idx}"),
                labelOpts={"position": 0.93, "color": "#94a3b8"},
            )
            self.rt_gas_plot.addItem(line)
            self.stage_lines.append(line)
            t_cursor = t_next

    def refresh_ports(self):
        current = self.cmb_port.currentText()
        self.cmb_port.clear()
        ports = [p.device for p in list_ports.comports()]
        self.cmb_port.addItems(ports)
        if current in ports:
            self.cmb_port.setCurrentText(current)
        if not ports:
            self.cmb_port.addItem("(nenhuma porta USB)")

    def toggle_serial_connection(self):
        if self.worker:
            self.disconnect_device()
            return
        port_txt = self.cmb_port.currentText()
        if not port_txt or port_txt.startswith("("):
            QMessageBox.warning(
                self,
                "Porta Serial Indisponível",
                "Conecte o Arduino UNO na USB e clique em 'Atualizar', ou use a 'Bancada Virtual'.",
            )
            return
        self.mode = "SERIAL"
        self._attach_worker(SerialWorker(port_txt))

    def start_simulation_mode(self):
        if self.worker:
            self.disconnect_device()
        self.mode = "SIMULACAO"
        gas = self.cmb_gas.currentData() or "A"
        self._attach_worker(SimulationWorker(gas_code=gas))

    def _attach_worker(self, worker):
        self.worker = worker
        worker.connected.connect(lambda src=worker: self._on_connected(src))
        worker.received.connect(lambda data, src=worker: self._on_worker_message(data) if src is self.worker else None)
        worker.disconnected.connect(lambda reason, src=worker: self._on_disconnected(reason, src))
        self.lbl_conn_val.setText("CONECTANDO...")
        self.lbl_conn_val.setStyleSheet("font: 700 11.5pt 'Consolas'; color: #f59e0b;")
        self._set_ui_state()
        worker.start()

    def _on_connected(self, source=None):
        if source is not None and source is not self.worker:
            return
        self.online = True
        if self.mode == "SIMULACAO":
            self.lbl_conn_val.setText("SIMULADOR UNO")
            self.lbl_conn_sub.setText("Bancada Virtual v0.4.3")
            self.lbl_conn_val.setStyleSheet("font: 700 11.5pt 'Consolas'; color: #a855f7;")
        else:
            self.lbl_conn_val.setText(f"UNO ({self.cmb_port.currentText()})")
            self.lbl_conn_sub.setText("Online @ 115200 bps")
            self.lbl_conn_val.setStyleSheet("font: 700 11.5pt 'Consolas'; color: #10b981;")
        self.log(f"Conectado em modo {self.mode}.")
        self._set_ui_state()

    def disconnect_device(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait(2500)
            self.online = False
            if self.running:
                self._finish_session("INTERROMPIDO / DESCONEXAO")
            self.worker = None
        self.lbl_conn_val.setText("DESCONECTADO")
        self.lbl_conn_sub.setText("UART 115200 8N1")
        self.lbl_conn_val.setStyleSheet("font: 700 11.5pt 'Consolas'; color: #64748b;")
        self._set_ui_state()

    def _on_disconnected(self, reason: str, source=None):
        if source is not None and source is not self.worker:
            return
        self.online = False
        if self.running:
            self._finish_session("INTERROMPIDO / LINK")
        self.lbl_conn_val.setText("DESCONECTADO")
        self.lbl_conn_val.setStyleSheet("font: 700 11.5pt 'Consolas'; color: #f43f5e;")
        self.log(reason)
        self.worker = None
        self._set_ui_state()

    def send_raw_command(self, cmd: str):
        if not self.online or not self.worker:
            QMessageBox.warning(self, "Sem Conexão", "Conecte-se ao Arduino UNO ou ative a Bancada Virtual primeiro.")
            return
        self.worker.send(cmd)
        self.log(f"TX >> {cmd}")

    def _send_manual_command(self):
        txt = self.edt_manual_cmd.text().strip()
        if txt:
            self.send_raw_command(txt)
            self.edt_manual_cmd.clear()

    def send_stage_times_to_arduino(self):
        """Envia SET <etapa> <tempo_ms> para as 6 etapas (0..5)."""
        if not self.online or not self.worker:
            QMessageBox.warning(self, "Sem Conexão", "Conecte-se ao Arduino UNO ou ative a Bancada Virtual primeiro.")
            return
        durations_ms = self.get_planned_stage_durations_ms()
        for etapa, ms in enumerate(durations_ms):
            self.worker.send(f"SET {etapa} {ms}")
        self.log(f"Tempos enviados ao Arduino UNO (ms): {durations_ms}")

    def clear_realtime_buffers(self):
        self.rt_times.clear()
        for s in SENSORES:
            self.rt_adc[s].clear()
        self.rt_temp.clear()
        self.rt_hum.clear()
        self.rt_press.clear()
        self.rt_cursor_line.setPos(0)
        for s in SENSORES:
            self.rt_curves[s].setData([], [])
            self.rt_heads[s].setData([], [])
        self.rt_temp_curve.setData([], [])
        self.rt_hum_curve.setData([], [])
        self._rebuild_stage_overlays()
        self._update_realtime_metrics_table()

    def start_measurement(self):
        if not self.online or not self.worker:
            return

        gas = self.cmb_gas.currentData() or "A"
        cfg = int(self.cmb_config.currentData() or 0)
        rep = self.cmb_rep.currentData() or "R1"
        conc = int(self.spn_conc.value())
        vol = int(self.spn_vol.value())
        sample_code = f"{gas}{cfg}-{rep}-{conc}"
        durations_ms = self.get_planned_stage_durations_ms()
        total_s = self.get_planned_total_seconds()

        if isinstance(self.worker, SimulationWorker):
            self.worker.set_gas_profile(gas)

        self.clear_realtime_buffers()
        self.current_stage = 0
        self.session_id = self.storage.begin(
            sample=sample_code,
            operator=self.edt_operator.text().strip(),
            notes=f"Gas={GAS_INFO.get(gas, gas)}; Config={CONFIG_NAMES.get(cfg)}; Rep={rep}; Conc={conc}ppm; Vol={vol}mL",
            duration=total_s,
            repetitions=1,
            mode=self.mode,
            gas_code=gas,
            config_id=cfg,
            rep_code=rep,
            concentration_ppm=conc,
            volume_ml=vol,
            stage_durations_ms=durations_ms,
        )
        self.last_session_id = self.session_id
        self.running = True
        self.cycle_progress.setRange(0, max(1, total_s))
        self.cycle_progress.setValue(0)
        self.lbl_stage_val.setText("INICIANDO...")
        self.lbl_stage_sub.setText(f"Amostra: {sample_code}")

        # Sincroniza os 6 tempos de etapa com o Arduino UNO antes do START
        for etapa, ms in enumerate(durations_ms):
            self.worker.send(f"SET {etapa} {ms}")
        self.worker.send("START")

        self.tabs.setCurrentIndex(0)
        self.log(f"=== ENSAIO #{self.session_id} INICIADO: {sample_code} (Tempo Total: {total_s} s) ===")
        self._set_ui_state()

    def stop_measurement(self):
        if self.worker:
            self.worker.send("STOP")
            self.log("TX >> STOP (Solicitando parada imediata e desligamento dos relés)")

    def reset_measurement(self):
        if self.worker:
            self.worker.send("RESET")
            self.log("TX >> RESET")
        if self.running:
            self._finish_session("RESETADO PELO OPERADOR")
        self._update_relay_badges(5)

    def _finish_session(self, status: str):
        finished_sid = self.session_id
        if self.session_id is not None:
            self.storage.event(self.session_id, f"FIM:{status}")
            self.storage.finish(self.session_id, status)
        self.session_id = None
        self.running = False
        self.lbl_stage_val.setText(status[:20])
        self._update_relay_badges(5)
        self.log(f"=== ENSAIO ENCERRADO: {status} ===")

        # Auto-save no formato v0.4.3 se habilitado e houver leituras
        if finished_sid is not None and self.chk_autosave_v043.isChecked() and len(self.rt_times) > 0:
            gas = self.cmb_gas.currentData() or "A"
            cfg = int(self.cmb_config.currentData() or 0)
            rep = self.cmb_rep.currentData() or "R1"
            conc = int(self.spn_conc.value())
            fname = format_v043_filename(gas, cfg, rep, conc)
            target_path = self.local_data_dir / str(cfg) / fname
            try:
                self.storage.export_v043_csv(finished_sid, target_path)
                self.log(f"CSV v0.4.3 salvo automaticamente em: {target_path}")
            except Exception as exc:
                self.log(f"Aviso: falha ao salvar CSV automático: {exc}")

        self._set_ui_state()

    def _update_relay_badges(self, stage: int):
        levels = STAGE_RELAY_LEVELS.get(stage, STAGE_RELAY_LEVELS[5])
        for key, (badge, lbl_state) in self.relay_badges.items():
            lvl = levels.get(key, "LOW")
            is_active = stage in (1, 2, 3, 4) and (
                (key in ("V1", "V2", "V3", "BOMBA") and lvl == "LOW" and stage in (1, 2))
                or (lvl == "HIGH" and stage in (3, 4))
            )
            badge.setObjectName("relayBadgeOn" if is_active else "relayBadgeOff")
            badge.style().unpolish(badge)
            badge.style().polish(badge)
            lbl_state.setText(f"Pino: {lvl}")
            lbl_state.setStyleSheet(
                f"font: 700 8pt 'Consolas'; color: {'#34d399' if is_active else '#94a3b8'};"
            )

    def _on_worker_message(self, d: dict):
        kind = d.get("type")

        if kind == "READING" or kind == "DATA":
            t_s = float(d.get("tempo_s", d.get("ms", 0) / 1000.0))
            mq2 = int(d.get("mq2", d["adc"][0]))
            mq3 = int(d.get("mq3", d["adc"][1]))
            mq5 = int(d.get("mq5", d["adc"][2]))
            temp = float(d.get("temp", 25.0))
            hum = float(d.get("hum", 50.0))
            press = float(d.get("pressao", 942.5))

            self.rt_times.append(t_s)
            self.rt_adc["MQ2"].append(mq2)
            self.rt_adc["MQ3"].append(mq3)
            self.rt_adc["MQ5"].append(mq5)
            self.rt_temp.append(temp)
            self.rt_hum.append(hum)
            self.rt_press.append(press)

            # Atualiza cartoes de telemetria no topo
            self.lbl_mq2_val.setText(f"{d['mq2_v']:.3f} V")
            self.lbl_mq2_sub.setText(f"ADC: {mq2}")
            self.lbl_mq3_val.setText(f"{d['mq3_v']:.3f} V")
            self.lbl_mq3_sub.setText(f"ADC: {mq3}")
            self.lbl_mq5_val.setText(f"{d['mq5_v']:.3f} V")
            self.lbl_mq5_sub.setText(f"ADC: {mq5}")
            self.lbl_env_val.setText(f"{temp:.2f} °C  |  {hum:.1f} %")
            self.lbl_env_sub.setText(f"Pressão: {press:.1f} hPa")

            total_planned = self.get_planned_total_seconds()
            pct = min(100.0, (t_s / max(1.0, float(total_planned))) * 100.0)
            self.lbl_time_val.setText(f"{int(t_s):03d}s / {total_planned:03d}s")
            self.lbl_time_sub.setText(f"Progresso: {pct:.1f}%")
            self.cycle_progress.setMaximum(max(total_planned, int(t_s) + 1))
            self.cycle_progress.setValue(int(t_s))

            if self.running and self.session_id is not None:
                self.storage.reading(self.session_id, d, current_stage=self.current_stage)

            # Atualiza o grafico em tempo real imediatamente a cada ponto recebido
            self.update_realtime_plots()
            self._update_realtime_metrics_table()

        elif kind == "STAGE":
            stage = int(d["stage"])
            self.current_stage = stage
            self.lbl_stage_val.setText(STAGE_SHORT_NAMES.get(stage, f"ETAPA {stage}"))
            self.lbl_stage_sub.setText(STAGE_NAMES.get(stage, ""))
            self._update_relay_badges(stage)
            self.log(f"ETAPA >> {d['message']}  ({STAGE_NAMES.get(stage, '')})")
            if self.session_id is not None:
                self.storage.event(self.session_id, f"STAGE:{stage}")

        elif kind == "STAGE_TIME":
            self.log(f"CONFIG >> {d['message']}")

        elif kind == "EVENT":
            ev_name = d["name"]
            self.log(f"EVENTO >> {ev_name}")
            if ev_name == "STARTED":
                self.lbl_stage_val.setText(STAGE_SHORT_NAMES.get(self.current_stage, "EM CICLO"))
            elif ev_name in ("FINISHED", "STOPPED", "FAILSAFE") and self.running:
                status_label = "CONCLUIDO" if ev_name == "FINISHED" else "PARADO"
                if ev_name == "FINISHED":
                    self.cycle_progress.setValue(self.cycle_progress.maximum())
                self._finish_session(status_label)
            elif ev_name == "RESET":
                self.lbl_stage_val.setText("RESETADO")
                self._update_relay_badges(5)

        elif kind == "ERR":
            self.log(f"ERRO >> {d['message']}")

        elif kind in ("INFO", "HEADER", "HELLO"):
            msg = d.get("message") or d.get("raw") or f"Protocolo {d.get('protocol')}"
            self.log(f"RX << {msg}")

    def update_realtime_plots(self):
        """Redesenha as curvas em tempo real sobre o Eixo X de Tempo Total."""
        total_planned_s = self.get_planned_total_seconds()
        if not self.rt_times:
            self.rt_gas_plot.setXRange(0, total_planned_s, padding=0.01)
            return

        x = np.asarray(self.rt_times, dtype=float)
        max_x = max(float(total_planned_s), float(x[-1]) + 2.0)
        self.rt_gas_plot.setXRange(0, max_x, padding=0.01)
        self.rt_cursor_line.setPos(float(x[-1]))

        ymode = self.cmb_rt_ymode.currentData() or "V"
        window = int(self.spn_rt_smooth.value())

        if ymode == "ADC":
            self.rt_gas_plot.setLabel("left", "Leitura ADC (0 – 1023)")
            self.rt_gas_plot.setYRange(0, 1023, padding=0.03)
        elif ymode == "V":
            self.rt_gas_plot.setLabel("left", "Tensão Absoluta (V)")
            self.rt_gas_plot.enableAutoRange(axis="y", enable=True)
        elif ymode == "REL_V":
            self.rt_gas_plot.setLabel("left", "Tensão Relativa ΔV (V)")
            self.rt_gas_plot.enableAutoRange(axis="y", enable=True)
        else:
            self.rt_gas_plot.setLabel("left", "Taxa dV/dt (V/s)")
            self.rt_gas_plot.enableAutoRange(axis="y", enable=True)

        for s in SENSORES:
            visible = self.chk_rt_sensors[s].isChecked()
            self.rt_curves[s].setVisible(visible)
            self.rt_heads[s].setVisible(visible)
            if not visible:
                continue

            raw_adc = np.asarray(self.rt_adc[s][: len(x)], dtype=float)
            if len(raw_adc) == 0:
                continue

            if window > 1 and len(raw_adc) >= 2:
                series_adc = pd.Series(raw_adc).rolling(window=window, center=True, min_periods=1).mean().to_numpy()
            else:
                series_adc = raw_adc

            series_v = AnalisadorGases.converter_adc_para_tensao(series_adc)

            if ymode == "ADC":
                y = series_adc
            elif ymode == "V":
                y = series_v
            elif ymode == "REL_V":
                mask_60 = x <= max(5.0, float(self.stage_spinboxes[1].value()))
                v_base = float(np.min(series_v[mask_60])) if np.any(mask_60) else float(np.min(series_v))
                y = series_v - v_base
            else:
                if len(series_v) >= 2:
                    dt = np.diff(x)
                    y = np.gradient(series_v, x) if np.all(dt > 0) else np.gradient(series_v)
                else:
                    y = np.zeros_like(series_v)

            self.rt_curves[s].setData(x, y)
            self.rt_heads[s].setData([float(x[-1])], [float(y[-1])])

        # Atualiza grafico ambiental sincronizado
        if len(self.rt_temp) == len(x):
            self.rt_temp_curve.setData(x, np.asarray(self.rt_temp, dtype=float))
        if len(self.rt_hum) == len(x):
            self.rt_hum_curve.setData(x, np.asarray(self.rt_hum, dtype=float))

    def _update_realtime_metrics_table(self):
        baseline_s = max(5.0, float(self.stage_spinboxes[1].value()))
        rows = realtime_metrics(
            self.rt_times,
            self.rt_adc,
            janela=int(self.spn_rt_smooth.value()),
            baseline_limit_s=baseline_s,
        )
        cols = [
            "Sensor",
            "ADC Atual",
            "V Atual (V)",
            "V_baseline (V)",
            "V_max Abs (V)",
            "ΔV Relativo (V)",
            "Taxa Max (V/s)",
            "AUC (V·s)",
        ]
        for i, row in enumerate(rows):
            for j, col_name in enumerate(cols):
                val = row.get(col_name)
                if val is None:
                    txt = "—"
                elif isinstance(val, int):
                    txt = str(val)
                elif isinstance(val, float):
                    txt = f"{val:.4f}"
                else:
                    txt = str(val)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_rt_metrics.setItem(i, j, item)

    def export_current_csv(self):
        if self.last_session_id is None:
            QMessageBox.information(self, "Sem Ensaio", "Execute ou inicie um ensaio antes de exportar.")
            return
        gas = self.cmb_gas.currentData() or "A"
        cfg = int(self.cmb_config.currentData() or 0)
        rep = self.cmb_rep.currentData() or "R1"
        conc = int(self.spn_conc.value())
        default_name = format_v043_filename(gas, cfg, rep, conc)
        default_dir = self.local_data_dir / str(cfg)
        default_dir.mkdir(parents=True, exist_ok=True)

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Ensaio CSV (Padrão v0.4.3)",
            str(default_dir / default_name),
            "CSV v0.4.3 (*.csv)",
        )
        if filename:
            try:
                self.storage.export_v043_csv(self.last_session_id, filename)
                self.log(f"Ensaio #{self.last_session_id} exportado no padrão v0.4.3: {filename}")
            except Exception as exc:
                QMessageBox.critical(self, "Erro na Exportação", str(exc))

    def _set_ui_state(self):
        self.btn_start.setEnabled(self.online and not self.running)
        self.btn_stop.setEnabled(self.online and self.running)
        self.btn_reset.setEnabled(self.online)
        self.btn_send_stages.setEnabled(self.online and not self.running)
        self.btn_show_stages.setEnabled(self.online)
        self.btn_connect.setText("Desconectar" if (self.worker and self.mode == "SERIAL") else "Conectar UNO")
        self.btn_sim.setEnabled(not self.running)
        self.cmb_gas.setEnabled(not self.running)
        self.cmb_config.setEnabled(not self.running)
        self.cmb_rep.setEnabled(not self.running)
        self.spn_conc.setEnabled(not self.running)
        self.spn_vol.setEnabled(not self.running)
        for spn in self.stage_spinboxes:
            spn.setEnabled(not self.running)
        self.btn_export_csv.setEnabled(self.last_session_id is not None)

    # =========================================================================
    # ABA 2 & ABA 3: ANALISADOR DE DADOS DO NARIZ ELETRONICO v0.4.3
    # =========================================================================
    def browse_v043_data_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Dados v0.4.3", self.edt_data_dir.text())
        if folder:
            self.edt_data_dir.setText(folder)
            self.refresh_v043_analysis()
            self.refresh_matrix_3x3()

    def refresh_v043_analysis(self):
        pasta = Path(self.edt_data_dir.text().strip())
        if not pasta.exists():
            return

        analisador = AnalisadorGases(volume_recipiente=self.spn_vol.value())
        mode = self.cmb_ana_mode.currentData() or "REP_V"
        gas = self.cmb_ana_gas.currentData() or "A"
        cfg = int(self.cmb_ana_cfg.currentData() or 0)
        conc = int(self.cmb_ana_conc.currentData() or 100)
        sensor_sel = self.cmb_ana_sensor.currentData() or "TODOS"
        janela = int(self.spn_ana_window.value())
        sensores_loop = SENSORES if sensor_sel == "TODOS" else [sensor_sel]

        self.ana_plot.clear()
        self.ana_plot.addLegend(offset=(14, 14))
        self.ana_plot.setLabel("bottom", "Tempo Total (s)")

        metricas_rows: list[dict] = []

        if mode in ("REP_V", "REP_REL"):
            relativo = mode == "REP_REL"
            self.ana_plot.setLabel("left", "Tensão Relativa ΔV (V)" if relativo else "Tensão (V)")
            self.ana_plot.setTitle(
                f"{GAS_INFO.get(gas, gas)}  |  {CONFIG_NAMES.get(cfg)}  |  {conc} ppm  ({'ΔV Relativa' if relativo else 'Tensão Absoluta'})"
            )
            dfs_reps, df_media = analisador.carregar_dados(pasta, gas, cfg, conc)
            if df_media is not None:
                df_media_s = analisador.suavizar(df_media, janela)
                t_m = df_media_s["tempo"].to_numpy() if "tempo" in df_media_s else np.arange(len(df_media_s))

                for s in sensores_loop:
                    col_v = f"{s}_V"
                    if dfs_reps:
                        for rep, df_r in dfs_reps.items():
                            df_rs = analisador.suavizar(df_r, janela)
                            t_r = df_rs["tempo"].to_numpy() if "tempo" in df_rs else np.arange(len(df_rs))
                            if col_v in df_rs:
                                y_r = df_rs[col_v].to_numpy(dtype=float)
                                if relativo and len(y_r):
                                    y_r = y_r - np.min(y_r)
                                color = CORES_NEON.get(rep, CORES_SENSORES[s]) if sensor_sel != "TODOS" else CORES_SENSORES[s]
                                pen = pg.mkPen(color, width=1.6, style=Qt.PenStyle.SolidLine)
                                self.ana_plot.plot(t_r, y_r, pen=pen, name=f"{s} {rep}")

                    if col_v in df_media_s:
                        y_m = df_media_s[col_v].to_numpy(dtype=float)
                        if relativo and len(y_m):
                            y_m = y_m - np.min(y_m)
                        color_m = "#ffffff" if sensor_sel != "TODOS" else CORES_SENSORES[s]
                        pen_m = pg.mkPen(color_m, width=3.2, style=Qt.PenStyle.DotLine)
                        self.ana_plot.plot(t_m, y_m, pen=pen_m, name=f"Média {s}")

                    m = analisador.calcular_metricas_avancadas(df_media_s, s, dfs_individuais=dfs_reps)
                    if m:
                        m["Gas"] = GAS_INFO.get(gas, gas)
                        m["Config"] = CONFIG_NAMES.get(cfg, str(cfg))
                        metricas_rows.append(m)

        elif mode == "COMP_ALETAS":
            target_s = "MQ2" if sensor_sel == "TODOS" else sensor_sel
            self.ana_plot.setLabel("left", f"Tensão Média Relativa ΔV (V) — {target_s}")
            self.ana_plot.setTitle(
                f"Comparativo de Aletas (Configs 0..4)  |  Gás: {GAS_INFO.get(gas, gas)} ({conc} ppm)  |  Sensor: {target_s}"
            )
            for cid in CONFIG_IDS:
                dfs_reps, df_media = analisador.carregar_dados(pasta, gas, cid, conc)
                if df_media is not None:
                    df_ms = analisador.suavizar(df_media, janela)
                    t_m = df_ms["tempo"].to_numpy() if "tempo" in df_ms else np.arange(len(df_ms))
                    col_v = f"{target_s}_V"
                    if col_v in df_ms:
                        y = df_ms[col_v].to_numpy(dtype=float)
                        if len(y):
                            y = y - np.min(y)
                        self.ana_plot.plot(
                            t_m,
                            y,
                            pen=pg.mkPen(CORES_CONFIG.get(cid, "#38bdf8"), width=2.5),
                            name=f"{CONFIG_NAMES[cid]} ({target_s})",
                        )
                    m = analisador.calcular_metricas_avancadas(df_ms, target_s, dfs_individuais=dfs_reps)
                    if m:
                        m["Gas"] = GAS_INFO.get(gas, gas)
                        m["Config"] = CONFIG_NAMES[cid]
                        metricas_rows.append(m)

        elif mode == "COMP_GASES":
            target_s = "MQ2" if sensor_sel == "TODOS" else sensor_sel
            self.ana_plot.setLabel("left", f"Tensão Média Relativa ΔV (V) — {target_s}")
            self.ana_plot.setTitle(
                f"Comparativo de Gases  |  Aleta: {CONFIG_NAMES.get(cfg)} ({conc} ppm)  |  Sensor: {target_s}"
            )
            for g_code in GAS_CODES_ALL:
                dfs_reps, df_media = analisador.carregar_dados(pasta, g_code, cfg, conc)
                if df_media is not None:
                    df_ms = analisador.suavizar(df_media, janela)
                    t_m = df_ms["tempo"].to_numpy() if "tempo" in df_ms else np.arange(len(df_ms))
                    col_v = f"{target_s}_V"
                    if col_v in df_ms:
                        y = df_ms[col_v].to_numpy(dtype=float)
                        if len(y):
                            y = y - np.min(y)
                        self.ana_plot.plot(
                            t_m,
                            y,
                            pen=pg.mkPen(CORES_GASES.get(g_code, "#38bdf8"), width=2.5),
                            name=f"{GAS_INFO.get(g_code, g_code)} ({target_s})",
                        )
                    m = analisador.calcular_metricas_avancadas(df_ms, target_s, dfs_individuais=dfs_reps)
                    if m:
                        m["Gas"] = GAS_INFO.get(g_code, g_code)
                        m["Config"] = CONFIG_NAMES.get(cfg, str(cfg))
                        metricas_rows.append(m)

        elif mode == "DERIVADA":
            self.ana_plot.setLabel("left", "Taxa de Variação dV/dt (V/s)")
            self.ana_plot.setTitle(
                f"Taxa de Variação (dV/dt)  |  {GAS_INFO.get(gas, gas)} — {CONFIG_NAMES.get(cfg)} ({conc} ppm)"
            )
            dfs_reps, df_media = analisador.carregar_dados(pasta, gas, cfg, conc)
            if df_media is not None:
                df_ms = analisador.suavizar(df_media, janela)
                t_m = df_ms["tempo"].to_numpy(dtype=float) if "tempo" in df_ms else np.arange(len(df_ms), dtype=float)
                for s in sensores_loop:
                    col_v = f"{s}_V"
                    if col_v in df_ms and len(t_m) >= 2:
                        y = df_ms[col_v].to_numpy(dtype=float)
                        grad = np.gradient(y, t_m) if np.all(np.diff(t_m) > 0) else np.gradient(y)
                        self.ana_plot.plot(t_m, grad, pen=pg.mkPen(CORES_SENSORES[s], width=2.2), name=f"d({s})/dt")
                    m = analisador.calcular_metricas_avancadas(df_ms, s, dfs_individuais=dfs_reps)
                    if m:
                        m["Gas"] = GAS_INFO.get(gas, gas)
                        m["Config"] = CONFIG_NAMES.get(cfg, str(cfg))
                        metricas_rows.append(m)

        elif mode == "AMBIENTAL":
            self.ana_plot.setLabel("left", "Temperatura (°C) / Umidade (%)")
            self.ana_plot.setTitle(
                f"Condições Ambientais  |  {GAS_INFO.get(gas, gas)} — {CONFIG_NAMES.get(cfg)} ({conc} ppm)"
            )
            _, df_media = analisador.carregar_dados(pasta, gas, cfg, conc)
            if df_media is not None:
                df_ms = analisador.suavizar(df_media, janela)
                t_m = df_ms["tempo"].to_numpy(dtype=float) if "tempo" in df_ms else np.arange(len(df_ms), dtype=float)
                if "Temperatura" in df_ms:
                    self.ana_plot.plot(
                        t_m, df_ms["Temperatura"].to_numpy(), pen=pg.mkPen("#ef4444", width=2.4), name="Temperatura (°C)"
                    )
                if "Umidade" in df_ms:
                    self.ana_plot.plot(
                        t_m, df_ms["Umidade"].to_numpy(), pen=pg.mkPen("#38bdf8", width=2.4), name="Umidade (%)"
                    )

        self._populate_analyzer_table(metricas_rows)
        self.refresh_matrix_3x3()

    def _populate_analyzer_table(self, rows: list[dict]):
        cols = [
            "Gas",
            "Config",
            "Sensor",
            "V_baseline (V)",
            "V_max Abs (V)",
            "V_max Relativo (V)",
            "Tempo V_max (s)",
            "Taxa Max (V/s)",
            "Tempo Subida (s)",
            "Tempo Descida (s)",
            "Erro Mult. (%)",
        ]
        self.tbl_ana_metrics.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, c in enumerate(cols):
                val = r.get(c)
                if val is None:
                    txt = "—"
                elif isinstance(val, float):
                    txt = f"{val:.4f}"
                else:
                    txt = str(val)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_ana_metrics.setItem(i, j, item)

    def refresh_matrix_3x3(self):
        pasta = Path(self.edt_data_dir.text().strip())
        if not pasta.exists():
            return

        analisador = AnalisadorGases(volume_recipiente=self.spn_vol.value())
        mode = self.cmb_m3_mode.currentData() or "ABS_V"
        cfg = int(self.cmb_m3_cfg.currentData() or 0)
        conc = int(self.cmb_m3_conc.currentData() or 100)
        janela = int(self.spn_ana_window.value())

        for gas_code in GAS_CODES_3X3:
            if mode == "ALETAS":
                for sensor in SENSORES:
                    pw = self.plots_3x3[(gas_code, sensor)]
                    pw.clear()
                    col_v = f"{sensor}_V"
                    for cid in CONFIG_IDS:
                        _, df_media = analisador.carregar_dados(pasta, gas_code, cid, conc)
                        if df_media is not None and col_v in df_media:
                            df_ms = analisador.suavizar(df_media, janela)
                            t = df_ms["tempo"].to_numpy() if "tempo" in df_ms else np.arange(len(df_ms))
                            y = df_ms[col_v].to_numpy(dtype=float)
                            if len(y):
                                y = y - np.min(y)
                            pw.plot(t, y, pen=pg.mkPen(CORES_CONFIG[cid], width=2.0), name=CONFIG_NAMES[cid])
            else:
                dfs_reps, df_media = analisador.carregar_dados(pasta, gas_code, cfg, conc)
                for sensor in SENSORES:
                    pw = self.plots_3x3[(gas_code, sensor)]
                    pw.clear()
                    if df_media is None:
                        continue
                    df_ms = analisador.suavizar(df_media, janela)
                    t_m = df_ms["tempo"].to_numpy(dtype=float) if "tempo" in df_ms else np.arange(len(df_ms), dtype=float)
                    col_v = f"{sensor}_V"

                    if mode in ("ABS_V", "REL_V"):
                        rel = mode == "REL_V"
                        if dfs_reps:
                            for rep, df_r in dfs_reps.items():
                                df_rs = analisador.suavizar(df_r, janela)
                                t_r = (
                                    df_rs["tempo"].to_numpy(dtype=float)
                                    if "tempo" in df_rs
                                    else np.arange(len(df_rs), dtype=float)
                                )
                                if col_v in df_rs:
                                    y_r = df_rs[col_v].to_numpy(dtype=float)
                                    if rel and len(y_r):
                                        y_r = y_r - np.min(y_r)
                                    pw.plot(t_r, y_r, pen=pg.mkPen(CORES_NEON.get(rep, "#38bdf8"), width=1.5))
                        if col_v in df_ms:
                            y_m = df_ms[col_v].to_numpy(dtype=float)
                            if rel and len(y_m):
                                y_m = y_m - np.min(y_m)
                            pw.plot(t_m, y_m, pen=pg.mkPen("#ffffff", width=2.6, style=Qt.PenStyle.DotLine))
                    elif mode == "DERIV" and col_v in df_ms and len(t_m) >= 2:
                        y_m = df_ms[col_v].to_numpy(dtype=float)
                        grad = np.gradient(y_m, t_m) if np.all(np.diff(t_m) > 0) else np.gradient(y_m)
                        pw.plot(t_m, grad, pen=pg.mkPen("#a855f7", width=2.0))

        # Popula Matrizes Comparativas por Sensor (% vs Default)
        comp_dict = analisador.gerar_tabelas_comparativas(pasta, conc, janela)
        cols_order = ["Gas", "Default", "Config V", "Config A", "Config X", "Config O"]
        for s in SENSORES:
            tbl = self.tbl_comp_by_sensor[s]
            df_s = comp_dict.get(s, pd.DataFrame())
            if df_s.empty:
                tbl.setRowCount(0)
                continue
            tbl.setRowCount(len(df_s))
            for i, (_, row) in enumerate(df_s.iterrows()):
                for j, col_name in enumerate(cols_order):
                    val = row.get(col_name, "—")
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    tbl.setItem(i, j, item)

    def export_full_matrix_csv(self):
        pasta = Path(self.edt_data_dir.text().strip())
        conc = int(self.cmb_m3_conc.currentData() or 100)
        janela = int(self.spn_ana_window.value())
        analisador = AnalisadorGases(volume_recipiente=self.spn_vol.value())
        df_mat = analisador.gerar_matriz_completa(pasta, conc, janela=janela)
        if df_mat.empty:
            QMessageBox.warning(self, "Matriz Vazia", "Não há dados suficientes na pasta selecionada para gerar a matriz.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Matriz Completa v0.4.3",
            f"matriz_completa_{conc}ppm.csv",
            "CSV (*.csv)",
        )
        if filename:
            df_mat.to_csv(filename, index=False, encoding="utf-8-sig")
            self.log(f"Matriz completa exportada: {filename}")

    def closeEvent(self, event):
        self.disconnect_device()
        self.storage.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(INDUSTRIAL_STYLE)
    pg.setConfigOptions(antialias=True)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
