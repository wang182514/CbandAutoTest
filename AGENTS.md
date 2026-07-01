# C波段射频模块自动化测试系统 — Agent 指南

> 最后更新：2026-07-01

## 项目定位

本项目是原 MATLAB 版 `CBandAutoTest` 的 Python/PySide6 重构版，用于在产线对 C 波段射频模块执行自动化射频性能测试。

**当前测试项（7 个）**：

| 测试 ID | 显示名称 | 类型 |
|---------|---------|------|
| `rx_nf` | RX 噪声系数 + 增益 | 接收 |
| `rx_nf_v2` | RX NF/增益 (带外抑制) | 接收 (扩展模板) |
| `rx_oob_sa` | RX 带外抑制(SA) | 接收 (SA 模式, 待验证) |
| `rx_pn` | RX 相位噪声 | 接收 |
| `tx_gain` | TX 增益 + 输出功率 | 发射 |
| `tx_flatness_pn` | TX 平坦度 + 相位噪声 | 发射 |
| `tx_rx_influence` | 收发干扰 | 通用 |

运行环境：**Python 3.12+ / Windows**，依赖真实硬件仪表（Keysight N9020A、R&S SMU200A、TDK-Lambda 电源 ×2、UDC-0624F 开关矩阵）。

## 启动方式

```bash
# GUI 模式
.venv\Scripts\python main.py

# 命令行模式（调试/自动化）
.venv\Scripts\python main.py --headless all
.venv\Scripts\python main.py --headless rx_pn tx_gain
```

## 目录结构

```
cband_autotest/
├── main.py                      # 入口 (GUI / --headless)
├── config/
│   ├── default_settings.json    # 默认配置（受版本控制）
│   ├── user_settings.json       # 用户配置（.gitignore 忽略）
│   └── config_manager.py        # 配置加载/保存/点号访问 (_ConfigNode)
├── instruments/                 # 仪器驱动层
│   ├── power_supply.py          # TDK-Lambda TCP SCPI (:2268)
│   ├── signal_generator.py      # R&S SMU200A via PyVISA
│   ├── spectrum_analyzer.py     # Keysight N9020A (SA/NF/PN三模式+截图)
│   └── switch_matrix.py         # UDC-0624F UART 串口
├── tests/                       # 测试执行层 (插件化注册)
│   ├── plugin.py                # @register_test 装饰器 + discover()
│   ├── base.py                  # TestBase(仪器/日志/截图/停止/进度) + TestResult
│   ├── rx_nf.py                 # RX 噪声系数+增益 (include_in_run_all=False)
│   ├── rx_nf_v2.py              # RX NF+增益+带外抑制(NF模式, 扩展模板)
│   ├── rx_oob_sa.py             # RX 带外抑制(SA模式, 调试用)
│   ├── rx_pn.py                 # RX 相位噪声
│   ├── tx_gain.py               # TX 增益+输出功率 (逐频点限值)
│   ├── tx_flatness_pn.py        # TX 平坦度+相位噪声
│   └── tx_rx_influence.py       # 收发干扰
├── ui/                          # PySide6 界面
│   ├── main_window.py           # 主窗口 (连接/测试/报告/布局记忆/皮肤)
│   ├── settings_dialog.py       # 10 Tab 设置 (含 "数据修正" Tab)
│   ├── test_runner.py           # QThread 执行器 (加权进度/自适应权重/安全停止)
│   └── results_panel.py         # 结果面板 (仪表板芯片+H5详情+JSON/CSV导出)
├── utils/
│   ├── logger.py                # 日志 (控制台+文件)
│   └── report.py                # 报告生成 (TXT+坐标DOCX+书签DOCX+客户合规)
└── output/                      # 运行时产出 (.gitignore)
    ├── logs/
    ├── reports/
    └── screenshots/{SN}/
```

## 核心架构约定

### 插件化测试注册 (tests/plugin.py)

新增测试不再需要改 `test_runner.py` 或 `main_window.py`。只需在 `tests/` 下新建文件，给函数加装饰器：

