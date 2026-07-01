"""
Test: RX Out-of-Band Rejection (SA mode, standalone).
Signal generator → RF IN (3.6 GHz CW), SA → RX IF (1.55 GHz).
Fixed-frequency marker measurement; long delays for debug observation.
Results logged only — not written to result.data or reports.
"""

import time
from .base import TestBase, TestResult
from .plugin import register_test


@register_test(id="rx_oob_sa", name="RX 带外抑制(SA)", category="rx", order=1, include_in_run_all=False)
def run_rx_oob_sa(base: TestBase) -> TestResult:
    result = TestResult(test_name="RX 带外抑制 (SA)")
    cfg = base.cfg.test_rx_oob_sa
    pn_cfg = base.cfg.test_rx_pn

    try:
        base.log.info("=" * 50)
        base.log.info("  SA 模式 — 带外抑制测试 (调试模式)")
        base.log.info("=" * 50)

        # ── step 1: switches ───────────────────────────────────────
        base.log.info(f"[1/6] 设置开关: {pn_cfg.switch_config}")
        base.set_switches(pn_cfg.switch_config)
        time.sleep(1.0)
        base.log.info("      开关已设置")

        # ── step 2: RX power on ────────────────────────────────────
        base.log.info("[2/6] 开启接收电源 (12V)...")
        base.rx_pwr.set_output(True)
        time.sleep(2.0)
        v = base.rx_pwr.measure_voltage()
        c = base.rx_pwr.measure_current()
        base.log.info(f"      电压: {v:.2f} V, 电流: {c:.3f} A")

        # ── step 3: VSG on ─────────────────────────────────────────
        oob_rf_mhz = 3600.0
        vsg_power = -30.0
        base.log.info(f"[3/6] 开启信号源: {oob_rf_mhz:.0f} MHz / {vsg_power:.1f} dBm")
        base.vsg.rf_off()
        base.vsg.set_cw(oob_rf_mhz, vsg_power)
        time.sleep(1.0)
        base.vsg.rf_on()
        time.sleep(2.0)
        base.log.info("      信号源 RF ON")

        # ── step 4: SA configure ───────────────────────────────────
        oob_if_mhz = 1550.0
        base.log.info(f"[4/6] 配置频谱仪: 中心 {oob_if_mhz:.0f} MHz, span ±10 MHz")
        base.log.info("      模式: SA")
        base.sa.set_mode_sa()
        time.sleep(1.5)
        base.sa.sa_configure_mhz(
            start_mhz=oob_if_mhz - 10,
            stop_mhz=oob_if_mhz + 10,
            rbw_khz=30,
            vbw_khz=30,
            ref_level_dbm=-10,
        )
        base.log.info("      SA 参数已配置, 等待稳定...")
        time.sleep(3.0)

        # ── step 5: fixed-frequency marker ─────────────────────────
        base.log.info(f"[5/6] 设置固定频点 marker @ {oob_if_mhz:.0f} MHz")
        base.sa.inst.write("*CLS")
        base.sa.inst.write(":CALCulate:MARKer:AOFF")
        base.sa.inst.write(":CALCulate:MARKer1:STATe ON")
        base.sa.inst.write(f":CALCulate:MARKer1:X {oob_if_mhz:.0f}MHz")
        time.sleep(1.0)
        amp_raw = base.sa.inst.query(":CALCulate:MARKer1:Y?")
        try:
            amp_dbm = float(amp_raw.strip())
        except ValueError:
            amp_dbm = -999
        base.log.info(f"      Marker Y 原始回包: {amp_raw.strip()}")
        base.log.info(f"      Marker Y 解析值: {amp_dbm:.2f} dBm")

        # ── step 6: compute ────────────────────────────────────────
        rf_loss = base.cfg.rf_path.tx_rf_line_loss
        rf_loss_avg = sum(rf_loss) / len(rf_loss) if rf_loss else 0
        sa_gain_db = amp_dbm - vsg_power - rf_loss_avg

        base.log.info(f"[6/6] 计算结果")
        base.log.info(f"      SA读数: {amp_dbm:.2f} dBm")
        base.log.info(f"      VSG功率: {vsg_power:.1f} dBm")
        base.log.info(f"      平均线损: {rf_loss_avg:.1f} dB")
        base.log.info(f"      带外增益 = {amp_dbm:.2f} − ({vsg_power:.1f}) − {rf_loss_avg:.1f} = {sa_gain_db:.2f} dB")
        base.log.info("=" * 50)

        # ── cleanup ────────────────────────────────────────────────
        base.vsg.rf_off()
        base.rx_pwr.set_output(False)
        base.log.info("电源和信号源已关闭")

        result.passed = True
        result.messages = ["调试模式 — 仅日志输出"]
        result.data["oob_sa_gain_db"] = sa_gain_db
        result.data["oob_sa_peak_dbm"] = amp_dbm
        result.data["oob_sa_freq_mhz"] = oob_if_mhz

    except Exception as e:
        result.passed = False
        result.messages.append(f"测试异常: {e}")
        base.log.error(f"SA 带外抑制测试异常: {e}")

    finally:
        base.sa.clear_markers()
        if base.stop_requested:
            base.safe_shutdown()

    return result
