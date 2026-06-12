"""
Test 5: TX-RX Interference (发射对接收的影响).
Mirrors SubProcess5_TestRXInfluence.m
"""

import time
import numpy as np
from .base import TestBase, TestResult


def run_tx_rx_influence(base: TestBase) -> TestResult:
    result = TestResult(test_name="TX-RX Interference")
    cfg = base.cfg.test_tx_rx_influence

    try:
        # ---- switches ----
        base.set_switches(cfg.switch_config)
        time.sleep(0.1)

        tx_if_freqs = cfg.tx_if_freqs_mhz
        rx_if_freqs = cfg.rx_if_freqs_mhz
        sa_cfg = cfg.sa

        noise_off_list = []
        noise_on_list = []

        for kk in range(len(tx_if_freqs)):
            rx_freq = rx_if_freqs[kk]
            tx_freq = tx_if_freqs[kk]

            base.log.info(f"测试: TX_IF={tx_freq}MHz → RX_IF={rx_freq}MHz")

            # Configure VSG
            base.vsg.rf_off()
            base.vsg.mod_off()
            base.vsg.set_cw(tx_freq, cfg.vsg_power_dbm)
            base.vsg.set_cw_mode()

            # Power: RX on, TX off
            base.rx_pwr.set_output(True)
            base.tx_pwr.set_output(False)
            time.sleep(0.5)

            base.vsg.rf_on()

            # Configure SA for narrow span around RX IF
            span_mhz = sa_cfg.span_mhz
            base.sa.set_mode_sa()
            base.sa.sa_set_offset(0)
            base.sa.sa_configure_mhz(
                start_mhz=rx_freq - span_mhz,
                stop_mhz=rx_freq + span_mhz,
                rbw_khz=sa_cfg.rbw_khz,
                vbw_khz=sa_cfg.vbw_khz,
                ref_level_dbm=sa_cfg.ref_level_dbm,
                trace_type="WRIT",
            )

            # ---- TX OFF: measure noise ----
            base.tx_pwr.set_output(False)
            time.sleep(1)
            noise_off = base.sa.sa_marker_noise(rx_freq)
            noise_off_list.append(noise_off)
            base.log.info(f"  未开发射噪底: {noise_off:.3f} dBm/Hz")

            ss = base.screenshot(
                f"{base.cfg.serial_number}_RX-NoiseFloor_TXOFF_@{rx_freq}MHz.png"
            )
            if ss:
                result.screenshots.append(ss)

            # ---- TX ON: measure noise ----
            base.tx_pwr.set_output(True)
            base.log.info("  等待发射稳定...")
            for jj in range(10, 0, -1):
                time.sleep(1)
                base.log.info(f"    {jj}s")

            noise_on = base.sa.sa_marker_noise(rx_freq)
            noise_on_list.append(noise_on)
            base.log.info(f"  开发射噪底: {noise_on:.3f} dBm/Hz")

            ss = base.screenshot(
                f"{base.cfg.serial_number}_RX-NoiseFloor_TXON_@{rx_freq}MHz.png"
            )
            if ss:
                result.screenshots.append(ss)

            base.log.info(
                f"  噪底对比: TXOFF={noise_off:.3f}, TXON={noise_on:.3f} dBm/Hz"
            )

        # ---- store ----
        result.data["rx_noise_tx_off"] = noise_off_list
        result.data["rx_noise_tx_on"] = noise_on_list
        result.data["rx_if_freqs_mhz"] = rx_if_freqs

        # ---- evaluate ----
        deltas = [abs(on - off) for on, off in zip(noise_on_list, noise_off_list)]
        result.data["noise_deltas"] = deltas
        max_delta = float(np.max(deltas))
        result.data["noise_delta_max"] = max_delta

        limit = cfg.limit.noise_floor_delta_db
        passed = max_delta <= limit

        messages = [
            f"噪底差异最大值: {max_delta:.2f} dB (限 {limit} dB) {'PASS' if passed else 'FAIL'}"
        ]

        # ---- cleanup ----
        base.vsg.rf_off()
        base.rx_pwr.set_output(False)
        base.tx_pwr.set_output(False)

        result.passed = passed
        result.messages = messages

    except Exception as e:
        result.passed = False
        result.messages.append(f"测试异常: {e}")
        base.log.error(f"TX-RX Interference 测试异常: {e}")

    finally:
        base.sa.clear_markers()

    return result
