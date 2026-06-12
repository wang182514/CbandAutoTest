"""
R&S SMU200A Vector Signal Generator via VISA (PyVISA).
Replaces MATLAB's visa('rs', ...) + fprintf/query pattern.
"""

import time
from typing import Optional
import pyvisa


class SignalGenerator:
    """R&S SMU200A (or compatible) VISA signal generator."""

    def __init__(self, ip: str, vendor: str = "rs", timeout_ms: int = 5000):
        self._ip = ip
        self._vendor = vendor
        self._timeout = timeout_ms
        self._resource_string = f"TCPIP0::{ip}::inst0::INSTR"
        self._inst: Optional[pyvisa.resources.MessageBasedResource] = None
        self._rm: Optional[pyvisa.ResourceManager] = None

    # ---- connection --------------------------------------------------------

    def connect(self) -> str:
        self._rm = pyvisa.ResourceManager()
        self._inst = self._rm.open_resource(self._resource_string)
        self._inst.timeout = self._timeout
        self._inst.read_termination = "\n"
        self._inst.write_termination = "\n"
        self._inst.write("*CLS")
        idn = self._inst.query("*IDN?").strip()
        return idn

    def disconnect(self):
        if self._inst:
            try:
                self._inst.close()
            except Exception:
                pass
            self._inst = None
        if self._rm:
            try:
                self._rm.close()
            except Exception:
                pass
            self._rm = None

    @property
    def is_connected(self) -> bool:
        return self._inst is not None

    # ---- CW mode -----------------------------------------------------------

    def set_cw(self, freq_mhz: float, power_dbm: float):
        """Set CW frequency (MHz) and power (dBm)."""
        self._inst.write(f"FREQ {freq_mhz:.3f}MHz")
        self._inst.write(f"POW {power_dbm:.2f}dBm")
        self._inst.write(":FREQ:MODE CW")

    # ---- sweep mode --------------------------------------------------------

    def configure_sweep(
        self,
        start_ghz: float,
        stop_ghz: float,
        step_khz: float,
        dwell_ms: float,
        power_dbm: float,
    ):
        """Configure linear frequency sweep."""
        self._inst.write(f"POW {power_dbm:.2f}dBm")
        self._inst.write(f"FREQ:STAR {start_ghz:.3f}GHz")
        self._inst.write(f"FREQ:STOP {stop_ghz:.3f}GHz")
        self._inst.write(f"SWE:STEP {step_khz:.0f}KHz")
        self._inst.write(f"SWE:DWEL {dwell_ms:.0f}ms")
        self._inst.write("SWE:SPAC LIN")
        self._inst.write("SWE:MODE AUTO")
        self._inst.write("FREQ:MODE SWE")

    def set_cw_mode(self):
        """Return to CW mode."""
        self._inst.write(":FREQ:MODE CW")

    # ---- RF output ---------------------------------------------------------

    def rf_on(self):
        self._inst.write("OUTP ON")

    def rf_off(self):
        self._inst.write("OUTP OFF")

    # ---- modulation --------------------------------------------------------

    def mod_off(self):
        """Turn off all modulation (equivalent to Mod On/Off key off)."""
        self._inst.write(":MOD:STAT OFF")
        self._inst.write(":SOUR:BB:DM:STAT OFF")

    # ---- raw access --------------------------------------------------------

    @property
    def inst(self):
        """Direct PyVISA resource for advanced commands."""
        return self._inst
