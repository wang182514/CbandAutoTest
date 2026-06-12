"""
Test 2: RX Phase Noise.
Mirrors SubProcess2_TestRXPN.m
"""

import time
from .base import TestBase, TestResult


def run_rx_pn(base: TestBase) -> TestResult:
    result = TestResult(test_name="RX Phase Noise")
    cfg = base.cfg.test_rx_pn

    try:
        # ---- load PN template ----
        base.log.info("加载相位噪声模板...")
        base.sa.set_mode_pn()
        time.sleep(1)
        base.sa.load_state(cfg.template_name)
        err = base.sa.check_error()
        if "+0" in err:
            base.log.info("  模板已调用")

        base.sa.pn_set_center_freq(cfg.center_freq_ghz)
        time.sleep(0.5)

        # ---- configure VSG ----
        base.vsg.set_cw(cfg.vsg_freq_mhz, cfg.vsg_power_dbm)
        base.vsg.mod_off()
        base.vsg.rf_on()
        time.sleep(0.5)

        # ---- set switches ----
        base.set_switches(cfg.switch_config)

        # ---- turn on RX power ----
        base.rx_pwr.set_output(True)
        time.sleep(0.2)
        state = base.rx_pwr.get_output_state()
        if state:
            base.log.info("接收电源已开启")
        else:
            base.log.warning("接收电源开启失败")
        time.sleep(0.5)

        # ---- measure PN ----
        base.log.info("正在测量相位噪声...")
        base.sa.pn_init_measurement()
        time.sleep(1)

        pn_data = {}
        pn_offsets = cfg.pn_offsets
        for idx, (label, info) in enumerate(pn_offsets.items(), start=1):
            offset_hz, pn_val = base.sa.pn_read_spot(idx)
            pn_data[label] = {"offset_hz": offset_hz, "pn_dbc_hz": pn_val}
            base.log.info(f"  OFST={offset_hz/1000:.1f}KHz, PN={pn_val:.3f} dBc/Hz")
        result.data["rx_pn_spots"] = pn_data

        # ---- screenshot ----
        ss = base.screenshot(f"{base.cfg.serial_number}_RX-PhaseNoise.png")
        if ss:
            result.screenshots.append(ss)

        # ---- read current & power off ----
        rx_current = base.rx_pwr.measure_current()
        result.data["rx_current_a"] = rx_current
        base.log.info(f"接收电流: {rx_current:.3f} A")
        base.rx_pwr.set_output(False)
        base.vsg.rf_off()

        # ---- evaluate ----
        messages = []
        passed = True
        for label, info in pn_offsets.items():
            val = pn_data[label]["pn_dbc_hz"]
            limit = info["limit_dbc_hz"]
            ok = val < limit
            messages.append(f"RX PN {label}: {val:.2f} dBc/Hz (限 {limit} dBc/Hz) {'PASS' if ok else 'FAIL'}")
            passed = passed and ok

        result.passed = passed
        result.messages = messages

    except Exception as e:
        result.passed = False
        result.messages.append(f"测试异常: {e}")
        base.log.error(f"RX PN 测试异常: {e}")

    finally:
        base.sa.clear_markers()

    return result
