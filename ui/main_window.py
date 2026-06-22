"""
PySide6 main window: instrument status, test control, results display.
"""

import json
import os
import sys
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QTextEdit,
    QCheckBox, QProgressBar, QTabWidget, QMessageBox, QFileDialog,
    QStatusBar, QSplitter, QApplication, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from config.config_manager import ConfigManager
from ui.settings_dialog import SettingsDialog
from ui.test_runner import TestRunner
from ui.results_panel import ResultsPanel
from utils.logger import Logger
from utils.report import ReportGenerator, sanitize_results


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("C波段射频模块自动化测试系统")
        self.resize(1200, 800)

        # ---- config ----
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        defaults = os.path.join(base_dir, "config", "default_settings.json")
        self.config = ConfigManager(defaults)
        user_config = os.path.join(base_dir, "config", "user_settings.json")
        if os.path.exists(user_config):
            self.config.load(user_config)

        # ---- logger ----
        self.logger = Logger(log_dir=os.path.join(base_dir, "output", "logs"))

        # ---- instruments (lazy) ----
        self._rx_pwr = None
        self._tx_pwr = None
        self._vsg = None
        self._sa = None
        self._switch = None

        # ---- accumulated results (for report) ----
        self._all_results: list = []

        # ---- UI ----
        self._build_ui()
        self._load_config_to_ui()

        # ---- runner ----
        self._runner: TestRunner | None = None

    # ========================================================================
    #  UI construction
    # ========================================================================

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)

        # ---- left panel (scrollable so it fits small screens) ----
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(260)
        left_scroll.setMaximumWidth(360)
        left_container = QWidget()
        left = QVBoxLayout(left_container)
        left.setStretch(0, 0)

        # --- instrument status group with colored indicators ---
        grp_inst = QGroupBox("仪器状态")
        g1 = QVBoxLayout(grp_inst)

        self._ind_rx_pwr = self._create_status_indicator()
        self._ind_tx_pwr = self._create_status_indicator()
        self._ind_vsg = self._create_status_indicator()
        self._ind_sa = self._create_status_indicator()
        self._ind_switch = self._create_status_indicator()

        self._lbl_rx_pwr = QLabel("接收电源: 未连接")
        self._lbl_rx_pwr.setWordWrap(True)
        self._lbl_tx_pwr = QLabel("发射电源: 未连接")
        self._lbl_tx_pwr.setWordWrap(True)
        self._lbl_vsg = QLabel("信号源: 未连接")
        self._lbl_vsg.setWordWrap(True)
        self._lbl_sa = QLabel("频谱仪: 未连接")
        self._lbl_sa.setWordWrap(True)
        self._lbl_switch = QLabel("开关矩阵: 未连接")
        self._lbl_switch.setWordWrap(True)

        g1.addLayout(self._status_row(self._ind_rx_pwr, self._lbl_rx_pwr))
        g1.addLayout(self._status_row(self._ind_tx_pwr, self._lbl_tx_pwr))
        g1.addLayout(self._status_row(self._ind_vsg, self._lbl_vsg))
        g1.addLayout(self._status_row(self._ind_sa, self._lbl_sa))
        g1.addLayout(self._status_row(self._ind_switch, self._lbl_switch))

        btn_connect = QPushButton("连接全部仪表")
        btn_connect.clicked.connect(self._on_connect_all)
        btn_disconnect = QPushButton("断开全部仪表")
        btn_disconnect.clicked.connect(self._on_disconnect_all)
        g1.addWidget(btn_connect)
        g1.addWidget(btn_disconnect)
        left.addWidget(grp_inst)

        # --- quick params ---
        grp_params = QGroupBox("快速设置")
        g2 = QVBoxLayout(grp_params)
        row_sn = QHBoxLayout()
        row_sn.addWidget(QLabel("序列号:"))
        self._edit_sn = QLineEdit()
        row_sn.addWidget(self._edit_sn)
        g2.addLayout(row_sn)

        self._chk_screenshot = QCheckBox("启用截图")
        g2.addWidget(self._chk_screenshot)

        btn_settings = QPushButton("详细设置...")
        btn_settings.clicked.connect(self._on_open_settings)
        g2.addWidget(btn_settings)

        btn_save_cfg = QPushButton("保存配置")
        btn_save_cfg.clicked.connect(self._on_save_config)
        g2.addWidget(btn_save_cfg)
        left.addWidget(grp_params)

        # --- test control ---
        grp_test = QGroupBox("测试控制")
        g3 = QVBoxLayout(grp_test)

        self._btn_run_all = QPushButton("▶ 运行全部测试")
        self._btn_run_all.clicked.connect(lambda: self._run_tests(None))
        self._btn_run_all.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        g3.addWidget(self._btn_run_all)

        # Individual test buttons
        test_names = [
            ("rx_nf", "RX 噪声系数 + 增益"),
            ("rx_pn", "RX 相位噪声"),
            ("tx_gain", "TX 增益 + 输出功率"),
            ("tx_flatness_pn", "TX 平坦度 + 相位噪声"),
            ("tx_rx_influence", "收发干扰"),
        ]
        for name, label in test_names:
            btn = QPushButton(label)
            btn.setMaximumWidth(320)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, n=name: self._run_tests([n]))
            g3.addWidget(btn)

        self._btn_stop = QPushButton("■ 停止")
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_stop.setEnabled(False)
        self._btn_stop.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        g3.addWidget(self._btn_stop)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        g3.addWidget(self._progress)

        self._btn_report = QPushButton("📄 写入报告")
        self._btn_report.clicked.connect(self._on_write_report)
        self._btn_report.setEnabled(False)
        self._btn_report.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        g3.addWidget(self._btn_report)
        left.addWidget(grp_test)

        left.addStretch()
        left_scroll.setWidget(left_container)

        # ---- right panel ----
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 0, 0)

        # Results panel
        self._results_panel = ResultsPanel()
        self._results_panel.setMinimumHeight(200)
        right.addWidget(self._results_panel, 2)

        # Log output
        grp_log = QGroupBox("日志")
        g4 = QVBoxLayout(grp_log)
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMinimumHeight(80)
        g4.addWidget(self._log_view)
        right.addWidget(grp_log, 1)

        # ---- main splitter: left | right ----
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(left_scroll)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([300, 900])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        root.addWidget(main_splitter, 1)

        # ---- status bar ----
        self._status = QStatusBar()
        self._status.showMessage("就绪")
        self.setStatusBar(self._status)

    # ========================================================================
    #  Status indicator helpers
    # ========================================================================

    @staticmethod
    def _create_status_indicator() -> QLabel:
        """Create a small colored square used as a connection status light."""
        ind = QLabel()
        ind.setFixedSize(14, 14)
        ind.setStyleSheet("background-color: #9E9E9E; border-radius: 7px;")
        return ind

    @staticmethod
    def _trim_idn(idn: str, max_len: int = 35) -> str:
        """Truncate long IDN strings so status labels stay single-line."""
        if len(idn) <= max_len:
            return idn
        return idn[:max_len] + "…"

    @staticmethod
    def _status_row(indicator: QLabel, label: QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(indicator)
        row.addWidget(label, 1)
        row.setSpacing(8)
        row.setContentsMargins(0, 2, 0, 2)
        return row

    def _set_status_indicator(self, indicator: QLabel, state: str):
        """Update indicator color: 'ok' green, 'error' red, 'idle' gray."""
        colors = {
            "ok": "#4CAF50",
            "error": "#F44336",
            "idle": "#9E9E9E",
        }
        indicator.setStyleSheet(
            f"background-color: {colors.get(state, colors['idle'])}; border-radius: 7px;"
        )

    # ========================================================================
    #  Config ↔ UI
    # ========================================================================

    def _load_config_to_ui(self):
        self._edit_sn.setText(self.config.get("serial_number", ""))
        self._chk_screenshot.setChecked(self.config.get("screenshot.enabled", True))

    def _save_ui_to_config(self):
        self.config.set("serial_number", self._edit_sn.text())
        self.config.set("screenshot.enabled", self._chk_screenshot.isChecked())

    def _on_save_config(self):
        self._save_ui_to_config()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "config", "user_settings.json")
        self.config.save(path)
        self._status.showMessage(f"配置已保存到 {path}")

    def _on_open_settings(self):
        self._save_ui_to_config()
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self._load_config_to_ui()

    # ========================================================================
    #  Instrument connection
    # ========================================================================

    def _on_connect_all(self):
        """Connect all 4 instruments + switch matrix."""
        from instruments.power_supply import PowerSupply
        from instruments.signal_generator import SignalGenerator
        from instruments.spectrum_analyzer import SpectrumAnalyzer
        from instruments.switch_matrix import SwitchMatrix

        self._status.showMessage("正在连接仪表...")
        self._log("=== 连接仪表 ===")

        cfg = self.config.data.instruments

        # RX Power Supply
        try:
            self._rx_pwr = PowerSupply(
                ip=cfg.rx_power_supply.ip,
                port=cfg.rx_power_supply.port,
                timeout_sec=cfg.rx_power_supply.timeout_sec,
            )
            idn = self._rx_pwr.connect()
            self._lbl_rx_pwr.setText(f"接收电源: ✓ {self._trim_idn(idn)}")
            self._lbl_rx_pwr.setToolTip(idn)
            self._set_status_indicator(self._ind_rx_pwr, "ok")
            self._log(f"  RX电源: {idn}")
        except Exception as e:
            self._lbl_rx_pwr.setText(f"接收电源: ✗ {e}")
            self._set_status_indicator(self._ind_rx_pwr, "error")
            self._log(f"  RX电源失败: {e}")

        # TX Power Supply
        try:
            self._tx_pwr = PowerSupply(
                ip=cfg.tx_power_supply.ip,
                port=cfg.tx_power_supply.port,
                timeout_sec=cfg.tx_power_supply.timeout_sec,
            )
            idn = self._tx_pwr.connect()
            self._lbl_tx_pwr.setText(f"发射电源: ✓ {self._trim_idn(idn)}")
            self._lbl_tx_pwr.setToolTip(idn)
            self._set_status_indicator(self._ind_tx_pwr, "ok")
            self._log(f"  TX电源: {idn}")
        except Exception as e:
            self._lbl_tx_pwr.setText(f"发射电源: ✗ {e}")
            self._set_status_indicator(self._ind_tx_pwr, "error")
            self._log(f"  TX电源失败: {e}")

        # Signal Generator
        try:
            self._vsg = SignalGenerator(
                ip=cfg.signal_generator.ip,
                vendor=cfg.signal_generator.vendor,
                timeout_ms=int(cfg.signal_generator.timeout_sec * 1000),
            )
            idn = self._vsg.connect()
            self._lbl_vsg.setText(f"信号源: ✓ {self._trim_idn(idn)}")
            self._lbl_vsg.setToolTip(idn)
            self._set_status_indicator(self._ind_vsg, "ok")
            self._log(f"  信号源: {idn}")
        except Exception as e:
            self._lbl_vsg.setText(f"信号源: ✗ {e}")
            self._set_status_indicator(self._ind_vsg, "error")
            self._log(f"  信号源失败: {e}")

        # Spectrum Analyzer
        try:
            self._sa = SpectrumAnalyzer(
                ip=cfg.spectrum_analyzer.ip,
                vendor=cfg.spectrum_analyzer.vendor,
                timeout_ms=int(cfg.spectrum_analyzer.timeout_sec * 1000),
            )
            idn = self._sa.connect()
            self._lbl_sa.setText(f"频谱仪: ✓ {self._trim_idn(idn)}")
            self._lbl_sa.setToolTip(idn)
            self._set_status_indicator(self._ind_sa, "ok")
            self._log(f"  频谱仪: {idn}")
        except Exception as e:
            self._lbl_sa.setText(f"频谱仪: ✗ {e}")
            self._set_status_indicator(self._ind_sa, "error")
            self._log(f"  频谱仪失败: {e}")

        # Switch Matrix
        try:
            self._switch = SwitchMatrix(
                com_port=cfg.switch_matrix.com_port,
                baud_rate=cfg.switch_matrix.baud_rate,
                timeout_sec=cfg.switch_matrix.timeout_sec,
            )
            self._switch.connect()
            com = cfg.switch_matrix.com_port
            self._lbl_switch.setText(f"开关矩阵: ✓ {com}")
            self._lbl_switch.setToolTip(f"COM端口: {com}")
            self._set_status_indicator(self._ind_switch, "ok")
            self._log(f"  开关矩阵: {com}")
        except Exception as e:
            self._lbl_switch.setText(f"开关矩阵: ✗ {e}")
            self._set_status_indicator(self._ind_switch, "error")
            self._log(f"  开关矩阵失败: {e}")

        self._status.showMessage("仪表连接完成")

    def _on_disconnect_all(self):
        for obj in [self._rx_pwr, self._tx_pwr, self._vsg, self._sa, self._switch]:
            if obj:
                try:
                    obj.disconnect()
                except Exception:
                    pass
        self._rx_pwr = self._tx_pwr = self._vsg = self._sa = self._switch = None
        self._lbl_rx_pwr.setText("接收电源: 未连接")
        self._lbl_rx_pwr.setToolTip("")
        self._lbl_tx_pwr.setText("发射电源: 未连接")
        self._lbl_tx_pwr.setToolTip("")
        self._lbl_vsg.setText("信号源: 未连接")
        self._lbl_vsg.setToolTip("")
        self._lbl_sa.setText("频谱仪: 未连接")
        self._lbl_sa.setToolTip("")
        self._lbl_switch.setText("开关矩阵: 未连接")
        self._lbl_switch.setToolTip("")
        for ind in [self._ind_rx_pwr, self._ind_tx_pwr, self._ind_vsg,
                    self._ind_sa, self._ind_switch]:
            self._set_status_indicator(ind, "idle")
        self._log("=== 已断开全部仪表 ===")
        self._status.showMessage("已断开全部仪表")

    def closeEvent(self, event):
        """Safely stop test thread and disconnect instruments on window close."""
        if self._runner and self._runner.isRunning():
            self._runner.request_stop()
            self._status.showMessage("正在停止测试线程...")
            if not self._runner.wait(5000):  # 5s grace
                self._runner.terminate()
                self._runner.wait(2000)
        self._on_disconnect_all()
        event.accept()

    # ========================================================================
    #  Test execution
    # ========================================================================

    def _run_tests(self, test_names: list | None):
        """Run one or all tests in a worker thread."""
        if not all([self._rx_pwr, self._tx_pwr, self._vsg, self._sa, self._switch]):
            QMessageBox.warning(self, "未连接", "请先连接全部仪表")
            return

        self._save_ui_to_config()

        # Keep previous results visible during this run; they will be
        # overwritten as each test completes. Only clear the log.
        self._log_view.clear()

        all_tests = [
            "rx_nf",
            "rx_pn",
            "tx_gain",
            "tx_flatness_pn",
            "tx_rx_influence",
        ]
        to_run = test_names if test_names else all_tests

        self._runner = TestRunner(
            rx_pwr=self._rx_pwr,
            tx_pwr=self._tx_pwr,
            vsg=self._vsg,
            sa=self._sa,
            switch=self._switch,
            config=self.config,
            test_names=to_run,
        )
        self._runner.log_signal.connect(self._log)
        self._runner.result_signal.connect(self._on_test_result)
        self._runner.finished_signal.connect(self._on_all_done)
        self._runner.progress_signal.connect(self._on_progress)

        self._progress.setVisible(True)
        self._progress.setMaximum(len(to_run))
        self._progress.setValue(0)
        self._btn_run_all.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._status.showMessage("测试运行中...")

        self._runner.start()

    def _on_stop(self):
        if self._runner and self._runner.isRunning():
            self._runner.request_stop()
            self._status.showMessage("正在停止...")

    def _on_test_result(self, test_name: str, passed: bool, messages: list):
        # Find the latest data for this test from accumulated results
        data = {}
        for r in self._all_results:
            if r.get("name") == test_name:
                data = r.get("data", {})
                break
        self._results_panel.set_result(test_name, passed, messages, data)

    def _on_progress(self, current: int, total: int):
        self._progress.setValue(current)

    def _on_all_done(self, results: list):
        self._progress.setVisible(False)
        self._btn_run_all.setEnabled(True)
        self._btn_stop.setEnabled(False)

        # Merge into accumulated results — same test name → overwrite
        for new_r in results:
            name = new_r.get("name", "")
            # Remove previous result with same name
            self._all_results = [r for r in self._all_results if r.get("name") != name]
            self._all_results.append(new_r)

        # Enable report button once we have at least one result
        self._btn_report.setEnabled(len(self._all_results) > 0)

        # Also refresh the results panel with the final accumulated data
        for r in self._all_results:
            self._results_panel.set_result(
                r.get("name", ""),
                r.get("passed", False),
                r.get("messages", []),
                r.get("data", {}),
            )

        # Summary
        total = len(results)
        passed = sum(1 for r in results if r.get("passed", False))
        self._status.showMessage(f"测试完成: {passed}/{total} 通过 — 点击「写入报告」保存结果")

    # ========================================================================
    #  Report (manual trigger)
    # ========================================================================

    def _on_write_report(self):
        """Manually triggered by user — writes report from accumulated results."""
        if not self._all_results:
            QMessageBox.information(self, "无数据", "没有测试结果可写入，请先运行测试。")
            return

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sn = self.config.get("serial_number", "UNKNOWN")

        self._log("=== 写入报告 ===")

        try:
            report_gen = ReportGenerator(self.config.data, logger=_UiLogAdapter(self._log))
            txt_path = report_gen.generate_txt(
                all_results=self._all_results,
                output_dir=os.path.join(base_dir, "output", "reports"),
                sn=sn,
            )
            if txt_path:
                self._log(f"文本报告已生成: {txt_path}")
                self._status.showMessage(f"报告已写入: {txt_path}")

            # DOCX requires Word template
            template = os.path.join(base_dir, "..", self.config.get("report.template_file", "CbandTemplate.docx"))
            if os.path.exists(template):
                # --- 内部 Word 报告 (真实数据) ---
                docx_path = report_gen.generate_docx(
                    all_results=self._all_results,
                    output_dir=os.path.join(base_dir, "output", "reports"),
                    sn=sn,
                    template_path=template,
                )
                if docx_path:
                    self._log(f"Word 报告已生成: {docx_path}")

                # --- 客户 Word 报告 (合规数据) ---
                sanitized = sanitize_results(self._all_results, self.config)
                customer_sn = f"{sn}_toC"
                docx_customer_path = report_gen.generate_docx(
                    all_results=sanitized,
                    output_dir=os.path.join(base_dir, "output", "reports"),
                    sn=customer_sn,
                    template_path=template,
                )
                if docx_customer_path:
                    self._log(f"客户 Word 报告已生成: {docx_customer_path}")
            else:
                self._log(f"Word 模板未找到: {template}，跳过 docx 生成")

        except Exception as e:
            self._log(f"报告生成失败: {e}")
            QMessageBox.critical(self, "报告错误", f"报告生成失败:\n{e}")

    # ========================================================================
    #  Logging
    # ========================================================================

    def _log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        self._log_view.append(line)
        self._log_view.ensureCursorVisible()
        self.logger.info(msg)


class _UiLogAdapter:
    """Adapts UI _log method to the logger interface expected by ReportGenerator."""
    def __init__(self, log_fn):
        self._log = log_fn
    def info(self, msg): self._log(msg)
    def warning(self, msg): self._log(f"[WARN] {msg}")
    def error(self, msg): self._log(f"[ERROR] {msg}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
