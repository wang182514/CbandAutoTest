"""
ResultsPanel — displays test summary and detailed formatted results.

Layout:
    ┌─────────────────────────────────┐
    │  [  ✓ 全部合格 — 5/5 通过  ]    │  ← banner
    ├─────────────────────────────────┤
    │  ┌──────────┐ ┌──────────┐     │  ← card grid (2 cols, scrollable)
    │  │ ✓ PASS   │ │ ✗ FAIL   │     │
    │  └──────────┘ └──────────┘     │
    ├─────────────────────────────────┤
    │  Detail browser (HTML)         │
    ├─────────────────────────────────┤
    │  [Export JSON] [Export CSV]     │
    └─────────────────────────────────┘

Clicking a card switches the detail view.
"""

import csv
import json
from datetime import datetime
from typing import Any, Dict, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QPushButton, QFileDialog, QMessageBox,
    QLabel, QFrame, QScrollArea, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal


class _ResultCard(QFrame):
    """A clickable card showing one test's status and key metrics."""

    clicked = Signal(str)

    def __init__(self, test_name: str, parent=None):
        super().__init__(parent)
        self._test_name = test_name
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(3)

        self._name_lbl = QLabel(test_name)
        self._name_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        lay.addWidget(self._name_lbl)

        self._status_lbl = QLabel("—")
        self._status_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        lay.addWidget(self._status_lbl)

        self._metric_lbl = QLabel("")
        self._metric_lbl.setStyleSheet("color: #666; font-size: 11px;")
        self._metric_lbl.setWordWrap(True)
        lay.addWidget(self._metric_lbl)

        self.set_default_style()

    def set_default_style(self):
        self.setStyleSheet(
            "_ResultCard { background: #fafafa; border: 1px solid #ddd; border-radius: 6px; }"
            "_ResultCard:hover { border-color: #aaa; }"
        )
        self._status_lbl.setText("—")
        self._status_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #999;")

    def set_passed(self, passed: bool, metric_text: str = "", stopped: bool = False):
        if stopped:
            clr, bg, badge = "#e65100", "#fff3e0", "⊘  已终止"
        elif passed:
            clr, bg, badge = "#2e7d32", "#e8f5e9", "✓  PASS"
        else:
            clr, bg, badge = "#c62828", "#ffebee", "✗  FAIL"

        self.setStyleSheet(
            f"_ResultCard {{ background: {bg}; border: 1px solid {clr}; "
            f"border-left: 4px solid {clr}; border-radius: 6px; }}"
            f"_ResultCard:hover {{ border-color: {clr}; }}"
        )
        self._status_lbl.setText(badge)
        self._status_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {clr};")
        self._metric_lbl.setText(metric_text)

    def mousePressEvent(self, event):
        self.clicked.emit(self._test_name)
        super().mousePressEvent(event)