```python
from .plugin import register_test

@register_test(
    id="my_test",
    name="我的测试",
    category="rx",       # rx / tx / general
    order=10,            # 排序 (越小越靠前)
    weight=15,           # 进度条权重 (耗时越长越大)
    include_in_run_all=True,  # 是否参与"运行全部"
)
def run_my_test(base: TestBase) -> TestResult:
    ...
```

### 配置系统

- `ConfigManager` 加载 `default_settings.json`，再 deep-merge `user_settings.json`。
- 点号访问：`cfg.instruments.rx_power_supply.ip`
- `user_settings.json` 只存储与默认值不同的字段。

### TestBase 公共服务

- 仪器引用：`base.rx_pwr / tx_pwr / vsg / sa / switch`
- 配置：`base.cfg`
- 日志：`base.log.info/warning/error`
- 截图：`base.screenshot(filename)` → 存到 `output/screenshots/{SN}/`
- 开关：`base.set_switches([SW1,SW2,SW3,SW4])`
- **安全停止**：`base.stop_requested` (bool 属性) + `base.safe_shutdown()`
- **子进度**：`base.report_progress(cur, total)` 让进度条在测试内部平滑推进

### 报告生成

点击「写入报告」后生成三份文件：

| 文件 | 路径 | 数据 |
|------|------|------|
| TXT | `output/reports/data/测试记录_{SN}.txt` | 真实 |
| 内部 DOCX | `output/reports/data/检验记录_{SN}.docx` | 真实 |
| 客户 DOCX | `output/reports/检验记录_{SN}_toB.docx` | 合规 (超标值修正) |

DOCX V2 模板 (`CbandTemplateV2.docx`) 使用书签定位，不再依赖硬编码行列坐标。文件名含 `V2` 自动走书签写入，不含则走旧坐标逻辑。

### 设置对话框

10 个 Tab：仪器连接 / 产品信息 / 射频链路 / RX NF增益 / RX 相位噪声 / TX 增益功率 / TX 平坦度PN / 收发干扰 / 报告截图 / **数据修正**

- "数据修正" Tab 配置客户报告合规修正的随机范围。
- 所有数字输入框禁用鼠标滚轮（防误触）。
- 内容超出可见范围时自动滚动。

### UI 关键特性

- **结果面板**：仪表板芯片行 (名称+✓/✗+简略值)，点击展开 HTML 详情
- **横幅**：始终可见，显示 `共N项 · ✓X合格 · ✗Y不合格 · ⊘Z终止`
- **进度条**：加权 + 测试内部子进度 + 自适应学习耗时
- **安全停止**：点击停止立即关 RF/电源，长循环内每秒检查停止标志
- **布局记忆**：窗口位置/大小/分隔条位置持久化 (QSettings)
- **SN 递增**：写入报告后弹窗确认自动 +1
- **清空结果**：重置芯片、按钮颜色、累积数据

### 适配客户报告的合规修正 (sanitize)

`sanitize_results()` 函数对不合格指标生成随机合规值。TX Gain 值由 Pout 值直接推导 (`Gain = Pout − VSG`)，而非独立随机。平坦度指标 > 2.0 即触发修正（客户标准严于产线标准）。

## 常见开发注意事项

1. **配置修改**：改 `user_settings.json`，不要改 `default_settings.json`。
2. **新增测试**：建文件 + 加 `@register_test` 装饰器即可，无需手动注册。
3. **仪器模板**：`state_RX_NF.state` 和 `state_RX_NF2.state` 是 N9020A 内部状态文件，需手动校准维护。
4. **DOCX 模板**：`CbandTemplate.docx` (旧,坐标) 和 `CbandTemplateV2.docx` (新,书签) 位于项目上级目录。
5. **截图路径**：`instrument_internal_path` 是 N9020A 仪器内部路径，不可随意改。
6. **无 mock 环境**：所有操作依赖真实硬件，本地运行会真实发 SCPI 指令。
7. **Git 操作**：避免手动 commit/push/revert，除非用户明确指示。
8. **QSS 皮肤**：全局样式在 `MainWindow._global_qss()`，按钮/芯片/横幅颜色分散在各处。
