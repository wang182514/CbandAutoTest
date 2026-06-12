"""
TDK-Lambda / generic power supply via TCP/IP SCPI (:2268).
Replaces MATLAB's tcpip() + fprintf/fgetl pattern.
"""

import socket
import time
from typing import Optional


class PowerSupply:
    """TCP/IP SCPI power supply controller."""

    def __init__(self, ip: str, port: int = 2268, timeout_sec: float = 1.0):
        self._ip = ip
        self._port = port
        self._timeout = timeout_sec
        self._sock: Optional[socket.socket] = None
        self._idn: str = ""

    # ---- connection --------------------------------------------------------

    def connect(self) -> str:
        """Open TCP socket and query *IDN?. Returns IDN string."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self._timeout)
        self._sock.connect((self._ip, self._port))
        self._idn = self._query("*IDN?")
        return self._idn

    def disconnect(self):
        """Close socket."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    @property
    def is_connected(self) -> bool:
        return self._sock is not None

    # ---- SCPI helpers ------------------------------------------------------

    def _send(self, cmd: str):
        """Send a command; append LF if missing."""
        if not cmd.endswith("\n"):
            cmd += "\n"
        self._sock.sendall(cmd.encode("ascii"))

    def _recv(self) -> str:
        """Receive until LF, strip trailing whitespace."""
        data = b""
        while True:
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in chunk:
                    break
            except socket.timeout:
                break
        return data.decode("ascii").strip()

    def _query(self, cmd: str) -> str:
        """Send + receive."""
        self._send(cmd)
        time.sleep(0.02)
        return self._recv()

    # ---- public API --------------------------------------------------------

    def set_output(self, on: bool):
        """Turn output ON (True) or OFF (False)."""
        val = "1" if on else "0"
        self._send(f":OUTP {val}")
        time.sleep(0.2)

    def get_output_state(self) -> bool:
        """Query output state."""
        resp = self._query(":OUTP?")
        return resp.strip() == "1"

    def measure_voltage(self) -> float:
        """Read actual output voltage (V)."""
        resp = self._query(":MEAS:VOLT?")
        return float(resp)

    def measure_current(self) -> float:
        """Read actual output current (A)."""
        resp = self._query(":MEAS:CURR?")
        return float(resp)

    def set_voltage(self, volts: float):
        self._send(f":SOUR:VOLT {volts}")

    def set_current(self, amps: float):
        self._send(f":SOUR:CURR {amps}")

    @property
    def idn(self) -> str:
        return self._idn
