# Keysight N9020A MXA — 项目 SCPI 速查手册

> 所有命令按功能分类，格式为 `:SUBSYS:CMD <参数>`（写）或 `:SUBSYS:CMD?`（查询）。
> 带 `[W]` 为只写命令，带 `[Q]` 为只读查询，`[W/Q]` 为可写可查。

---

## 一、系统控制

| 命令           | 方向  | 说明                           |
| ------------ |:---:| ---------------------------- |
| `*CLS`       | W   | 清空状态寄存器和错误队列                 |
| `*IDN?`      | Q   | 查询仪器标识字符串                    |
| `*OPC?`      | Q   | 等待当前操作完成后返回 `+1`（阻塞同步）       |
| `:SYST:ERR?` | Q   | 查询错误队列（正常返回 `+0,"No error"`） |

---

## 二、模式切换

| 命令                  | 方向  | 说明                  |
| ------------------- |:---:| ------------------- |
| `:INST SA`          | W   | 切换到标准频谱分析模式         |
| `:INST:SEL NFIGURE` | W   | 切换到噪声系数模式（需 NFE 选件） |
| `:INST PNOISE`      | W   | 切换到相位噪声模式           |

---

## 三、模板加载

| 命令                        | 方向  | 说明                                             |
| ------------------------- |:---:| ---------------------------------------------- |
| `:MMEM:LOAD:STAT "<文件名>"` | W   | 加载仪器本地存储的状态模板。必须先 `*CLS` 清错误队列，后接 `*OPC?` 等待完成 |

**项目常用模板**：

| 文件名                 | 用途           |
| ------------------- | ------------ |
| `state_RX_NF.state` | 接收噪声系数 + 增益  |
| `state_PN.state`    | 相位噪声         |
| `State_ACPR.state`  | ACPR / 主信道功率 |
| `State_Psat.state`  | 饱和功率         |

---

## 四、SA 模式（频谱分析）

### 4.1 扫频配置

| 命令                                  | 说明                        |
| ----------------------------------- | ------------------------- |
| `:SENS:FREQ:STAR <value>GHz`        | 起始频率                      |
| `:SENS:FREQ:STOP <value>GHz`        | 终止频率                      |
| `:FREQuency:CENTer <value>GHz`      | 中心频率（等效于设 STAR/STOP，写法更短） |
| `:SENS:FREQ:STAR <value>MHz`        | 起始频率（窄扫宽用 MHz）            |
| `:SENS:FREQ:STOP <value>MHz`        | 终止频率（窄扫宽用 MHz）            |
| `:SENS:BAND:RES <value>KHz`         | 分辨率带宽（RBW）                |
| `:SENS:BAND:VID <value>KHz`         | 视频带宽（VBW）                 |
| `:DISP:WIND:TRAC:Y:RLEV <value>dBm` | 参考电平                      |
| `:SENS:SWE:TIME:AUTO ON`            | 自动扫描时间                    |
| `:DET:TRAC1:<type> ON`              | 检波器类型（POS/AVER/AUTO…）     |
| `:TRAC1:TYPE WRIT`                  | 迹线类型设为 Clear/Write        |
| `:INIT:CONT ON`                     | 连续触发                      |

### 4.2 显示与补偿

| 命令                                             | 说明                 |
| ---------------------------------------------- | ------------------ |
| `:DISPlay:WIND1:TRACe:Y:RLEVel:OFFSet <value>` | 参考电平偏移（线损补偿，单位 dB） |

### 4.3 Marker 操作

| 命令                            | 方向  | 说明                    |
| ----------------------------- |:---:| --------------------- |
| `:CALC:MARK1:STAT ON`         | W   | 打开 Marker1            |
| `:CALCulate:MARKer1:MAXimum`  | W   | 峰值搜索（找最高点）            |
| `:CALC:MARK1:X?`              | Q   | 读 Marker1 X 轴（频率，Hz）  |
| `:CALC:MARK1:Y?`              | Q   | 读 Marker1 Y 轴（幅度，dBm） |
| `:CALC:MARK1:PTP`             | W   | 峰-峰值搜索                |
| `:CALCulate:MARKer:AOFF`      | W   | 关闭所有 Marker           |
| `:CALCulate:MARKer1:STATe ON` | W   | 设 Marker1 到指定频率       |

