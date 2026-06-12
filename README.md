# C波段射频模块自动化测试系统 (Python版)

## 环境要求

- **Python 3.12+**
- **Windows** (截图功能依赖 N9020A 内部 Windows 路径; Word 报告依赖 python-docx)
- 硬件: Keysight N9020A, R&S SMU200A, TDK-Lambda 电源 ×2, UDC-0624F 开关矩阵

## 快速开始

```bash
cd cband_autotest

# 1. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 2. 启动 GUI
.venv\Scripts\python main.py

# 3. 或命令行运行（无 GUI）
.venv\Scripts\python main.py --headless all
.venv\Scripts\python main.py --headless rx_nf rx_pn
```

## 项目结构

```
cband_autotest/
├── main.py                      # 入口 (GUI / --headless)
├── requirements.txt
├── config/
│   ├── default_settings.json    # 全部可配置参数默认值
│   ├── user_settings.json       # 用户保存的配置 (运行时生成)
│   └── config_manager.py        # 配置管理器 (JSON ↔ 属性)
├── instruments/                 # 仪器驱动层
│   ├── power_supply.py          # TCP/IP SCPI 电源控制
│   ├── signal_generator.py      # VISA SMU200A 信号源
│   ├── spectrum_analyzer.py     # VISA N9020A 频谱仪
│   └── switch_matrix.py         # UART 开关矩阵
├── tests/                       # 测试执行层
│   ├── base.py                  # 测试基类
│   ├── rx_nf.py                 # RX 噪声系数 + 增益
│   ├── rx_pn.py                 # RX 相位噪声
│   ├── tx_gain.py               # TX 增益 + 输出功率
│   ├── tx_flatness_pn.py        # TX 平坦度 + 相位噪声
│   └── tx_rx_influence.py       # 收发干扰
├── ui/                          # PySide6 桌面界面
│   ├── main_window.py           # 主窗口
│   ├── settings_dialog.py       # 设置对话框 (8个Tab)
│   ├── test_runner.py           # QThread 测试执行器
│   └── results_panel.py         # 结果面板
├── utils/
│   ├── logger.py                # 日志
│   └── report.py                # TXT + DOCX 报告生成
└── output/
    ├── screenshots/             # 截图输出
    ├── reports/                 # 测试报告输出
    └── logs/                    # 日志文件
```

## 可配置参数 (通过 UI 设置 → 保存 → 持久化为 JSON)

| 分类 | 参数 |
|---|---|
| **仪器连接** | 4台IP地址、端口、VISA厂商、COM口号、波特率 |
| **产品信息** | 序列号、型号、名称、测试日期、环境、操作员 |
| **射频链路** | TX IF 线损 (3频点)、TX RF 线损 (3频点)、修正值 |
| **RX NF** | 模板名、NF最大/平均限值、增益/平坦度限值 |
| **RX PN** | 模板名、VSG频率/功率、4个偏置点限值 |
| **TX Gain** | 模板名、VSG功率、Pout/Gain最小限值 |
| **TX Flatness** | 模板名、VSG功率、平坦度限值、扫频参数、SA参数 |
| **TX PN** | 中心频率、4个偏置点限值 |
| **收发干扰** | VSG功率、噪底差异限值 |
| **报告/截图** | 启用开关、截图路径、报告格式 |

## 测试流程

```
连接仪表 → 选择测试 → QThread 执行 → 结果表格 + 日志 → 生成报告(.txt + .docx)
```

每个测试独立运行，可单独执行或全部运行。测试过程中 UI 不冻结。

## 与原 MATLAB 版本的对应关系

| MATLAB | Python |
|---|---|
| `CBandAutoTest.m` | `main.py` + `ui/main_window.py` |
| `SubProcess0_InitInstrument.m` | `ui/main_window.py._on_connect_all()` |
| `SubProcess1_TestRXNF.m` | `tests/rx_nf.py` |
| `SubProcess2_TestRXPN.m` | `tests/rx_pn.py` |
| `SubProcess3_TestTXFlatness_PN.m` | `tests/tx_flatness_pn.py` |
| `SubProcess4_TestTXGain_Pout.m` | `tests/tx_gain.py` |
| `SubProcess5_TestRXInfluence.m` | `tests/tx_rx_influence.py` |
| `Display_ALL_DATA.m` | `ui/main_window.py` 结果表格 |
| `SaveDate.m` | `utils/report.py.generate_txt()` |
| `ExportData2Docx.m` | `utils/report.py.generate_docx()` |
| `reset_data.m` | `config/default_settings.json` |
| 硬编码参数 | `config/default_settings.json` + UI 编辑 |
