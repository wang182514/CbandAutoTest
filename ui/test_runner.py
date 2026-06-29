"""
QThread test runner — runs tests sequentially without blocking the UI.
"""

from PySide6.QtCore import QThread, Signal

from tests.base import TestBase
from tests.plugin import discover

TEST_REGISTRY = discover()


class TestRunner(QThread):
    log_signal = Signal(str)
    result_signal = Signal(str, bool, list, dict)  # test_name, passed, messages, data
    progress_signal = Signal(int, int)          # current, total
    finished_signal = Signal(list)              # all_results

    def __init__(
        self,
        rx_pwr,
        tx_pwr,
        vsg,
        sa,
        switch,
        config,
        test_names: list,
    ):
        super().__init__()
        self._rx_pwr = rx_pwr
        self._tx_pwr = tx_pwr
        self._vsg = vsg
        self._sa = sa
        self._switch = switch
        self._config = config
        self._test_names = test_names
        self._stop_requested = False

    def run(self):
        base = TestBase(
            rx_pwr=self._rx_pwr,
            tx_pwr=self._tx_pwr,
            vsg=self._vsg,
            sa=self._sa,
            switch=self._switch,
            config=self._config,
            logger=_SignalLogger(self.log_signal),
        )
        base.set_stop_check(lambda: self._stop_requested)

        all_results = []
        total = len(self._test_names)

        for idx, name in enumerate(self._test_names):
            if self._stop_requested:
                self.log_signal.emit("=== 用户停止 ===")
                break

            info = TEST_REGISTRY.get(name)
            if info is None:
                display_name = name
                runner = None
            else:
                display_name = info["name"]
                runner = info["runner"]
            if runner is None:
                self.log_signal.emit(f"未知测试: {name}")
                continue

            self.log_signal.emit(f"\n{'='*50}")
            self.log_signal.emit(f"开始: {display_name}")
            self.log_signal.emit(f"{'='*50}")

            try:
                result = runner(base)
                stopped = self._stop_requested
                msgs = list(result.messages)
                if stopped:
                    msgs.insert(0, "⚠ 手动终止 — 测试未完成")
                all_results.append({
                    "name": display_name,
                    "passed": result.passed and not stopped,
                    "stopped": stopped,
                    "messages": msgs,
                    "data": result.data,
                    "screenshots": result.screenshots,
                })
                self.result_signal.emit(display_name, result.passed and not stopped, msgs, result.data)

                if stopped:
                    self.log_signal.emit(f"⊘ {display_name} 已终止")
                elif result.passed:
                    self.log_signal.emit(f"✓ {display_name} PASS")
                else:
                    self.log_signal.emit(f"✗ {display_name} FAIL")

            except Exception as e:
                stopped = self._stop_requested
                prefix = "⚠ 手动终止 → " if stopped else ""
                self.log_signal.emit(f"✗ {display_name} {prefix}异常: {e}")
                all_results.append({
                    "name": display_name,
                    "passed": False,
                    "stopped": stopped,
                    "messages": [f"{prefix}异常: {e}"],
                    "data": {},
                    "screenshots": [],
                })
                self.result_signal.emit(display_name, False, [f"{prefix}异常: {e}"], {})

            self.progress_signal.emit(idx + 1, total)

        self.finished_signal.emit(all_results)

    def request_stop(self):
        self._stop_requested = True


class _SignalLogger:
    """Logger that emits to a Qt signal."""
    def __init__(self, signal: Signal):
        self._signal = signal

    def info(self, msg):
        self._signal.emit(msg)

    def warning(self, msg):
        self._signal.emit(f"[WARN] {msg}")

    def error(self, msg):
        self._signal.emit(f"[ERROR] {msg}")
