"""
Keysight N9020A MXA Spectrum Analyzer via VISA (PyVISA).
Covers SA, Noise Figure (NF), and Phase Noise (PN) modes.
Replaces MATLAB's visa('agilent', ...) / visa('rs', ...) pattern.
"""

import os
import time
from typing import Optional, List
import pyvisa


class SpectrumAnalyzer:
    """Keysight N9020A MXA Signal Analyzer controller."""

    def __init__(self, ip: str, vendor: str = "agilent", timeout_ms: int = 10000):
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

    @property
    def inst(self):
        return self._inst

    # ---- mode switching ----------------------------------------------------

    def set_mode_sa(self):
        """Switch to Standard Spectrum Analyzer mode."""
        self._inst.write(":INST SA")

    def set_mode_nf(self):
        """Switch to Noise Figure mode (requires NFE option)."""
        self._inst.write(":INST:SEL NFIGURE")

    def set_mode_pn(self):
        """Switch to Phase Noise mode."""
        self._inst.write(":INST PNOISE")

    # ---- template loading --------------------------------------------------

    def load_state(self, template_name: str):
        """Load an instrument state file (from the analyzer's local storage)."""
        self._inst.write(f':MMEM:LOAD:STAT "{template_name}"')
        time.sleep(1)

    def check_error(self) -> str:
        """Query :SYST:ERR? and return result."""
        return self._inst.query(":SYST:ERR?").strip()

    def clear_markers(self):
        """Turn off all markers and marker functions.
        N9020A has a known bug where residual marker settings
        can affect subsequent measurements — always call this
        at the end of each test."""
        self._inst.write(":CALCulate:MARKer:AOFF")
        self._inst.write(":CALCulate:MARKer1:FUNCtion OFF")

    # ---- SA mode -----------------------------------------------------------

    def sa_configure(
        self,
        start_ghz: float,
        stop_ghz: float,
        rbw_khz: float,
        vbw_khz: float,
        ref_level_dbm: float,
        trace_type: str = "WRIT",
        detector: str = "AUTO",
    ):
        """Configure spectrum analyzer for basic sweep."""
        self._inst.write(f":SENS:FREQ:STAR {start_ghz:.3f}GHz")
        self._inst.write(f":SENS:FREQ:STOP {stop_ghz:.3f}GHz")
        self._inst.write(f":SENS:BAND:RES {rbw_khz:.0f}KHz")
        self._inst.write(f":SENS:BAND:VID {vbw_khz:.0f}KHz")
        self._inst.write(f":DISP:WIND:TRAC:Y:RLEV {ref_level_dbm:.0f}dBm")
        self._inst.write(":SENS:SWE:TIME:AUTO ON")
        self._inst.write(f":DET:TRAC1:{detector} ON")
        self._inst.write(f":TRAC1:TYPE {trace_type}")
        self._inst.write(":INIT:CONT ON")

    def sa_configure_mhz(
        self,
        start_mhz: float,
        stop_mhz: float,
        rbw_khz: float,
        vbw_khz: float,
        ref_level_dbm: float,
        trace_type: str = "WRIT",
    ):
        """Configure SA with MHz units (for narrow spans)."""
        self._inst.write(f":SENS:FREQ:STAR {start_mhz:.3f}MHz")
        self._inst.write(f":SENS:FREQ:STOP {stop_mhz:.3f}MHz")
        self._inst.write(f":SENS:BAND:RES {rbw_khz:.0f}KHz")
        self._inst.write(f":SENS:BAND:VID {vbw_khz:.0f}KHz")
        self._inst.write(f":DISP:WIND:TRAC:Y:RLEV {ref_level_dbm:.0f}dBm")
        self._inst.write(":SENS:SWE:TIME:AUTO ON")
        self._inst.write(f":TRAC1:TYPE {trace_type}")
        self._inst.write(":INIT:CONT ON")

    def sa_set_offset(self, offset_db: float):
        """Set display reference level offset (for line loss compensation)."""
        self._inst.write(f":DISPlay:WIND1:TRACe:Y:RLEVel:OFFSet {offset_db:.1f}")

    def sa_marker_peak(self) -> tuple[float, float]:
        """Execute peak search; return (freq_GHz, amp_dBm)."""
        self._inst.write(":CALC:MARK1:STAT ON")
        self._inst.write(":CALCulate:MARKer1:MAXimum")
        time.sleep(0.1)
        freq = float(self._inst.query("CALC:MARK1:X?"))
        amp = float(self._inst.query("CALC:MARK1:Y?"))
        return freq, amp

    def sa_marker_ptp(self) -> float:
        """Peak-to-peak marker; returns delta (dB)."""
        self._inst.write(":CALC:MARK1:PTP")
        return float(self._inst.query(":CALC:MARK1:Y?"))

    def sa_marker_noise(self, freq_mhz: float, wait_sec: float = 3.0) -> float:
        """Set marker to freq, enable noise function, read noise level (dBm/Hz).
        wait_sec: delay before reading (MATLAB original uses 3s; N9020A needs
        time to compute noise marker after enabling the function)."""
        self._inst.write(":CALCulate:MARKer:AOFF")
        self._inst.write(":CALCulate:MARKer1:STATe ON")
        self._inst.write(f":CALCulate:MARKer1:X {freq_mhz:.0f}MHz")
        self._inst.write(":CALCulate:MARKer1:FUNCtion NOIS")
        time.sleep(wait_sec)
        # Timeout-guarded read — N9020A may be slow with narrow RBW
        old_timeout = self._inst.timeout
        try:
            self._inst.timeout = max(old_timeout, 15000)  # ≥15s for query
            return float(self._inst.query(":CALCulate:MARKer1:Y?"))
        finally:
            self._inst.timeout = old_timeout

    # ---- NF mode -----------------------------------------------------------

    def nf_init_cal(self):
        """Initialize noise figure calibration."""
        self._inst.write(":NFIG:CAL:INIT")
        self._inst.query("*OPC?")

    def nf_is_calibrated(self) -> bool:
        resp = self._inst.query(":NFIG:CAL:STAT?")
        return resp.strip() == "1"

    def nf_init_measurement(self):
        """Single-shot NF measurement."""
        self._inst.write(":INIT:CONT ON")
        self._inst.write(":INIT:IMM")
        self._inst.query("*OPC?")

    def nf_prepare_markers(self):
        """Disable marker coupling and all markers."""
        self._inst.write(":CALC:NFIG:MARK:COUP OFF")
        self._inst.write(":CALC:NFIG:MARK:AOFF")

    def nf_set_marker(self, marker: int, trace: int, freq_ghz: float):
        """Set NF marker to a specific frequency on a trace."""
        self._inst.write(f":CALC:NFIG:MARK{marker}:STAT ON")
        self._inst.write(f":CALC:NFIG:MARK{marker}:TRAC TRAC{trace}")
        self._inst.write(f":CALC:NFIG:MARK{marker}:X {freq_ghz:.2f}GHz")
        time.sleep(0.05)
        y = float(self._inst.query(f":CALC:NFIG:MARK{marker}:Y?"))
        return y

    # ---- PN mode -----------------------------------------------------------

    def pn_set_center_freq(self, freq_ghz: float):
        """Set center frequency for phase noise measurement."""
        self._inst.write(f":FREQ:CENT {freq_ghz:.3f}GHz")

    def pn_init_measurement(self):
        """Single-shot PN measurement with *OPC? synchronization."""
        self._inst.write(":INIT:CONT OFF")
        self._inst.write(":INIT:IMM")
        self._inst.query("*OPC?")

    def pn_read_spot(self, marker_index: int) -> tuple[float, float]:
        """Read PN spot noise: returns (offset_Hz, noise_dBc_per_Hz)."""
        freq_str = self._inst.query(f":CALCulate:LPLot:MARK{marker_index}:X?")
        pn_str = self._inst.query(f":CALCulate:LPLot:MARK{marker_index}:Y?")
        return float(freq_str), float(pn_str)

    # ---- screenshot --------------------------------------------------------

    def screenshot(
        self,
        local_dir: str,
        local_filename: str,
        theme: str = "FCOL",
        internal_path: str = r"D:\User_My_Documents\Instrument\My Documents\tmp.png",
    ) -> str:
        """Capture screen to local PNG file. Returns full local path."""
        self._inst.write(":DISP:FSCR ON")
        self._inst.write(f':MMEM:STOR:SCR:THEM {theme}')
        self._inst.write(f':MMEM:STOR:SCR "{internal_path}"')
        self._inst.query("*OPC?")
        time.sleep(0.5)

        self._inst.write(f':MMEM:DATA? "{internal_path}"')
        raw = self._inst.read_raw()
        # PyVISA returns the whole block including the # header;
        # we strip it manually.
        if raw.startswith(b"#"):
            idx = raw.find(b"\n")
            if idx > 0:
                # #nLEN\n... form
                img_data = raw[idx + 1:]
            else:
                img_data = raw[2:]  # fallback
        else:
            img_data = raw

        os.makedirs(local_dir, exist_ok=True)
        full_path = os.path.join(local_dir, local_filename)
        with open(full_path, "wb") as fh:
            fh.write(img_data)

        self._inst.write(":DISP:FSCR OFF")
        return full_path
