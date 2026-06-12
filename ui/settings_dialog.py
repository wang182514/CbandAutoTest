"""
Settings dialog — tabbed editor for ALL configurable parameters.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QFormLayout,
    QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton,
    QGroupBox, QDialogButtonBox, QComboBox, QWidget,
)
from PySide6.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("详细设置")
        self.resize(700, 550)
        self._cfg = config_manager

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._tab_instruments(), "仪器连接")
        tabs.addTab(self._tab_product(), "产品信息")
        tabs.addTab(self._tab_rf_path(), "射频链路")
        tabs.addTab(self._tab_test_rx_nf(), "RX NF/增益")
        tabs.addTab(self._tab_test_rx_pn(), "RX 相位噪声")
        tabs.addTab(self._tab_test_tx_gain(), "TX 增益/功率")
        tabs.addTab(self._tab_test_tx_flat(), "TX 平坦度/PN")
        tabs.addTab(self._tab_test_influence(), "收发干扰")
        tabs.addTab(self._tab_report(), "报告/截图")

        layout.addWidget(tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._load_all()

    # ========================================================================
    #  Tab builders
    # ========================================================================

    def _tab_instruments(self) -> QWidget:
        w = QWidget()
        l = QFormLayout(w)

        c = self._cfg.data.instruments

        # RX Power
        self._rx_pwr_ip = self._add_line(l, "RX电源 IP", c.rx_power_supply.ip)
        self._rx_pwr_port = self._add_spin(l, "RX电源端口", c.rx_power_supply.port, 1, 65535)

        # TX Power
        self._tx_pwr_ip = self._add_line(l, "TX电源 IP", c.tx_power_supply.ip)
        self._tx_pwr_port = self._add_spin(l, "TX电源端口", c.tx_power_supply.port, 1, 65535)

        # VSG
        self._vsg_ip = self._add_line(l, "信号源 IP", c.signal_generator.ip)
        self._vsg_vendor = self._add_line(l, "信号源 厂商", c.signal_generator.vendor)

        # SA
        self._sa_ip = self._add_line(l, "频谱仪 IP", c.spectrum_analyzer.ip)
        self._sa_vendor = self._add_line(l, "频谱仪 厂商", c.spectrum_analyzer.vendor)

        # Switch
        self._sw_com = self._add_line(l, "开关 COM口", c.switch_matrix.com_port)
        self._sw_baud = self._add_spin(l, "开关 波特率", c.switch_matrix.baud_rate, 9600, 921600)

        return w

    def _tab_product(self) -> QWidget:
        w = QWidget()
        l = QFormLayout(w)
        c = self._cfg.data
        self._prod_name = self._add_line(l, "产品名称", c.product.name)
        self._prod_model = self._add_line(l, "产品型号", c.product.model)
        self._prod_env = self._add_line(l, "测试环境", c.product.test_env)
        self._prod_op = self._add_line(l, "操作员", c.product.operator)
        self._prod_sn = self._add_line(l, "序列号", c.serial_number)
        return w

    def _tab_rf_path(self) -> QWidget:
        w = QWidget()
        l = QFormLayout(w)
        c = self._cfg.data.rf_path

        grp_if = QGroupBox("TX IF 线损 (dB)")
        g1 = QFormLayout(grp_if)
        self._if_loss = []
        vals = c.tx_if_line_loss
        for i, label in enumerate(["0.95GHz", "1.20GHz", "1.55GHz"]):
            sp = self._add_double(g1, label, vals[i] if i < len(vals) else 2.0, -20, 40)
            self._if_loss.append(sp)
        l.addRow(grp_if)

        grp_rf = QGroupBox("TX RF 线损 (dB, 含衰减器)")
        g2 = QFormLayout(grp_rf)
        self._rf_loss = []
        vals = c.tx_rf_line_loss
        for i, label in enumerate(["5.85GHz", "6.10GHz", "6.45GHz"]):
            sp = self._add_double(g2, label, vals[i] if i < len(vals) else 23.5, 0, 60)
            self._rf_loss.append(sp)
        l.addRow(grp_rf)

        grp_off = QGroupBox("RF 线损修正 (dB)")
        g3 = QFormLayout(grp_off)
        self._rf_off = []
        vals = c.tx_rf_line_loss_offset
        for i, label in enumerate(["5.85GHz", "6.10GHz", "6.45GHz"]):
            sp = self._add_double(g3, label, vals[i] if i < len(vals) else 0.0, -10, 10)
            self._rf_off.append(sp)
        l.addRow(grp_off)

        return w

    def _tab_test_rx_nf(self) -> QWidget:
        w = QWidget()
        l = QFormLayout(w)
        c = self._cfg.data.test_rx_nf
        self._nf_template = self._add_line(l, "模板名称", c.template_name)
        self._nf_max = self._add_double(l, "NF 最大限 (dB)", c.limits.nf_max_db, 0, 10)
        self._nf_mean = self._add_double(l, "NF 平均限 (dB)", c.limits.nf_mean_db, 0, 10)
        self._gain_mean = self._add_double(l, "增益平均限 (dB)", c.limits.gain_mean_db, 0, 80)
        self._flatness = self._add_double(l, "增益平坦度限 (dB)", c.limits.gain_flatness_db, 0, 10)
        return w

    def _tab_test_rx_pn(self) -> QWidget:
        w = QWidget()
        l = QFormLayout(w)
        c = self._cfg.data.test_rx_pn
        self._pn_rx_template = self._add_line(l, "模板名称", c.template_name)
        self._pn_rx_center = self._add_double(l, "中心频率 (GHz)", c.center_freq_ghz, 0.1, 10)
        self._pn_rx_vsg_freq = self._add_double(l, "VSG 频率 (MHz)", c.vsg_freq_mhz, 100, 12000)
        self._pn_rx_vsg_pwr = self._add_double(l, "VSG 功率 (dBm)", c.vsg_power_dbm, -120, 30)

        pn = c.pn_offsets
        for label in ["100Hz", "1KHz", "10KHz", "100KHz"]:
            setattr(self, f"_rx_pn_{label}",
                    self._add_double(l, f"RX PN {label} 限 (dBc/Hz)",
                                     pn[label].limit_dbc_hz, -160, 0))
        return w

    def _tab_test_tx_gain(self) -> QWidget:
        w = QWidget()
        l = QFormLayout(w)
        c = self._cfg.data.test_tx_gain
        self._txg_template = self._add_line(l, "模板名称", c.template_name)
        self._txg_vsg_pwr = self._add_double(l, "VSG 功率 (dBm)", c.vsg_power_dbm, -120, 30)
        self._txg_pout_min = self._add_double(l, "Pout 最小限 (dBm)", c.limits.pout_min_dbm, 0, 60)
        self._txg_gain_min = self._add_double(l, "Gain 最小限 (dB)", c.limits.gain_min_db, 0, 80)
        return w

    def _tab_test_tx_flat(self) -> QWidget:
        w = QWidget()
        l = QFormLayout(w)
        c = self._cfg.data.test_tx_flatness_pn
        self._txf_flat_template = self._add_line(l, "平坦度模板", c.flatness_template)
        self._txf_pn_template = self._add_line(l, "PN 模板", c.pn_template)
        self._txf_vsg_pwr = self._add_double(l, "VSG 功率", c.vsg_power_dbm, -120, 30)
        self._txf_flat_limit = self._add_double(l, "平坦度限 (dB)", c.limits.flatness_db, 0, 10)
        for label in ["pn_100Hz_dbc_hz", "pn_1KHz_dbc_hz", "pn_10KHz_dbc_hz", "pn_100KHz_dbc_hz"]:
            setattr(self, f"_txf_{label}",
                    self._add_double(l, f"TX PN {label.split('_')[1]} 限 (dBc/Hz)",
                                     getattr(c.limits, label), -160, 0))
        return w

    def _tab_test_influence(self) -> QWidget:
        w = QWidget()
        l = QFormLayout(w)
        c = self._cfg.data.test_tx_rx_influence
        self._inf_vsg_pwr = self._add_double(l, "VSG 功率", c.vsg_power_dbm, -120, 30)
        self._inf_limit = self._add_double(l, "噪底差异限 (dB)", c.limit.noise_floor_delta_db, 0, 20)
        return w

    def _tab_report(self) -> QWidget:
        w = QWidget()
        l = QFormLayout(w)
        c = self._cfg.data
        self._scr_en = QCheckBox("启用截图")
        self._scr_en.setChecked(c.screenshot.enabled)
        l.addRow("截图:", self._scr_en)
        self._scr_path = self._add_line(l, "仪表截图路径", c.screenshot.instrument_internal_path)
        self._rpt_txt = QCheckBox("生成 TXT 报告")
        self._rpt_txt.setChecked(c.report.txt_enabled)
        l.addRow("TXT:", self._rpt_txt)
        self._rpt_docx = QCheckBox("生成 DOCX 报告")
        self._rpt_docx.setChecked(c.report.docx_enabled)
        l.addRow("DOCX:", self._rpt_docx)
        self._rpt_template = self._add_line(l, "DOCX 模板", c.report.template_file)
        return w

    # ========================================================================
    #  Helpers
    # ========================================================================

    def _add_line(self, form, label, default):
        edit = QLineEdit(str(default) if default else "")
        form.addRow(label + ":", edit)
        return edit

    def _add_spin(self, form, label, default, min_v, max_v):
        sp = QSpinBox()
        sp.setRange(min_v, max_v)
        sp.setValue(int(default) if default else 0)
        form.addRow(label + ":", sp)
        return sp

    def _add_double(self, form, label, default, min_v, max_v):
        sp = QDoubleSpinBox()
        sp.setRange(min_v, max_v)
        sp.setDecimals(2)
        sp.setValue(float(default) if default else 0.0)
        form.addRow(label + ":", sp)
        return sp

    # ========================================================================
    #  Load / Save
    # ========================================================================

    def _load_all(self):
        """UI is already pre-populated in _tab_* methods from config."""
        pass

    def _on_accept(self):
        """Save all UI values back to config."""
        c = self._cfg.data

        # Instruments
        c.instruments.rx_power_supply.ip = self._rx_pwr_ip.text()
        c.instruments.rx_power_supply.port = self._rx_pwr_port.value()
        c.instruments.tx_power_supply.ip = self._tx_pwr_ip.text()
        c.instruments.tx_power_supply.port = self._tx_pwr_port.value()
        c.instruments.signal_generator.ip = self._vsg_ip.text()
        c.instruments.signal_generator.vendor = self._vsg_vendor.text()
        c.instruments.spectrum_analyzer.ip = self._sa_ip.text()
        c.instruments.spectrum_analyzer.vendor = self._sa_vendor.text()
        c.instruments.switch_matrix.com_port = self._sw_com.text()
        c.instruments.switch_matrix.baud_rate = self._sw_baud.value()

        # Product
        c.product.name = self._prod_name.text()
        c.product.model = self._prod_model.text()
        c.product.test_env = self._prod_env.text()
        c.product.operator = self._prod_op.text()
        c.serial_number = self._prod_sn.text()

        # RF path
        for i, sp in enumerate(self._if_loss):
            c.rf_path.tx_if_line_loss[i] = sp.value()
        for i, sp in enumerate(self._rf_loss):
            c.rf_path.tx_rf_line_loss[i] = sp.value()
        for i, sp in enumerate(self._rf_off):
            c.rf_path.tx_rf_line_loss_offset[i] = sp.value()

        # RX NF
        c.test_rx_nf.template_name = self._nf_template.text()
        c.test_rx_nf.limits.nf_max_db = self._nf_max.value()
        c.test_rx_nf.limits.nf_mean_db = self._nf_mean.value()
        c.test_rx_nf.limits.gain_mean_db = self._gain_mean.value()
        c.test_rx_nf.limits.gain_flatness_db = self._flatness.value()

        # RX PN
        c.test_rx_pn.template_name = self._pn_rx_template.text()
        c.test_rx_pn.center_freq_ghz = self._pn_rx_center.value()
        c.test_rx_pn.vsg_freq_mhz = self._pn_rx_vsg_freq.value()
        c.test_rx_pn.vsg_power_dbm = self._pn_rx_vsg_pwr.value()
        for label in ["100Hz", "1KHz", "10KHz", "100KHz"]:
            c.test_rx_pn.pn_offsets[label].limit_dbc_hz = getattr(self, f"_rx_pn_{label}").value()

        # TX Gain
        c.test_tx_gain.template_name = self._txg_template.text()
        c.test_tx_gain.vsg_power_dbm = self._txg_vsg_pwr.value()
        c.test_tx_gain.limits.pout_min_dbm = self._txg_pout_min.value()
        c.test_tx_gain.limits.gain_min_db = self._txg_gain_min.value()

        # TX Flatness
        c.test_tx_flatness_pn.flatness_template = self._txf_flat_template.text()
        c.test_tx_flatness_pn.pn_template = self._txf_pn_template.text()
        c.test_tx_flatness_pn.vsg_power_dbm = self._txf_vsg_pwr.value()
        c.test_tx_flatness_pn.limits.flatness_db = self._txf_flat_limit.value()
        for label in ["pn_100Hz_dbc_hz", "pn_1KHz_dbc_hz", "pn_10KHz_dbc_hz", "pn_100KHz_dbc_hz"]:
            setattr(c.test_tx_flatness_pn.limits, label, getattr(self, f"_txf_{label}").value())

        # Influence
        c.test_tx_rx_influence.vsg_power_dbm = self._inf_vsg_pwr.value()
        c.test_tx_rx_influence.limit.noise_floor_delta_db = self._inf_limit.value()

        # Report
        c.screenshot.enabled = self._scr_en.isChecked()
        c.screenshot.instrument_internal_path = self._scr_path.text()
        c.report.txt_enabled = self._rpt_txt.isChecked()
        c.report.docx_enabled = self._rpt_docx.isChecked()
        c.report.template_file = self._rpt_template.text()

        self.accept()