class ResultsPanel(QWidget):
    """Panel for showing test summary and detailed results."""

    cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: Dict[str, Dict[str, Any]] = {}
        self._cards: Dict[str, _ResultCard] = {}
        self._build_ui()

    # ========================================================================
    #  UI construction
    # ========================================================================

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ---- banner ----
        self._banner = QLabel()
        self._banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._banner.setVisible(False)
        self._banner.setStyleSheet("font-size: 14px; font-weight: bold; padding: 6px; border-radius: 4px;")
        layout.addWidget(self._banner)

        # ---- card grid (scrollable) ----
        self._card_scroll = QScrollArea()
        self._card_scroll.setWidgetResizable(True)
        self._card_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._card_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._card_scroll.setMaximumHeight(250)

        self._card_container = QWidget()
        self._card_grid = QGridLayout(self._card_container)
        self._card_grid.setContentsMargins(2, 2, 2, 2)
        self._card_grid.setSpacing(6)
        self._card_scroll.setWidget(self._card_container)
        layout.addWidget(self._card_scroll)

        # ---- detail browser ----
        self._detail = QTextBrowser()
        self._detail.setOpenExternalLinks(False)
        self._detail.setHtml(self._welcome_html())
        layout.addWidget(self._detail, 1)

        # ---- buttons ----
        btn_layout = QHBoxLayout()
        self._btn_export_json = QPushButton("导出 JSON")
        self._btn_export_json.clicked.connect(self._on_export_json)
        self._btn_export_csv = QPushButton("导出 CSV")
        self._btn_export_csv.clicked.connect(self._on_export_csv)
        self._btn_clear = QPushButton("清空结果")
        self._btn_clear.clicked.connect(self.clear_results)
        btn_layout.addWidget(self._btn_export_json)
        btn_layout.addWidget(self._btn_export_csv)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_clear)
        layout.addLayout(btn_layout)

        self._update_button_state()

    # ========================================================================
    #  Public API
    # ========================================================================

    def set_result(self, test_name: str, passed: bool, messages: List[str], data: Dict[str, Any], stopped: bool = False):
        """Add or update a test result."""
        self._results[test_name] = {
            "passed": passed,
            "stopped": stopped,
            "messages": messages,
            "data": data,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
        self._refresh_cards()
        self._update_banner()
        self._show_detail(test_name)

    def clear_results(self):
        """Clear all displayed results."""
        self._results.clear()
        for card in self._cards.values():
            card.set_default_style()
        self._banner.setVisible(False)
        self._detail.setHtml(self._welcome_html())
        self._update_button_state()
        self.cleared.emit()

    def set_test_names(self, names: List[str]):
        """Pre-populate card placeholders before tests start."""
        for card in self._cards.values():
            self._card_grid.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        cols = 2
        for i, name in enumerate(names):
            card = _ResultCard(name)
            card.clicked.connect(self._on_card_clicked)
            self._cards[name] = card
            self._card_grid.addWidget(card, i // cols, i % cols)

    def results(self) -> List[Dict[str, Any]]:
        """Return results in the same shape used by ReportGenerator."""
        return [
            {
                "name": name,
                "passed": r["passed"],
                "messages": r["messages"],
                "data": r["data"],
            }
            for name, r in self._results.items()
        ]

    # ========================================================================
    #  Banner
    # ========================================================================

    def _update_banner(self):
        if not self._results:
            self._banner.setVisible(False)
            return

        total = len(self._results)
        passed = sum(1 for r in self._results.values() if r["passed"])
        stopped = sum(1 for r in self._results.values() if r.get("stopped"))

        if stopped > 0:
            bg, fg, text = "#ffe0b2", "#e65100", f"⊘  {passed}/{total} 通过，{stopped} 项已终止"
        elif passed == total:
            bg, fg, text = "#c8e6c9", "#2e7d32", f"✓  全部合格 — {passed}/{total} 通过"
        elif passed > 0:
            bg, fg, text = "#fff9c4", "#f57f17", f"⚠  {passed}/{total} 通过，{total - passed} 项不合格"
        else:
            bg, fg, text = "#ffcdd2", "#c62828", f"✗  全部不合格 — 0/{total} 通过"

        self._banner.setText(text)
        self._banner.setStyleSheet(
            f"font-size: 14px; font-weight: bold; padding: 8px; border-radius: 4px;"
            f"background-color: {bg}; color: {fg};"
        )
        self._banner.setVisible(True)

    # ========================================================================
    #  Card grid
    # ========================================================================

    def _refresh_cards(self):
        for name, r in self._results.items():
            card = self._cards.get(name)
            if card is None:
                continue
            try:
                card.set_passed(
                    r["passed"],
                    self._summary_text(name, r["data"]),
                    r.get("stopped", False),
                )
            except Exception:
                # If summary_text crashes (e.g. empty data), at least show the badge
                card.set_passed(r["passed"], "—", r.get("stopped", False))

    def _on_card_clicked(self, name: str):
        self._show_detail(name)

    # ========================================================================
    #  Detail view
    # ========================================================================

    def _show_detail(self, name: str):
        r = self._results.get(name)
        if r is None:
            return
        self._detail.setHtml(self._build_detail_html(name, r))

    # ========================================================================
    #  HTML helpers
    # ========================================================================

    @staticmethod
    def _welcome_html() -> str:
        return (
            "<html><body style='font-family:Microsoft YaHei,SimHei,sans-serif;'>"
            "<p style='color:#666;'>测试结果将在运行后自动显示。</p>"
            "</body></html>"
        )

    @staticmethod
    def _style() -> str:
        return """
        <style>
            body { font-family: Microsoft YaHei, SimHei, sans-serif; font-size: 13px; }
            h3 { margin: 8px 0 6px 0; color: #333; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 8px; }
            th, td { border: 1px solid #ccc; padding: 4px 7px; text-align: center; }
            th { background-color: #f2f2f2; font-weight: bold; }
            .agg-row td { background-color: #f9f9f9; font-weight: bold; font-size: 12px; }
            .pass { color: #2e7d32; font-weight: bold; }
            .fail { color: #c62828; font-weight: bold; }
        </style>
        """

    def _build_detail_html(self, name: str, r: Dict[str, Any]) -> str:
        passed = r["passed"]
        data = r.get("data", {})
        status = "PASS" if passed else "FAIL"
        status_class = "pass" if passed else "fail"

        html = [
            "<html><head>",
            self._style(),
            "</head><body>",
            f"<h3>{name} <span class='{status_class}'>{status}</span></h3>",
            f"<p style='color:#888;font-size:12px;'>测试时间: {r.get('time', '--:--:--')}</p>",
            self._detail_section(name, data),
            "</body></html>",
        ]
        return "\n".join(html)

    @staticmethod
    def _badge(ok: bool) -> str:
        return '<span class="pass">✓</span>' if ok else '<span class="fail">✗</span>'

    def _detail_section(self, name: str, data: Dict[str, Any]) -> str:
        if name == "RX 噪声系数 + 增益":
            return self._rx_nf_html(data)
        if name == "RX 相位噪声":
            return self._rx_pn_html(data)
        if name == "TX 增益 + 输出功率":
            return self._tx_gain_html(data)
        if name == "TX 平坦度 + 相位噪声":
            return self._tx_flatness_pn_html(data)
        if name == "收发干扰":
            return self._tx_rx_influence_html(data)
        return self._generic_html(data)

    @staticmethod
    def _rx_nf_html(data: Dict[str, Any]) -> str:
        B = ResultsPanel._badge
        L = data.get("limits", {})
        freqs = data.get("nf_freqs", [])
        nf = data.get("nf_list", [])
        gain = data.get("gain_list", [])
        rows = []
        for i, f in enumerate(freqs):
            nv = f"{nf[i]:.3f}" if i < len(nf) else "—"
            gv = f"{gain[i]:.3f}" if i < len(gain) else "—"
            rows.append(f"<tr><td>{f:.2f}</td><td>{nv}</td><td>{gv}</td></tr>")

        nf_max = data.get("nf_max_db", 0)
        nf_mean = data.get("nf_mean_db", 0)
        g_mean = data.get("gain_mean_db", 0)
        g_flat = data.get("gain_flatness_db", 0)
        lm1 = L.get("nf_max_db", 1.3)
        lm2 = L.get("nf_mean_db", 1.2)
        lm3 = L.get("gain_mean_db", 50.0)
        lm4 = L.get("gain_flatness_db", 2.5)
        agg = (
            f"<tr class='agg-row'><td>NF 最大值</td>"
            f"<td>{nf_max:.3f}</td><td>≤ {lm1:.2f}</td><td>{B(nf_max <= lm1)}</td></tr>"
            f"<tr class='agg-row'><td>NF 平均值</td>"
            f"<td>{nf_mean:.3f}</td><td>&lt; {lm2:.2f}</td><td>{B(nf_mean < lm2)}</td></tr>"
            f"<tr class='agg-row'><td>增益平均值</td>"
            f"<td>{g_mean:.3f}</td><td>&gt; {lm3:.2f}</td><td>{B(g_mean > lm3)}</td></tr>"
            f"<tr class='agg-row'><td>增益平坦度</td>"
            f"<td>{g_flat:.3f}</td><td>&lt; {lm4:.2f}</td><td>{B(g_flat < lm4)}</td></tr>"
        )
        return (
            "<h3>RX 噪声系数与增益</h3>"
            "<table><tr><th>频率 (GHz)</th><th>NF (dB)</th><th>Gain (dB)</th></tr>"
            + "".join(rows)
            + "<tr><td colspan='3' style='border:none;'></td></tr>"
            + agg + "</table>"
        )

    @staticmethod
    def _rx_pn_html(data: Dict[str, Any]) -> str:
        B = ResultsPanel._badge
        has_limits = any(k in data.get("limits", {}) for k in ["100Hz", "1KHz"])
        if has_limits:
            limits = data["limits"]
        else:
            limits = {"100Hz": -65.0, "1KHz": -74.0, "10KHz": -80.0, "100KHz": -95.0}
        spots = data.get("rx_pn_spots", {})
        rows = []
        for label in ["100Hz", "1KHz", "10KHz", "100KHz"]:
            entry = spots.get(label, {})
            val = entry.get("pn_dbc_hz")
            offset = entry.get("offset_hz")
            v_str = f"{val:.3f}" if val is not None else "—"
            o_str = f"{offset / 1000:.1f} kHz" if offset is not None else label
            lim = limits[label]
            ok = val is not None and val < lim
            rows.append(
                f"<tr><td>{o_str}</td><td>{v_str}</td>"
                f"<td>&lt; {lim:.1f}</td><td>{B(ok)}</td></tr>"
            )
        current = data.get("rx_current_a")
        c_str = f"{current:.3f} A" if current is not None else "—"
        return (
            "<h3>RX 相位噪声</h3>"
            "<table><tr><th>偏移</th><th>PN (dBc/Hz)</th><th>限值</th><th></th></tr>"
            + "".join(rows) + "</table>"
            f"<p>接收电流: {c_str}</p>"
        )

    @staticmethod
    def _tx_gain_html(data: Dict[str, Any]) -> str:
        B = ResultsPanel._badge
        L = data.get("limits", {})
        p_limits = L.get("pout_min_dbm", [32.8, 32.8, 32.8])
        g_limits = L.get("gain_min_db", [47.0, 47.0, 47.0])
        if not isinstance(p_limits, list):
            p_limits = [p_limits, p_limits, p_limits]
        if not isinstance(g_limits, list):
            g_limits = [g_limits, g_limits, g_limits]
        freqs = data.get("tx_freqs_mhz", [])
        pout = data.get("tx_pout_dbm", [])
        gain = data.get("tx_gain_db", [])
        current = data.get("tx_current_a", [])
        rows = []
        for i, f in enumerate(freqs):
            p = pout[i] if i < len(pout) else None
            g = gain[i] if i < len(gain) else None
            c = current[i] if i < len(current) else None
            pm = p_limits[i] if i < len(p_limits) else 32.8
            gm = g_limits[i] if i < len(g_limits) else 47.0
            rows.append(
                "<tr><td>" + str(f) + "</td>"
                + ("<td>" + f"{p:.2f}" + "</td>" if p is not None else "<td>—</td>")
                + "<td>≥ " + f"{pm:.2f}" + "</td>"
                + "<td>" + B(p is not None and p >= pm) + "</td>"
                + ("<td>" + f"{g:.2f}" + "</td>" if g is not None else "<td>—</td>")
                + "<td>≥ " + f"{gm:.2f}" + "</td>"
                + "<td>" + B(g is not None and g >= gm) + "</td>"
                + ("<td>" + f"{c:.3f}" + "</td>" if c is not None else "<td>—</td>")
                + "</tr>"
            )
        peak = data.get("tx_peak_current_a")
        p_str = f"{peak:.3f} A" if peak is not None else "—"
        return (
            "<h3>TX 增益与输出功率</h3>"
            "<table><tr><th>IF (MHz)</th><th>Pout (dBm)</th><th>限值</th><th></th>"
            "<th>Gain (dB)</th><th>限值</th><th></th><th>电流 (A)</th></tr>"
            + "".join(rows) + "</table>"
            f"<p>峰值电流: {p_str}</p>"
        )

    @staticmethod
    def _tx_flatness_pn_html(data: Dict[str, Any]) -> str:
        B = ResultsPanel._badge
        L = data.get("limits", {})
        flat_limit = L.get("flatness_db", 3.0)
        flatness = data.get("tx_flatness_db")
        f_val = f"{flatness:.3f}" if flatness is not None else "—"
        f_ok = flatness is not None and flatness < flat_limit
        flat_row = (
            f"<tr><td>发射平坦度</td><td>{f_val} dB</td>"
            f"<td>&lt; {flat_limit:.2f}</td><td>{B(f_ok)}</td></tr>"
        )

        limits = {
            "100Hz": L.get("pn_100Hz", -65.0),
            "1KHz": L.get("pn_1KHz", -74.0),
            "10KHz": L.get("pn_10KHz", -80.0),
            "100KHz": L.get("pn_100KHz", -95.0),
        }
        spots = data.get("tx_pn_spots", {})
        pn_rows = []
        for label in ["100Hz", "1KHz", "10KHz", "100KHz"]:
            entry = spots.get(label, {})
            val = entry.get("pn_dbc_hz")
            offset = entry.get("offset_hz")
            v_str = f"{val:.3f}" if val is not None else "—"
            o_str = f"{offset / 1000:.1f} kHz" if offset is not None else label
            lim = limits[label]
            ok = val is not None and val < lim
            pn_rows.append(
                f"<tr><td>{o_str}</td><td>{v_str}</td>"
                f"<td>&lt; {lim:.1f}</td><td>{B(ok)}</td></tr>"
            )
        return (
            "<h3>TX 平坦度</h3>"
            "<table><tr><th>指标</th><th>值</th><th>限值</th><th></th></tr>"
            + flat_row + "</table>"
            "<h3>TX 相位噪声</h3>"
            "<table><tr><th>偏移</th><th>PN (dBc/Hz)</th><th>限值</th><th></th></tr>"
            + "".join(pn_rows) + "</table>"
        )

    @staticmethod
    def _tx_rx_influence_html(data: Dict[str, Any]) -> str:
        B = ResultsPanel._badge
        LIMIT = data.get("limits", {}).get("noise_floor_delta_db", 2.0)
        rx_freqs = data.get("rx_if_freqs_mhz", [])
        off = data.get("rx_noise_tx_off", [])
        on = data.get("rx_noise_tx_on", [])
        deltas = data.get("noise_deltas", [])
        rows = []
        for i, f in enumerate(rx_freqs):
            o = off[i] if i < len(off) else None
            n = on[i] if i < len(on) else None
            d = deltas[i] if i < len(deltas) else None
            d_ok = d is not None and d <= LIMIT
            rows.append(
                "<tr><td>" + str(f) + "</td>"
                + ("<td>" + f"{o:.3f}" + "</td>" if o is not None else "<td>—</td>")
                + ("<td>" + f"{n:.3f}" + "</td>" if n is not None else "<td>—</td>")
                + ("<td>" + f"{d:.3f}" + "</td>" if d is not None else "<td>—</td>")
                + "<td>≤ " + f"{LIMIT:.1f}" + "</td><td>" + B(d_ok) + "</td></tr>"
            )
        max_delta = data.get("noise_delta_max")
        m_val = f"{max_delta:.3f}" if max_delta is not None else "—"
        m_ok = max_delta is not None and max_delta <= LIMIT
        agg = (
            f"<tr class='agg-row'><td>最大差异</td><td colspan='2'></td>"
            f"<td>{m_val}</td><td>≤ {LIMIT:.1f}</td><td>{B(m_ok)}</td></tr>"
        )
        return (
            "<h3>TX-RX 收发干扰</h3>"
            "<table><tr><th>RX IF (MHz)</th><th>TXOFF (dBm/Hz)</th>"
            "<th>TXON (dBm/Hz)</th><th>差异 (dB)</th><th>限值</th><th></th></tr>"
            + "".join(rows) + agg + "</table>"
        )

    @staticmethod
    def _generic_html(data: Dict[str, Any]) -> str:
        if not data:
            return "<p>无详细数据。</p>"
        rows = []
        for k, v in data.items():
            rows.append(f"<tr><td><b>{k}</b></td><td>{str(v)}</td></tr>")
        return "<table>" + "".join(rows) + "</table>"

    @staticmethod
    def _summary_text(name: str, data: Dict[str, Any]) -> str:
        def _fmt(val, unit=""):
            """Safe float format — returns '—' for non-numeric values."""
            if not isinstance(val, (int, float)):
                return "—"
            return f"{val:.3f}{unit}" if unit else f"{val:.3f}"

        if name == "RX 噪声系数 + 增益":
            return (f"NF均值 {_fmt(data.get('nf_mean_db'))} dB  |  "
                    f"Gain均值 {_fmt(data.get('gain_mean_db'))} dB")
        if name == "RX 相位噪声":
            spots = data.get("rx_pn_spots", {})
            val = spots.get("1KHz", {}).get("pn_dbc_hz")
            return f"1KHz PN {_fmt(val)} dBc/Hz" if isinstance(val, (int, float)) else "—"
        if name == "TX 增益 + 输出功率":
            pout = data.get("tx_pout_dbm", [])
            avg = sum(pout) / len(pout) if pout else None
            return f"平均 Pout {_fmt(avg)} dBm" if isinstance(avg, (int, float)) else "—"
        if name == "TX 平坦度 + 相位噪声":
            flat = data.get("tx_flatness_db")
            return f"平坦度 {_fmt(flat)} dB" if isinstance(flat, (int, float)) else "—"
        if name == "收发干扰":
            delta = data.get("noise_delta_max")
            return f"最大差异 {_fmt(delta)} dB" if isinstance(delta, (int, float)) else "—"
        return ""

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ========================================================================
    #  Buttons / export
    # ========================================================================

    def _update_button_state(self):
        has_data = len(self._results) > 0
        self._btn_export_json.setEnabled(has_data)
        self._btn_export_csv.setEnabled(has_data)
        self._btn_clear.setEnabled(has_data)

    def _on_export_json(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 JSON", f"测试结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.results(), f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已保存: {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", f"测试结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            rows = self._flatten_for_csv()
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["测试项目", "指标名", "值", "单位", "结果"])
                for row in rows:
                    writer.writerow(row)
            QMessageBox.information(self, "导出成功", f"已保存: {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _flatten_for_csv(self) -> List[List[Any]]:
        rows = []
        for name, r in self._results.items():
            passed = "PASS" if r["passed"] else "FAIL"
            data = r.get("data", {})
            if name == "RX 噪声系数 + 增益":
                freqs = data.get("nf_freqs", [])
                for i, f in enumerate(freqs):
                    nf = data.get("nf_list", [])
                    gain = data.get("gain_list", [])
                    rows.append([name, f"NF @ {f}GHz", nf[i] if i < len(nf) else "", "dB", passed])
                    rows.append([name, f"Gain @ {f}GHz", gain[i] if i < len(gain) else "", "dB", passed])
                rows.append([name, "NF最大值", data.get("nf_max_db", ""), "dB", passed])
                rows.append([name, "NF平均值", data.get("nf_mean_db", ""), "dB", passed])
                rows.append([name, "Gain平均值", data.get("gain_mean_db", ""), "dB", passed])
                rows.append([name, "Gain平坦度", data.get("gain_flatness_db", ""), "dB", passed])
            elif name == "RX 相位噪声":
                spots = data.get("rx_pn_spots", {})
                for label, entry in spots.items():
                    rows.append([name, f"PN {label}", entry.get("pn_dbc_hz", ""), "dBc/Hz", passed])
                rows.append([name, "接收电流", data.get("rx_current_a", ""), "A", passed])
            elif name == "TX 增益 + 输出功率":
                freqs = data.get("tx_freqs_mhz", [])
                for i, f in enumerate(freqs):
                    pout = data.get("tx_pout_dbm", [])
                    gain = data.get("tx_gain_db", [])
                    curr = data.get("tx_current_a", [])
                    rows.append([name, f"Pout @ {f}MHz", pout[i] if i < len(pout) else "", "dBm", passed])
                    rows.append([name, f"Gain @ {f}MHz", gain[i] if i < len(gain) else "", "dB", passed])
                    rows.append([name, f"电流 @ {f}MHz", curr[i] if i < len(curr) else "", "A", passed])
                rows.append([name, "峰值电流", data.get("tx_peak_current_a", ""), "A", passed])
            elif name == "TX 平坦度 + 相位噪声":
                rows.append([name, "发射平坦度", data.get("tx_flatness_db", ""), "dB", passed])
                spots = data.get("tx_pn_spots", {})
                for label, entry in spots.items():
                    rows.append([name, f"PN {label}", entry.get("pn_dbc_hz", ""), "dBc/Hz", passed])
            elif name == "收发干扰":
                freqs = data.get("rx_if_freqs_mhz", [])
                for i, f in enumerate(freqs):
                    off = data.get("rx_noise_tx_off", [])
                    on = data.get("rx_noise_tx_on", [])
                    dlt = data.get("noise_deltas", [])
                    rows.append([name, f"TXOFF噪底 @ {f}MHz", off[i] if i < len(off) else "", "dBm/Hz", passed])
                    rows.append([name, f"TXON噪底 @ {f}MHz", on[i] if i < len(on) else "", "dBm/Hz", passed])
                    rows.append([name, f"差异 @ {f}MHz", dlt[i] if i < len(dlt) else "", "dB", passed])
                rows.append([name, "最大差异", data.get("noise_delta_max", ""), "dB", passed])
            else:
                for k, v in data.items():
                    rows.append([name, k, str(v), "", passed])
        return rows
