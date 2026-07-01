"""
Test: RX Out-of-Band Rejection (SA mode, standalone).
Uses spectrum analyzer in SA mode to measure gain at IF 1.55 GHz (RF 3.6 GHz).
Results logged only — not written to result.data or reports.
"""

import time
from .base import TestBase, TestResult
from .plugin import register_test


@register_test(id="rx_oob_sa", name="RX 带外抑制(SA)", category="rx", order=1, include_in_run_all=False)
def run_rx_oob_sa(base: TestBase) -> TestResult:
    result = TestResult(test_name="RX 带外抑制 (SA)")
    cfg = base.cfg.test_rx_oob_sa

    try:
        base.log.info("─" * 40)
        base.log.info("  [SA 模式] 带外抑制测试 (待验证)")
        base.log.info("─" * 40)

        # ---- switches & power ----
        base.set_switches(cfg.switch_config)
        base.rx_pwr.set_output(True)
        time.sleep(0.3)
        base.log.info("接收电源已开启")

        # ---- SA mode: measure marker peak at IF 1.55 GHz ----
        base.sa.set_mode_sa()
        time.sleep(0.5)
        oob_if_mhz = 1550.0
        base.sa.sa_configure_mhz(
            start_mhz=oob_if_mhz - 10,
            stop_mhz=oob_if_mhz + 10,
            rbw_khz=30,
            vbw_khz=30,
            ref_level_dbm=-10,
        )
        base.sa.inst.write("*CLS")
        time.sleep(0.3)
        freq_mhz, amp_dbm = base.sa.sa_marker_peak()

        base.log.info(f"  [SA 模式] IF {freq_mhz:.1f} MHz 峰值功率: {amp_dbm:.2f} dBm")
        base.log.info("─" * 40)

        # ---- power off ----
        base.rx_pwr.set_output(False)

        result.passed = True
        result.messages = ["待验证 — 仅日志输出"]
        result.data["oob_sa_peak_dbm"] = amp_dbm
        result.data["oob_sa_freq_mhz"] = freq_mhz

    except Exception as e:
        result.passed = False
        result.messages.append(f"测试异常: {e}")
        base.log.error(f"SA 带外抑制测试异常: {e}")

    finally:
        base.sa.clear_markers()
        if base.stop_requested:
            base.safe_shutdown()

    return result
