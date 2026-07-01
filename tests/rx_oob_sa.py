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
    pn_cfg = base.cfg.test_rx_pn  # use RX PN switch path

    try:
        base.log.info("─" * 40)
        base.log.info("  [SA 模式] 带外抑制测试 (待验证)")
        base.log.info("─" * 40)

        # ---- switches & power ---- (use RX PN switch path: [0,0,0,0])
        base.set_switches(pn_cfg.switch_config)
        base.rx_pwr.set_output(True)
        time.sleep(0.3)
        base.log.info("接收电源已开启")

        # ---- VSG: CW at 3.6 GHz into RF IN ----
        oob_rf_mhz = 3600.0
        vsg_power = -30.0   # low enough not to saturate
        base.vsg.rf_off()
        base.vsg.set_cw(oob_rf_mhz, vsg_power)
        base.vsg.rf_on()
        base.log.info(f"信号源: {oob_rf_mhz:.0f} MHz / {vsg_power:.1f} dBm")

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
        time.sleep(0.5)
        freq_mhz, amp_dbm = base.sa.sa_marker_peak()

        # Gain = Pout (SA) − Pin (VSG) − line loss
        rf_loss = base.cfg.rf_path.tx_rf_line_loss
        rf_loss_avg = sum(rf_loss) / len(rf_loss) if rf_loss else 0
        sa_gain_db = amp_dbm - vsg_power - rf_loss_avg

        base.log.info(f"  [SA 模式] IF {freq_mhz:.1f} MHz 峰值: {amp_dbm:.2f} dBm")
        base.log.info(f"  [SA 模式] 带外增益: {sa_gain_db:.2f} dB (Pin={vsg_power:.1f}, 线损{rf_loss_avg:.1f})")
        base.log.info("─" * 40)

        # ---- power off ----
        base.vsg.rf_off()
        base.rx_pwr.set_output(False)

        result.passed = True
        result.messages = ["待验证 — 仅日志输出"]
        result.data["oob_sa_gain_db"] = sa_gain_db
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