### 4.4 噪声 Marker

| 命令                                 | 说明                           |
| ---------------------------------- | ---------------------------- |
| `:CALCulate:MARKer1:X <freq>MHz`   | Marker1 放到指定频率               |
| `:CALCulate:MARKer1:FUNCtion NOIS` | 启用噪声测量功能                     |
| `:CALCulate:MARKer1:Y?`            | 读噪声功率（dBm/Hz）。**等待 3s 以上再读** |

### 4.5 检波器

| 命令                  | 说明                       |
| ------------------- | ------------------------ |
| `:DET:TRAC1:POS ON` | POS（峰值）检波器，噪声 Marker 建议用 |

### 4.6 ACPR 测量（邻信道功率比）

| 命令                                   | 方向  | 说明                                                                                       |
| ------------------------------------ |:---:| ---------------------------------------------------------------------------------------- |
| `:MMEM:LOAD:STAT "State_ACPR.state"` | W   | 加载 ACPR 测量模板（预配信道间隔、带宽、偏移）                                                               |
| `:READ:ACP?`                         | Q   | 触发一次 ACPR 测量并返回结果。**返回格式**：`acp_m,acp_l,acp_u` — 分别为主信道功率(dBm)、低侧 ACPR(dBc)、高侧 ACPR(dBc) |
| `:INIT:IMM`                          | W   | 触发单次测量（用于连续测量模式下手动触发）                                                                    |
| `ACP:CARR1:LIST:WIDT <value>Mhz`     | W   | 修改CarrierSpacing,可查询                                                                     |
| `ACP:CARR1:LIST:BAND <value>Mhz`     | W   | 修改Measurement Noise Bandwidth,可查询                                                        |
| `ACP:OFFS:LIST <value>Mhz`           | W   | 修改OffsetFreq,返回值为一组以逗号分割的数组,取第一个值,可查询                                                    |
| `ACP:OFFS:LIST:BAND <value>Mhz`      | W   | 修改IntegeBW,可查询                                                                           |
| 备注:标注可查询的,把\<value\>改为?加在语句后可以查询对应值  |     |                                                                                          |

> **典型流程**（参考 `UPautoTestV0_4.m`）：
> 
> ```
> :INST SA  →  :MMEM:LOAD:STAT "State_ACPR.state"
> :FREQuency:CENTer 14.125GHz
> :DISP:WIND1:TRACe:Y:RLEVel:OFFSet 35.1   (线损补偿)
> :INIT:CONT ON  →  :INIT:IMM  →  pause(2s)
> :READ:ACP?   →  返回 "12.3,-28.5,-29.1"
> ```
> 
> **ACPR 取值**：`max(acp_l, acp_u)` 为最终 ACPR 值（取较差侧）。
> 
> **饱和功率测量模板**：`State_Psat.state`，配合 `:CALC:MARK1:MAX` + `:CALC:MARK1:Y?` 读峰值。

---

## 五、NF 模式（噪声系数）

### 5.1 测量控制

| 命令                         | 方向  | 说明              |
| -------------------------- |:---:| --------------- |
| `:INIT:CONT ON`            | W   | 设为连续触发          |
| `:INIT:IMM`                | W   | 单次触发测量          |
| 后接 `*OPC?`                 | Q   | 等待测量完成          |
| `:CALC:NFIG:MARK:COUP OFF` | W   | 关闭 NF marker 耦合 |
| `:CALC:NFIG:MARK:AOFF`     | W   | 关闭所有 NF marker  |
| `:NFIG:CAL:INIT`           | W   | 初始化 NF 校准       |
| `:NFIG:CAL:STAT?`          | Q   | 查询校准状态（1=已校准）   |

### 5.2 Marker 读值

| 命令                                | 说明                                 |
| --------------------------------- | ---------------------------------- |
| `:CALC:NFIG:MARK<n>:STAT ON`      | 打开 NF marker n（1~4）                |
| `:CALC:NFIG:MARK<n>:TRAC TRAC<t>` | 绑定到迹线 t（1=NF, 2=Gain, 3=Y-Factor…） |
| `:CALC:NFIG:MARK<n>:X <freq>GHz`  | 设 marker 频率                        |
| `:CALC:NFIG:MARK<n>:Y?`           | 读 marker 纵轴值（NF=dB, Gain=dB）       |

