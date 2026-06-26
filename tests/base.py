"""
Base class for all test modules.
Provides instrument references, logging, screenshot helper, and result dict.
"""

import os
import time
from typing import Any, Dict
from dataclasses import dataclass, field

from instruments.power_supply import PowerSupply
from instruments.signal_generator import SignalGenerator
from instruments.spectrum_analyzer import SpectrumAnalyzer
from instruments.switch_matrix import SwitchMatrix


@dataclass
class TestResult:
    """Structured result from a single test module."""
    test_name: str = ""
    passed: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    messages: list = field(default_factory=list)
    screenshots: list = field(default_factory=list)


class TestBase:
    """Shared context for all test sub-processes."""

    def __init__(
        self,
        rx_pwr: PowerSupply,
        tx_pwr: PowerSupply,
        vsg: SignalGenerator,
        sa: SpectrumAnalyzer,
        switch: SwitchMatrix,
        config,
        logger=None,
    ):
        self.rx_pwr = rx_pwr
        self.tx_pwr = tx_pwr
        self.vsg = vsg
        self.sa = sa
        self.switch = switch
        self.cfg = config
        self.log = logger or _SimpleLogger()
        self._stop_flag: callable = lambda: False

    # ---- stop control ------------------------------------------------------

    def set_stop_check(self, fn: callable):
        """Accept a callback that returns True when stop is requested."""
        self._stop_flag = fn or (lambda: False)

    @property
    def stop_requested(self) -> bool:
        return self._stop_flag()

    def safe_shutdown(self):
        """Emergency instrument shutdown — safe to call at any time."""
        for obj, action in [
            (self.vsg, "rf_off"),
            (self.rx_pwr, "off"),
            (self.tx_pwr, "off"),
        ]:
            if obj is None:
                continue
            try:
                if action == "rf_off":
                    obj.rf_off()
                    obj.set_cw_mode()
                else:
                    obj.set_output(False)
            except Exception:
                pass

    # ---- helpers -----------------------------------------------------------

    def screenshot(self, local_filename: str) -> str | None:
        """Capture SA screenshot if enabled.  Saved under per-SN subfolder."""
        if not self.cfg.screenshot.enabled:
            return None
        try:
            sn = self.cfg.get("serial_number", "UNKNOWN")
            local_dir = self.cfg.get("screenshot.local_dir", "output/screenshots")
            path = self.sa.screenshot(
                local_dir=os.path.join(local_dir, sn),
                local_filename=local_filename,
                theme=self.cfg.screenshot.theme,
                internal_path=self.cfg.screenshot.instrument_internal_path,
            )
            self.log.info(f"截图已保存: {path}")
            return path
        except Exception as e:
            self.log.warning(f"截图失败: {e}")
            return None

    def set_switches(self, sw_config):
        """Set switch matrix from config list [SW1, SW2, SW3, SW4]."""
        if len(sw_config) >= 4:
            self.switch.set_udc_switches(*sw_config[:4])
        elif len(sw_config) == 3:
            self.switch.set_udc_switches(*sw_config, 0)
        time.sleep(0.1)

    def ensure_sa_mode(self, mode: str):
        """Switch SA to mode if needed."""
        if mode == "SA":
            self.sa.set_mode_sa()
        elif mode == "NF":
            self.sa.set_mode_nf()
        elif mode == "PN":
            self.sa.set_mode_pn()
        time.sleep(0.5)

    def _ok(self, condition: bool, msg: str) -> bool:
        if condition:
            self.log.info(f"  PASS: {msg}")
        else:
            self.log.warning(f"  FAIL: {msg}")
        return condition


class _SimpleLogger:
    """Minimal logger fallback."""

    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARN] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
