"""
Test: RX Noise Figure, Gain, Flatness + Out-of-Band Rejection.
Uses extended template state_RX_NF2.state covering IF 0.95-1.55 GHz (13 points).

- First 11 points (0.95-1.45 GHz): standard NF/Gain/Flatness evaluation.
- Point at IF 1.55 GHz (RF 3.6 GHz): out-of-band gain → rejection computed
  and logged, but NOT written into result.data or the report.
"""

import time
import numpy as np
from .base import TestBase, TestResult
from .plugin import register_test


@register_test(id="rx_nf_v2", name="RX NF/增益 (带外抑制)", category="rx", order=1, include_in_run_all=False)
def run_rx_nf_v2(base: TestBase) -> TestResult:
    result = TestResult(test_name="RX NF & Gain & Flatness")
    cfg = base.cfg.test_rx_nf_v2

    try:
        # ---- enable SCPI debug for troubleshooting ----
        base.sa.enable_debug(base.log.info)

        # ---- load NF template (extended 0.95-1.55 GHz) ----
        base.log.info("加载噪声系数模板 (state_RX_NF2.state)...")
        base.sa.set_mode_nf()
        time.sleep(1)
        base.sa.load_state(cfg.template_name)
        err = base.sa.check_error()
        if "+0" in err:
            base.log.info("  模板已调用")
        else:
            base.log.warning(f"  模板错误: {err}")
        base.log.warning(cfg.template_name)
        # ---- set switches ----
        base.set_switches(cfg.switch_config)

        # ---- turn on RX power ----
        base.rx_pwr.set_output(True)
        time.sleep(0.2)
        if base.rx_pwr.get_output_state():
            base.log.info("接收电源已开启")
        time.sleep(0.5)

        # ---- single-shot measurement ----
        base.log.info("正在启动单次测量...")
        base.sa.nf_init_measurement()
        base.log.info("  测量完成")

        base.sa.nf_prepare_markers()

        # ---- read NF & Gain at all 13 frequency points ----
        nf_freqs = cfg.nf_freq_list_ghz
        nf_list = []
        gain_list = []
        base.log.info("测量接收噪声系数与增益中...")
        for f in nf_freqs:
            nf = base.sa.nf_set_marker(1, 1, f)
            g = base.sa.nf_set_marker(3, 2, f)
            nf_list.append(nf)
            gain_list.append(g)
            base.log.info(f"  频率:{f:.2f}GHz, NF: {nf:.3f} dB, Gain: {g:.3f} dB")

        # ---- split: in-band (first 11) vs out-of-band (IF 1.55 GHz) ----
        nf_inband = nf_list[:11]
        gain_inband = gain_list[:11]
        gain_oob = gain_list[12] if len(gain_list) > 12 else None   # IF 1.55 GHz

        result.data["nf_list"] = nf_inband
        result.data["gain_list"] = gain_inband
        result.data["nf_freqs"] = nf_freqs[:11]  # only in-band freqs in report

        # ---- screenshot ----
        ss = base.screenshot(f"{base.cfg.serial_number}_RX-NF-Gain-v2.png")
        if ss:
            result.screenshots.append(ss)

        # ---- turn off RX power ----
        base.rx_pwr.set_output(False)
        time.sleep(0.2)
        base.log.info(f"  电源状态: {'开启' if base.rx_pwr.get_output_state() else '关闭'}")

        # ---- evaluate in-band (11 points, same logic as rx_nf) ----
        limits = cfg.limits
        nf_arr = np.array(nf_inband)
        gain_arr = np.array(gain_inband)

        messages = []
        passed = True

        nf_max = float(np.max(nf_arr))
        result.data["nf_max_db"] = nf_max
        ok = nf_max <= limits.nf_max_db
        messages.append(f"NF最大值: {nf_max:.2f} dB (限 {limits.nf_max_db} dB) {'PASS' if ok else 'FAIL'}")
        passed = passed and ok

        nf_mean = float(np.mean(nf_arr))
        result.data["nf_mean_db"] = nf_mean
        ok = nf_mean < limits.nf_mean_db
        messages.append(f"NF平均值: {nf_mean:.2f} dB (限 {limits.nf_mean_db} dB) {'PASS' if ok else 'FAIL'}")
        passed = passed and ok

        gain_mean = float(np.mean(gain_arr))
        result.data["gain_mean_db"] = gain_mean
        ok = gain_mean > limits.gain_mean_db
        messages.append(f"增益平均值: {gain_mean:.2f} dB (限 {limits.gain_mean_db} dB) {'PASS' if ok else 'FAIL'}")
        passed = passed and ok

        gain_trimmed = gain_arr[1:-1]
        if len(gain_trimmed) > 1:
            gain_diff = float(np.max(np.abs(np.diff(gain_trimmed))))
        else:
            gain_diff = 0.0
        result.data["gain_flatness_db"] = gain_diff

        result.data["limits"] = {
            "nf_max_db": limits.nf_max_db,
            "nf_mean_db": limits.nf_mean_db,
            "gain_mean_db": limits.gain_mean_db,
            "gain_flatness_db": limits.gain_flatness_db,
        }

        ok = gain_diff < limits.gain_flatness_db
        messages.append(f"增益平坦度: {gain_diff:.2f} dB (限 {limits.gain_flatness_db} dB) {'PASS' if ok else 'FAIL'}")
        passed = passed and ok

        # ---- out-of-band rejection (LOG ONLY, not in result.data) ----
        if gain_oob is not None:
            rejection_db = gain_mean - gain_oob
            base.log.info("─" * 30)
            base.log.info(f"  带外 (IF 1.55GHz / RF 3.6GHz) 增益: {gain_oob:.2f} dB")
            base.log.info(f"  带内平均增益: {gain_mean:.2f} dB")
            base.log.info(f"  带外抑制: {rejection_db:.2f} dB (限 ≥ {limits.rejection_min_db} dB)")
            base.log.info("─" * 30)
        else:
            base.log.warning("  未能读取 IF 1.55 GHz 增益，跳过带外抑制计算")

        result.passed = passed
        result.messages = messages

    except Exception as e:
        result.passed = False
        result.messages.append(f"测试异常: {e}")
        base.log.error(f"RX NF v2 测试异常: {e}")

    finally:
        base.sa.clear_markers()
        if base.stop_requested:
            base.safe_shutdown()

    return result