> 项目惯例：MARK1 trace1=NF, MARK2 trace1=NF(备), MARK3 trace2=Gain

---

## 六、PN 模式（相位噪声）

| 命令                            | 方向  | 说明                   |
| ----------------------------- |:---:| -------------------- |
| `:FREQ:CENT <value>GHz`       | W   | 设中心频率                |
| `:INIT:CONT OFF`              | W   | 关闭连续触发               |
| `:INIT:IMM`                   | W   | 单次触发                 |
| 后接 `*OPC?`                    | Q   | 等待完成（**超时需设 ≥120s**） |
| `:CALCulate:LPLot:MARK<n>:X?` | Q   | 读偏移频率（Hz）            |
| `:CALCulate:LPLot:MARK<n>:Y?` | Q   | 读相位噪声（dBc/Hz）        |

---

## 七、截图

| 命令                         | 说明                               |
| -------------------------- | -------------------------------- |
| `:DISP:FSCR ON`            | 开启截图功能                           |
| `:DISP:FSCR OFF`           | 关闭                               |
| `:MMEM:STOR:SCR:THEM FCOL` | 设配色主题                            |
| `:MMEM:STOR:SCR "<内部路径>"`  | 截图存到仪器本地（如 `D:\...\tmp.png`）     |
| `:MMEM:DATA? "<路径>"`       | 通过 VISA 把截图的二进制 PNG 数据读到 PC      |
| 后接 `read_raw()`            | PyVISA 读取二进制数据块（`#nLEN\n...` 格式） |

---

## 八、常用指令速记

```
SA 扫频全流程:
  :INST SA
  :SENS:FREQ:STAR 0.95GHz  →  :SENS:FREQ:STOP 1.55GHz
  :SENS:BAND:RES 30KHz  →  :SENS:BAND:VID 30KHz
  :DISP:WIND:TRAC:Y:RLEV -10dBm
  :INIT:CONT ON

Marker 峰值 + 读取:
  :CALC:MARK1:STAT ON  →  :CALCulate:MARKer1:MAXimum
  CALC:MARK1:X?   →  频率 (Hz)
  CALC:MARK1:Y?   →  幅度 (dBm)

NF 测一个频点:
  :INST:SEL NFIGURE
  :MMEM:LOAD:STAT "state_RX_NF.state"  →  *OPC?
  :INIT:CONT ON  →  :INIT:IMM  →  *OPC?
  :CALC:NFIG:MARK:COUP OFF  →  :CALC:NFIG:MARK:AOFF
  :CALC:NFIG:MARK1:STAT ON  →  :CALC:NFIG:MARK1:TRAC TRAC1  →  :CALC:NFIG:MARK1:X 1.20GHz
  :CALC:NFIG:MARK1:Y?   →  NF 值
  :CALC:NFIG:MARK3:TRAC TRAC2  →  :CALC:NFIG:MARK3:X 1.20GHz
  :CALC:NFIG:MARK3:Y?   →  Gain 值

PN 测一个点:
  :INST PNOISE
  :MMEM:LOAD:STAT "state_PN.state"  →  *OPC?
  :FREQ:CENT 1.20GHz
  :INIT:CONT OFF  →  :INIT:IMM  →  *OPC? (timeout=120s)
  :CALC:LPL:MARK1:X?  →  偏移 (Hz)
  :CALC:LPL:MARK1:Y?  →  PN (dBc/Hz)

ACPR 测量（N9020A + SMU200A）:
  :INST SA
  :MMEM:LOAD:STAT "State_ACPR.state"  →  *OPC?
  :FREQ:CENT 14.125GHz
  :DISP:WIND1:TRAC:Y:RLEV:OFFS 35.1
  :INIT:CONT ON  →  :INIT:IMM
  pause(2s)  →  :READ:ACP?
  → 返回 acp_m(dBm), acp_l(dBc), acp_u(dBc)

清理:
  :CALC:MARK:AOFF   →  :CALC:MARK1:FUNC OFF
  :SYST:ERR?   →  确认 +0
```
