"""
Test 4 (order in original): TX Gain and Output Power.
Mirrors SubProcess4_TestTXGain_Pout.m
"""

import time
import numpy as np
from .base import TestBase, TestResult
from .plugin import register_test


@register_test(id="tx_gain", name="TX 增益 + 输出功率", category="tx", order=3)
def run_tx_gain(base: TestBase) -> TestResult:
    result = TestResult(test_name="TX Gain & Pout")
    cfg = base.cfg.test_tx_gain

    try:
        # ---- prepare VSG ----
        base.vsg.rf_off()
        base.vsg.mod_off()
        base.vsg.set_cw_mode()

        # ---- switches ----
        base.set_switches(cfg.switch_config)
        time.sleep(0.1)

        # ---- load SA template ----
        base.log.info("调用频谱仪模板...")
        base.sa.set_mode_sa()
        time.sleep(1)
        base.sa.load_state(cfg.template_name)
        err = base.sa.check_error()
        if "+0" in err:
            base.log.info("  模板已调用")

        # ---- turn on TX power ----
        base.tx_pwr.set_output(True)
        time.sleep(1)
        base.log.info("发射电源已开启")

        # ---- measure at each test frequency ----
        test_freqs = cfg.test_freqs_mhz
        rf_offset = cfg.rf_offset_mhz
        sa_cfg = cfg.sa
        tx_if_loss = base.cfg.rf_path.tx_if_line_loss
        tx_rf_loss = [a + b for a, b in zip(
            base.cfg.rf_path.tx_rf_line_loss,
            base.cfg.rf_path.tx_rf_line_loss_offset,
        )]

        amps = []
        currents = []

        for kk, if_freq in enumerate(test_freqs):
            rf_freq_mhz = if_freq + rf_offset
            rf_freq_ghz = rf_freq_mhz / 1000.0

            base.vsg.rf_off()
            base.vsg.set_cw(if_freq, cfg.vsg_power_dbm)

            # Configure SA for narrow span around RF
            base.sa.set_mode_sa()
            span = sa_cfg.span_delta_ghz
            base.sa.sa_configure(
                start_ghz=rf_freq_ghz - span,
                stop_ghz=rf_freq_ghz + span,
                rbw_khz=sa_cfg.rbw_khz,
                vbw_khz=sa_cfg.vbw_khz,
                ref_level_dbm=sa_cfg.ref_level_dbm,
                trace_type="WRIT",
            )

            base.vsg.rf_on()
            time.sleep(0.2)

            # Apply line loss offset
            loss_db = tx_rf_loss[kk] if kk < len(tx_rf_loss) else tx_rf_loss[-1]
            base.sa.sa_set_offset(loss_db)
            time.sleep(0.1)

            # Peak search
            freq_ghz, amp_dbm = base.sa.sa_marker_peak()
            amps.append(amp_dbm)
            base.log.info(f"  TX-IF={if_freq}MHz, TX-RF={rf_freq_mhz}MHz, "
                          f"RF功率={amp_dbm:.2f}dBm")

            # Read current
            current = base.tx_pwr.measure_current()
            currents.append(current)
            base.log.info(f"  电流={current:.3f}A")

            # Screenshot
            ss = base.screenshot(
                f"{base.cfg.serial_number}_TX-Pout_@{rf_freq_ghz:.2f}GHz.png"
            )
            if ss:
                result.screenshots.append(ss)

            time.sleep(0.5)

        # ---- store ----
        result.data["tx_pout_dbm"] = amps
        result.data["tx_current_a"] = currents
        result.data["tx_freqs_mhz"] = test_freqs

        # Compute gain
        vsg_pwr = cfg.vsg_power_dbm
        gains = [a - vsg_pwr for a in amps]
        result.data["tx_gain_db"] = gains

        # ---- evaluate ----
        limits = cfg.limits
        messages = []
        passed = True

        for kk, if_freq in enumerate(test_freqs):
            ok = amps[kk] >= limits.pout_min_dbm and gains[kk] >= limits.gain_min_db
            messages.append(
                f"TX @{if_freq}MHz: Pout={amps[kk]:.2f}dBm (限≥{limits.pout_min_dbm}), "
                f"Gain={gains[kk]:.2f}dB (限≥{limits.gain_min_db}) {'PASS' if ok else 'FAIL'}"
            )
            passed = passed and ok

        result.data["tx_peak_current_a"] = float(np.max(currents))
        result.passed = passed
        result.messages = messages

        # ---- cleanup ----
        base.vsg.rf_off()
        base.tx_pwr.set_output(False)

    except Exception as e:
        result.passed = False
        result.messages.append(f"测试异常: {e}")
        base.log.error(f"TX Gain 测试异常: {e}")

    finally:
        base.sa.clear_markers()

    return result
