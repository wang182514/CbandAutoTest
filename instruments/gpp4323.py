"""
GWINSTEK GPP-4323 四通道可编程DC电源 — USB 虚拟串口 (VCP)

与原有 TCP 单通道电源 (PowerSupply) 的关键区别:
  - 物理连接: USB → 虚拟串口 COM? (非网线 TCP)
  - 一台设备 4 通道, 本项目 CH1=RX/12V, CH2=TX/24V
  - 所有通道共享一个串口, 指令后缀区分通道号, 无需切换通道
  - 线程安全: 所有 SCPI 操作通过 threading.Lock 原子化

用法:
    rx_pwr = Gpp4323("COM11", channel=1)   # CH1 = RX 12V
    tx_pwr = Gpp4323("COM11", channel=2)   # CH2 = TX 24V

SCPI 指令格式 (用户实测):
    :OUTP{ch} On/Off   — 开/关输出
    :MEAS{ch}:VOLT?    — 读电压
    :MEAS{ch}:CURR?    — 读电流
    VOLT{ch} <值>      — 设电压
    CURR{ch} <值>      — 设电流
    *IDN?              — 查询 IDN
    :SYST:ERR?         — 查询错误
"""

import threading
import time

import serial  # pyserial


class Gpp4323:
    """GPP-4323 四通道电源 — 每通道一个实例, 共享底层串口."""

    # ---- 类级共享 (所有通道实例共用) ----
    _shared_port: "serial.Serial | None" = None  # class-level, accessed via Gpp4323._shared_port
    _shared_port_name: str | None = None
    _lock = threading.RLock()
    _ref_count: int = 0

    def __init__(self, port: str, channel: int, baud_rate: int = 9600):
        self._port = port
        self._channel = channel          # 1=CH1(RX), 2=CH2(TX)
        self._baud_rate = baud_rate
        self._idn: str = ""
        self._last_error: str = ""

    # ---- 属性 ----
    @property
    def idn(self) -> str:
        return self._idn

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return Gpp4323._shared_port is not None and Gpp4323._shared_port.is_open

    # ========================================================================
    #  连接 / 断开
    # ========================================================================

    def connect(self) -> str:
        """打开共享串口, 查询 IDN. 返回 IDN 字符串.
        整个方法持有锁——防止开串口和查IDN之间被其他线程关闭."""
        with self._lock:
            # 如果已有串口打开但端口名不同, 先关闭
            if Gpp4323._shared_port is not None and self._shared_port_name != self._port:
                try:
                    Gpp4323._shared_port.close()
                except Exception:
                    pass
                Gpp4323._shared_port = None
                Gpp4323._ref_count = 0

            # 打开串口 (首次连接时)
            if Gpp4323._shared_port is None:
                try:
                    Gpp4323._shared_port = serial.Serial(
                        port=self._port,
                        baudrate=self._baud_rate,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1.0,
                    )
                except serial.SerialException:
                    # 端口已被其他进程占用, 尝试复用
                    pass
                if Gpp4323._shared_port is None or not Gpp4323._shared_port.is_open:
                    # 第二次尝试 — 也许是另一个通道实例已打开
                    pass
                self._shared_port_name = self._port
                Gpp4323._ref_count = 0

            Gpp4323._ref_count += 1

            # 查询 IDN——锁仍然持有，不会被其他线程打断
            self._send("*IDN?")
            time.sleep(0.05)
            try:
                self._idn = Gpp4323._shared_port.readline().decode("ascii").strip()
            except Exception:
                self._last_error = "IDN 读取超时"
                self._idn = ""

        return self._idn

    def disconnect(self):
        """断开此通道. 所有通道断开后才真正关闭串口."""
        with self._lock:
            Gpp4323._ref_count -= 1
            if Gpp4323._ref_count <= 0 and Gpp4323._shared_port is not None:
                try:
                    Gpp4323._shared_port.close()
                except Exception:
                    pass
                Gpp4323._shared_port = None
                self._shared_port_name = None
                Gpp4323._ref_count = 0
        self._idn = ""

    # ========================================================================
    #  电源控制
    # ========================================================================

    def set_output(self, on: bool):
        state = "On" if on else "Off"
        self._send(f":OUTP{self._channel} {state}")
        time.sleep(0.2)

    def get_output_state(self) -> bool:
        resp = self._query(f":OUTP{self._channel}?")
        return resp.strip().upper() in ("ON", "1")

    def measure_voltage(self) -> float:
        resp = self._query(f":MEAS{self._channel}:VOLT?")
        try:
            return float(resp)
        except ValueError:
            return float("nan")

    def measure_current(self) -> float:
        resp = self._query(f":MEAS{self._channel}:CURR?")
        try:
            return float(resp)
        except ValueError:
            return float("nan")

    def set_voltage(self, volts: float):
        self._send(f"VOLT{self._channel} {volts:.2f}")

    def set_current(self, amps: float):
        self._send(f"CURR{self._channel} {amps:.2f}")

    # ========================================================================
    #  底层串口通信
    # ========================================================================

    def _send(self, cmd: str):
        """发送指令 (不读回复), 自动加锁."""
        with self._lock:
            if Gpp4323._shared_port is None or not Gpp4323._shared_port.is_open:
                raise RuntimeError("GPP-4323 串口未打开")
            if not cmd.endswith("\n"):
                cmd += "\n"
            Gpp4323._shared_port.write(cmd.encode("ascii"))
            time.sleep(0.02)

    def _query(self, cmd: str) -> str:
        """发送查询指令并读取回复, 自动加锁."""
        with self._lock:
            self._send(cmd)
            time.sleep(0.05)
            try:
                return Gpp4323._shared_port.readline().decode("ascii").strip()
            except Exception:
                self._last_error = "读取超时"
                return ""
