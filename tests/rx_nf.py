"""
Test 1: RX Noise Figure, Gain, and Flatness.
Mirrors SubProcess1_TestRXNF.m
"""

import time
import numpy as np
from .base import TestBase, TestResult
from .plugin import register_test


@register_test(id="rx_nf", name="RX 噪声系数 + 增益", category="rx", order=1)
def run_rx_nf(base: TestBase) -> TestResult:
    result = TestResult(test_name="RX NF & Gain & Flatness")
    cfg = base.cfg.test_rx_nf

    try:
        # ---- load NF template ----
        base.log.info("加载噪声系数模板...")
        base.sa.set_mode_nf()
        time.sleep(1)
        base.sa.load_state(cfg.template_name)
        err = base.sa.check_error()
        if "+0" in err:
            base.log.info("  模板已调用")
        else:
            base.log.warning(f"  模板错误: {err}")

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

        # ---- read NF at each frequency point ----
        nf_freqs = cfg.nf_freq_list_ghz
        nf_list = []
        base.log.info("测量接收噪声系数中...")
        for f in nf_freqs:
            nf = base.sa.nf_set_marker(1, 1, f)
            nf_list.append(nf)
            base.log.info(f"  频率:{f:.2f}GHz, NF: {nf:.3f} dB")
        result.data["nf_list"] = nf_list
        result.data["nf_freqs"] = nf_freqs

        # ---- read Gain at each frequency point ----
        gain_list = []
        base.log.info("测量接收增益中...")
        for f in nf_freqs:
            g = base.sa.nf_set_marker(3, 2, f)
            gain_list.append(g)
            base.log.info(f"  频率:{f:.2f}GHz, Gain: {g:.3f} dB")
        result.data["gain_list"] = gain_list

        # ---- screenshot ----
        ss = base.screenshot(f"{base.cfg.serial_number}_RX-NF-Gain.png")
        if ss:
            result.screenshots.append(ss)

        # ---- turn off RX power ----
        base.rx_pwr.set_output(False)
        time.sleep(0.2)
        base.log.info(f"  电源状态: {'开启' if base.rx_pwr.get_output_state() else '关闭'}")

        # ---- evaluate ----
        limits = cfg.limits
        nf_arr = np.array(nf_list)
        gain_arr = np.array(gain_list)

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

        # Flatness: max diff between adjacent points (excluding endpoints)
        gain_trimmed = gain_arr[1:-1]
        if len(gain_trimmed) > 1:
            gain_diff = float(np.max(np.abs(np.diff(gain_trimmed))))
        else:
            gain_diff = 0.0
        result.data["gain_flatness_db"] = gain_diff

        # store limits for UI inline display
        result.data["limits"] = {
            "nf_max_db": limits.nf_max_db,
            "nf_mean_db": limits.nf_mean_db,
            "gain_mean_db": limits.gain_mean_db,
            "gain_flatness_db": limits.gain_flatness_db,
        }

        ok = gain_diff < limits.gain_flatness_db
        messages.append(f"增益平坦度: {gain_diff:.2f} dB (限 {limits.gain_flatness_db} dB) {'PASS' if ok else 'FAIL'}")
        passed = passed and ok

        result.passed = passed
        result.messages = messages

    except Exception as e:
        result.passed = False
        result.messages.append(f"测试异常: {e}")
        base.log.error(f"RX NF 测试异常: {e}")

    finally:
        base.sa.clear_markers()

    return result
