"""
Test 3 (order in original): TX Flatness and TX Phase Noise.
Mirrors SubProcess3_TestTXFlatness_PN.m
"""

import time
from .base import TestBase, TestResult


def run_tx_flatness_pn(base: TestBase) -> TestResult:
    result = TestResult(test_name="TX Flatness & Phase Noise")
    cfg = base.cfg.test_tx_flatness_pn

    try:
        # ============ Part A: TX Flatness ==================================

        # ---- load SA flatness template ----
        base.log.info("调用频谱仪模板 (发射平坦度)...")
        base.sa.set_mode_sa()
        time.sleep(0.5)
        base.sa.load_state(cfg.flatness_template)
        err = base.sa.check_error()
        if "+0" in err:
            base.log.info("  模板已调用")
        time.sleep(0.5)

        # ---- prepare VSG ----
        base.vsg.rf_off()
        base.vsg.mod_off()

        # ---- switches ----
        base.set_switches(cfg.switch_config)

        # ---- power supplies ----
        base.rx_pwr.set_output(False)
        time.sleep(0.2)
        base.tx_pwr.set_output(True)
        time.sleep(0.2)
        base.log.info("发射电源已开启")
        time.sleep(0.5)

        # ---- configure VSG sweep ----
        sweep = cfg.sweep
        base.log.info("配置信号源扫频...")
        base.vsg.configure_sweep(
            start_ghz=sweep.if_start_ghz,
            stop_ghz=sweep.if_stop_ghz,
            step_khz=sweep.step_khz,
            dwell_ms=sweep.dwell_ms,
            power_dbm=cfg.vsg_power_dbm,
        )
        base.vsg.rf_on()
        base.log.info("扫频已启动")

        # ---- SA for flatness ----
        sa_f = cfg.sa_flatness
        base.sa.set_mode_sa()
        base.sa.sa_set_offset(0)
        base.sa.sa_configure(
            start_ghz=sa_f.rf_start_ghz,
            stop_ghz=sa_f.rf_stop_ghz,
            rbw_khz=sa_f.rbw_khz,
            vbw_khz=sa_f.vbw_khz,
            ref_level_dbm=sa_f.ref_level_dbm,
            trace_type="MAXH",
        )

        # ---- wait for max hold ----
        wait_sec = sa_f.max_hold_wait_sec
        for kk in range(wait_sec, 0, -1):
            time.sleep(1)
            base.log.info(f"  Max Hold 等待中... {kk}s")

        # ---- peak-to-peak measurement ----
        flatness_db = base.sa.sa_marker_ptp()
        flatness_db = abs(flatness_db)
        result.data["tx_flatness_db"] = flatness_db
        base.log.info(f"发射平坦度: {flatness_db:.2f} dB")

        ok_flat = flatness_db < cfg.limits.flatness_db
        base.log.info(f"  {'PASS' if ok_flat else 'FAIL'} (限 {cfg.limits.flatness_db} dB)")

        # ---- screenshot flatness ----
        ss = base.screenshot(f"{base.cfg.serial_number}_TX-Flatness.png")
        if ss:
            result.screenshots.append(ss)

        # ============ Part B: TX Phase Noise ==============================  =

        base.log.info("测量发射相位噪声...")
        base.vsg.rf_off()
        base.vsg.mod_off()
        base.vsg.set_cw_mode()
        base.vsg.set_cw(cfg.sa_pn.vsg_freq_mhz, cfg.sa_pn.vsg_power_dbm)
        base.vsg.rf_on()
        time.sleep(0.5)

        # Load PN template
        base.sa.set_mode_pn()
        time.sleep(1)
        base.sa.load_state(cfg.pn_template)
        err = base.sa.check_error()
        if "+0" in err:
            base.log.info("  PN模板已调用")

        base.sa.pn_set_center_freq(cfg.sa_pn.center_freq_ghz)
        time.sleep(3)

        # Measure
        base.sa.pn_init_measurement()
        time.sleep(1)

        pn_data = {}
        limits = cfg.limits
        pn_labels = [
            ("100Hz", limits.pn_100Hz_dbc_hz),
            ("1KHz", limits.pn_1KHz_dbc_hz),
            ("10KHz", limits.pn_10KHz_dbc_hz),
            ("100KHz", limits.pn_100KHz_dbc_hz),
        ]
        for idx, (label, limit_db) in enumerate(pn_labels, start=1):
            offset_hz, pn_val = base.sa.pn_read_spot(idx)
            pn_data[label] = {"offset_hz": offset_hz, "pn_dbc_hz": pn_val}
            base.log.info(f"  TX PN {label}: {pn_val:.3f} dBc/Hz (限 {limit_db})")
        result.data["tx_pn_spots"] = pn_data

        # Screenshot
        ss = base.screenshot(f"{base.cfg.serial_number}_TX-PhaseNoise.png")
        if ss:
            result.screenshots.append(ss)

        # ---- cleanup ----
        base.vsg.rf_off()
        base.tx_pwr.set_output(False)

        # ---- evaluate ----
        messages = []
        passed = ok_flat

        messages.append(
            f"发射平坦度: {flatness_db:.2f} dB (限 {cfg.limits.flatness_db} dB) "
            f"{'PASS' if ok_flat else 'FAIL'}"
        )

        for label, limit_db in pn_labels:
            val = pn_data[label]["pn_dbc_hz"]
            ok = val < limit_db
            messages.append(
                f"TX PN {label}: {val:.2f} dBc/Hz (限 {limit_db}) "
                f"{'PASS' if ok else 'FAIL'}"
            )
            passed = passed and ok

        result.passed = passed
        result.messages = messages

    except Exception as e:
        result.passed = False
        result.messages.append(f"测试异常: {e}")
        base.log.error(f"TX Flatness/PN 测试异常: {e}")

    finally:
        base.sa.clear_markers()

    return result
