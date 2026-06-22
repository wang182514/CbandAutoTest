# C波段射频模块自动化测试系统 — Agent 指南

## 项目定位

本项目是原 MATLAB 版 `CBandAutoTest` 的 Python/PySide6 重构版，用于在产线对 C 波段射频模块执行 5 项自动化测试：

1. RX 噪声系数 + 增益 + 平坦度 (`rx_nf`)
2. RX 相位噪声 (`rx_pn`)
3. TX 增益 + 输出功率 (`tx_gain`)
4. TX 平坦度 + 相位噪声 (`tx_flatness_pn`)
5. TX-RX 收发干扰 (`tx_rx_influence`)

运行环境：**Python 3.12+ / Windows**，依赖真实硬件仪表（Keysight N9020A、R&S SMU200A、TDK-Lambda 电源 ×2、UDC-0624F 开关矩阵）。

## 启动方式

```bash
# GUI 模式
.venv\Scripts\python main.py

# 命令行模式（调试/自动化）
.venv\Scripts\python main.py --headless all
.venv\Scripts\python main.py --headless rx_nf rx_pn
```

## 目录结构

```
cband_autotest/
├── main.py                      # 入口 (GUI / --headless)
├── config/
│   ├── default_settings.json    # 默认配置（受版本控制）
│   ├── user_settings.json       # 用户配置（.gitignore 忽略）
│   └── config_manager.py        # 配置加载/保存/点号访问
├── instruments/                 # 仪器驱动层
│   ├── power_supply.py          # TDK-Lambda TCP SCPI
│   ├── signal_generator.py      # R&S SMU200A via PyVISA
│   ├── spectrum_analyzer.py     # Keysight N9020A via PyVISA
│   └── switch_matrix.py         # UDC-0624F UART
├── tests/                       # 测试执行层
│   ├── base.py                  # TestBase / TestResult / 公共辅助
│   ├── rx_nf.py
│   ├── rx_pn.py
│   ├── tx_gain.py
│   ├── tx_flatness_pn.py
│   └── tx_rx_influence.py
├── ui/                          # PySide6 界面
│   ├── main_window.py           # 主窗口、连接、报告按钮
│   ├── settings_dialog.py       # 8 Tab 设置对话框
│   ├── test_runner.py           # QThread 测试执行器 + TEST_REGISTRY
│   └── results_panel.py         # 当前为空占位
├── utils/
│   ├── logger.py                # 控制台 + 文件日志
│   └── report.py                # TXT / DOCX 报告生成
└── output/
    ├── logs/
    ├── reports/
    └── screenshots/
```

## 核心约定

### 配置系统

- 使用 `ConfigManager` 加载 `default_settings.json`，再叠加 `user_settings.json`。
- 配置支持点号访问：`cfg.instruments.rx_power_supply.ip`。
- 修改配置后调用 `cfg.save(user_settings.json)` 持久化。
- `default_settings.json` 中已包含典型产线参数（IP、模板名、限值、线损等）。

### 仪器对象

所有仪器都提供统一接口：

- `connect()` / `disconnect()` / `is_connected`
- 高频谱仪 `SpectrumAnalyzer` 负责 SA / NF / PN 三种模式切换，以及截图。
- 测试模块不直接创建仪器，而是由 `TestBase` 统一持有引用。

### 测试模块

- 每个测试都是 `def run_xxx(base: TestBase) -> TestResult`。
- 通过 `tests/base.py` 的 `TestBase` 访问仪器、配置、日志、截图、开关设置。
- 测试异常必须捕获，返回 `passed=False` 并在 `messages` 中说明；`finally` 中调用 `base.sa.clear_markers()`。
- 注册表在 `ui/test_runner.py::TEST_REGISTRY`，新增测试需要同步注册。

### UI 与线程

- 测试在 `TestRunner(QThread)` 中执行，通过 Signal 回传日志/结果/进度。
- `MainWindow` 维护 `_all_results`，重复运行同名测试会覆盖旧结果。
- 报告由用户点击「写入报告」手动触发，不会自动在每次测试后生成。

### 报告生成

- `utils/report.py::ReportGenerator` 生成 `测试记录_{SN}.txt` 与 `检验记录_{SN}.docx`。
- DOCX 依赖 `CbandTemplate.docx` 模板，模板应放在项目根目录（与 `main.py` 同级的上一级位置，代码中通过 `..` 查找）。

## 常见开发注意事项

1. **不要修改 `default_settings.json` 中的真实产线默认值**，除非用户明确要求；临时改配置应保存到 `user_settings.json`。
2. **测试模块中始终使用 `base.cfg.xxx` 读取配置**，不要硬编码限值或频率。
3. **新增测试**需要在 `ui/test_runner.py::TEST_REGISTRY` 注册，并在 `ui/main_window.py` 的测试按钮列表中添加对应项。
4. **截图路径** `screenshot.instrument_internal_path` 是 N9020A 仪器内部 Windows 路径，不要随意改成本地路径。
5. **DOCX 模板路径** 当前指向项目根目录上一级 `CbandTemplate.docx`；若模板位置变化需同步 `main_window.py` 中 `_on_write_report` 的 `template` 变量。
6. **运行测试前必须先连接仪表**；`--headless` 模式会主动连接并断开。
7. **所有仪器操作都依赖实际硬件**，没有 mock/仿真环境；本地运行测试会真实发 SCPI / 开电源 / 切开关。
8. **避免手动操作 git 提交/推送/重置**，除非用户明确指示。

## Agent 后续命令示例

- "将 RX NF 的限值 `nf_max_db` 从 1.3 改为 1.5 并保存到 user_settings.json"
- "在 tests/ 下新增一个 tx_current 测试并注册到 UI"
- "给 report.py 增加把截图插入 Word 报告的功能"
- "修复 --headless 模式下测试失败没有正常断开仪表的问题"
- "给 main_window.py 的结果表格增加导出 CSV 按钮"
