# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- 新增 `AGENTS.md`，为后续 Agent 协作提供项目说明与编码约定。
- 右侧结果面板重构为 `ResultsPanel`：
  - 上方总览表显示所有已测项目的关键指标
  - 点击项目行可在下方查看完整格式化数据
  - 支持导出 JSON 与 CSV
- 仪器状态区域增加彩色指示灯（绿/红/灰）。
- 客户合规报告功能（`utils/report.py`）：
  - 对超标指标按配置的 `sanitize` 区间进行随机修正
  - 生成 `检验记录_{SN}_toC.docx` 用于客户交付
  - 在 `ui/settings_dialog.py` 新增「数据修正」Tab 管理 16 项指标区间
- `config/default_settings.json` 新增 `sanitize` 配置节。

### Changed

- 左侧面板改为可滚动，适配小屏幕。
- 主窗口左右区域使用 `QSplitter`，可手动拖动调整宽度。
- 右侧结果面板与日志区域也使用可调整布局，并设置最小高度。
- 测试运行时结果面板不再清空，上一轮结果保持可见并随新结果逐条更新。
- 设置对话框「数据修正」Tab 支持滚动，所有数值输入框禁用鼠标滚轮防止误触。

### Fixed

- 修复连接仪器后，长 IDN 文本把左侧面板撑宽、导致下方测试按钮被拉长遮挡的问题。
- 修复测试过程中结果面板暂时不可见的问题。

## [1.0.0] - 2026-06-22

### Added

- Python/PySide6 重构版 C 波段射频模块自动化测试系统。
- 支持 5 项测试：RX 噪声系数/增益/平坦度、RX 相位噪声、TX 增益/输出功率、TX 平坦度/相位噪声、TX-RX 收发干扰。
- 仪器驱动：TDK-Lambda 电源（TCP SCPI）、R&S SMU200A 信号源（VISA）、Keysight N9020A 频谱仪（VISA）、UDC-0624F 开关矩阵（UART）。
- PySide6 图形界面与 `--headless` 命令行模式。
- TXT + DOCX 测试报告生成。
