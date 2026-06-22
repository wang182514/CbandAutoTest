# 今日改动总结

> 日期：2026-06-22  
> 分支：main（所有 stable 分支改动已 fast-forward 合并到 main）

---

## 一、文档新增

### 1. `AGENTS.md`

- 项目整体说明、目录结构、核心约定
- 仪器驱动与测试模块的调用方式
- 常见开发注意事项与后续命令示例

### 2. `improvements.md`

- 汇总 UI 排布 10 项可改进点
- 汇总测试流程 4 大类缺陷
- 列出 6 条建议优先修复项

---

## 二、UI 改进

### 1. 左侧面板优化

- **可滚动**：将左侧控件（仪器状态、快速设置、测试控制）放入 `QScrollArea`，小屏幕也能访问到底部按钮。
- **状态指示灯**：每个仪器左侧增加圆形彩色指示灯：
  - 绿色：连接成功
  - 红色：连接失败
  - 灰色：未连接
- **宽度约束**：
  - 左侧面板最小宽度 260px，最大宽度 360px
  - 仪器 IDN 文本启用自动换行，避免撑宽面板
  - 测试按钮设置最大宽度 320px，防止被长文本拉长

### 2. 右侧结果面板重构

- 新增 `ui/results_panel.py`：`ResultsPanel` 控件
- 改为上下双区域：
  - **上方总览表**：测试项目、结果、关键指标
  - **下方详情浏览器**：点击总览表行，显示该测试的完整格式化数据
- 支持导出：
  - 导出 JSON：保留原始数据结构
  - 导出 CSV：展平为 Excel 友好格式
- 保留 PASS/FAIL 颜色标识

### 3. 主窗口布局优化

- 左右区域改为 `QSplitter`，可手动拖动分界线
- 右侧结果面板与日志区域也设置最小高度，避免被过度压缩
- 测试运行时不再清空结果面板，上一轮结果保持可见并随新结果逐条更新

---

## 三、测试流程分析

在 `improvements.md` 中记录了以下待修复缺陷，**今日尚未修改代码**：

- 测试开始前缺少统一仪器复位
- 部分测试异常时未关闭电源 / VSG 射频
- 硬编码等待时间（收发干扰 10s、噪声 marker 3s）
- 线损 offset 未复位
- 序列号未校验
- 命令行模式不生成报告
- DOCX 模板路径指向项目根目录上级

---

## 四、今日提交记录

```
d803d64 ui: constrain left panel max width and wrap IDN labels to prevent test buttons from stretching
0364fd5 ui: use QSplitter for resizable panels, keep results visible during tests, set min widths
670cf51 ui: redesign results panel with summary table, detailed HTML view, and JSON/CSV export
980da13 ui: wrap left panel in scroll area and add colored instrument status indicators
42e1c08 docs: add improvements.md
fae9851 docs: add AGENTS.md for agent guidance
```

---

## 五、未推送说明

GitHub 推送因当前环境无法连接 `github.com:443` 而失败。所有改动已提交到本地 `main` 和 `stable` 分支，需在网络正常时手动执行：

```bash
git push origin main
git push origin stable
```

---

## 六、下一步建议

1. 验证 UI 在连接真实仪表后按钮不再被拉长、结果面板始终可见。
2. 根据 `improvements.md` 修复测试流程缺陷。
3. 完成 GitHub 推送同步。
