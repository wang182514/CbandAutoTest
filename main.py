#!/usr/bin/env python
"""
C波段射频模块自动化测试系统 — 主入口
==========================================
用法:
    python main.py                    # 启动 GUI
    python main.py --headless all     # 命令行运行全部测试 (无 UI)
    python main.py --headless rx_nf   # 仅运行指定测试
"""

import os
import sys
import argparse

# Ensure the project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config.config_manager import ConfigManager


def run_headless(test_names: list):
    """Command-line mode — no GUI."""
    from instruments.power_supply import PowerSupply
    from instruments.signal_generator import SignalGenerator
    from instruments.spectrum_analyzer import SpectrumAnalyzer
    from instruments.switch_matrix import SwitchMatrix
    from tests.base import TestBase
    from ui.test_runner import TEST_REGISTRY

    # Load config
    defaults = os.path.join(PROJECT_ROOT, "config", "default_settings.json")
    user = os.path.join(PROJECT_ROOT, "config", "user_settings.json")
    cfg = ConfigManager(defaults)
    if os.path.exists(user):
        cfg.load(user)

    inst = cfg.data.instruments

    # Connect
    print("Connecting instruments...")
    rx_pwr = PowerSupply(ip=inst.rx_power_supply.ip, port=inst.rx_power_supply.port)
    tx_pwr = PowerSupply(ip=inst.tx_power_supply.ip, port=inst.tx_power_supply.port)
    vsg = SignalGenerator(ip=inst.signal_generator.ip, vendor=inst.signal_generator.vendor)
    sa = SpectrumAnalyzer(ip=inst.spectrum_analyzer.ip, vendor=inst.spectrum_analyzer.vendor)
    sw = SwitchMatrix(com_port=inst.switch_matrix.com_port, baud_rate=inst.switch_matrix.baud_rate)

    rx_pwr.connect()
    print(f"  RX PWR: {rx_pwr.idn}")
    tx_pwr.connect()
    print(f"  TX PWR: {tx_pwr.idn}")
    vsg.connect()
    print(f"  VSG: OK")
    sa.connect()
    print(f"  SA: OK")
    sw.connect()
    print(f"  Switch: {inst.switch_matrix.com_port}")

    base = TestBase(
        rx_pwr=rx_pwr,
        tx_pwr=tx_pwr,
        vsg=vsg,
        sa=sa,
        switch=sw,
        config=cfg,
    )

    all_names = list(TEST_REGISTRY.keys())
    to_run = test_names if test_names and test_names != ["all"] else all_names

    for name in to_run:
        if name not in TEST_REGISTRY:
            print(f"Unknown test: {name}")
            continue
        display_name, runner = TEST_REGISTRY[name]
        print(f"\n{'='*50}")
        print(f"Running: {display_name}")
        print(f"{'='*50}")
        result = runner(base)
        status = "PASS" if result.passed else "FAIL"
        print(f"\n{display_name}: {status}")
        for msg in result.messages:
            print(f"  {msg}")

    # Disconnect
    for obj in [rx_pwr, tx_pwr, vsg, sa, sw]:
        obj.disconnect()
    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(description="C波段射频模块自动化测试系统")
    parser.add_argument(
        "--headless",
        nargs="+",
        help="命令行模式：指定测试名称 (rx_nf, rx_pn, tx_gain, tx_flatness_pn, tx_rx_influence) 或 'all'",
    )
    args = parser.parse_args()

    if args.headless:
        run_headless(args.headless)
    else:
        from PySide6.QtWidgets import QApplication
        from ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        win = MainWindow()
        win.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
