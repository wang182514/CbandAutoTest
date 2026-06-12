"""
RF Switch Matrix (UDC-0624F) via UART serial.
Replaces MATLAB's serial() + GenerateFrame / UART_SetUDC pattern.
"""

import struct
import time
from typing import List, Optional
import serial
import serial.tools.list_ports


class SwitchMatrix:
    """UDC-0624F RF switch matrix via UART."""

    # Protocol constants
    HEAD = bytes([0x51, 0xAA, 0x5A])  # for PSA / legacy commands
    UDC_HEAD = bytes([85, 68, 67])     # [0x55, 0x44, 0x43]

    def __init__(
        self,
        com_port: str = "COM6",
        baud_rate: int = 115200,
        timeout_sec: float = 1.0,
    ):
        self._com_port = com_port
        self._baud_rate = baud_rate
        self._timeout = timeout_sec
        self._ser: Optional[serial.Serial] = None

    # ---- connection --------------------------------------------------------

    def connect(self):
        """Open serial port."""
        self._ser = serial.Serial(
            port=self._com_port,
            baudrate=self._baud_rate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self._timeout,
        )
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    def disconnect(self):
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._ser = None

    @property
    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    # ---- PSA-style command (Test0_INSTR_INIT) ------------------------------

    def psa_set_mode(self, mode: int, sw_on: List[int]):
        """
        Send PSA mode-set command.
        mode: hex mode, e.g. 0xA1 (TRSet_Mod)
        sw_on: [SW1, SW2, SW3] — 0 or 1 each
        """
        ctrl_data = [0] + sw_on + [mode]
        ctrl_lengths = [5, 1, 1, 1, 8]
        ctrl_body = self._generate_frame(ctrl_data, ctrl_lengths)
        ctrl_body_size = len(ctrl_body)

        cmd = [0x51, 0xAA, 0x5A, ctrl_body_size] + list(ctrl_body)
        checksum = sum(cmd) % 256
        frame = bytes(cmd + [checksum])

        self._ser.write(frame)
        back = self._ser.read(9)

        if len(back) >= 9 and back[0] == 0x51 and back[1] == 0xAA and back[2] == 0x5A:
            temp_code = back[6] * 256 + back[7]
            temp_deg = temp_code / 100.0
            ack = back[4] * 256 + back[5]
            lo_lck = back[8]
            return {"temperature_c": temp_deg, "ack": ack, "lo_lock": lo_lck}
        return None

    # ---- UDC command (SetMSWitch / UART_SetUDC) ---------------------------

    def set_udc_switches(self, sw1: int, sw2: int, sw3: int, sw4: int):
        """
        Set UDC switch states via OpMode=2.
        sw1..sw4: 0 or 1
        """
        self._set_udc(op_mode=2, lo_en=1, sw1=sw1, sw2=sw2, sw3=sw3, sw4=sw4)

    def save_udc_config(self):
        """Save current UDC config to flash (OpMode=31)."""
        self._set_udc(op_mode=31)

    # ---- internal ----------------------------------------------------------

    def _set_udc(
        self,
        op_mode: int,
        freq: int = 3950,
        tgain: int = 40,
        lo_en: int = 1,
        sw1: int = 0,
        sw2: int = 0,
        sw3: int = 0,
        sw4: int = 0,
    ):
        """Build and send a UDC control frame."""
        payload = self._build_ctrl_packet(
            op_mode=op_mode,
            freq=freq,
            tgain=tgain,
            lo_en=lo_en,
            sw1=sw1,
            sw2=sw2,
            sw3=sw3,
            sw4=sw4,
        )
        checksum = (sum(self.UDC_HEAD) + sum(payload)) % 256
        frame = self.UDC_HEAD + payload + bytes([checksum])
        self._ser.write(frame)
        time.sleep(0.05)
        # Read 8-byte response (best-effort)
        try:
            self._ser.read(8)
        except Exception:
            pass

    def _build_ctrl_packet(
        self,
        op_mode: int,
        freq: int = 0,
        tgain: int = 0,
        lo_en: int = 0,
        sw1: int = 0,
        sw2: int = 0,
        sw3: int = 0,
        sw4: int = 0,
    ) -> bytes:
        """Build the 5-byte control packet [data0..data3, op_mode]."""
        freq_h = (freq >> 8) & 0xFF
        freq_l = freq & 0xFF

        if op_mode == 1:
            payload = [freq_h, freq_l, (tgain * 2) & 0xFF, 0]
        elif op_mode == 2:
            sw_val = (sw4 << 3) | (sw3 << 2) | (sw2 << 1) | sw1
            payload = [0, 0, lo_en & 0xFF, sw_val & 0xFF]
        elif op_mode in (15, 31, 63):
            payload = [0, 0, 0, 0]
        else:
            payload = [0, 0, 0, 0]
        payload.append(op_mode & 0xFF)
        return bytes(payload)

    def _generate_frame(
        self, ctrl_elements: List[int], ctrl_lengths: List[int]
    ) -> List[int]:
        """Binary frame builder — mirrors GenerateFrame.m exactly."""
        if len(ctrl_elements) != len(ctrl_lengths):
            return [0]

        bit_string = ""
        for val, bits in zip(ctrl_elements, ctrl_lengths):
            val = max(0, min(val, (1 << bits) - 1))
            bit_string = format(val, f"0{bits}b") + bit_string

        total_bits = sum(ctrl_lengths)
        pad = (8 - total_bits % 8) % 8
        bit_string = "0" * pad + bit_string

        body = []
        for i in range(0, len(bit_string), 8):
            body.append(int(bit_string[i : i + 8], 2))
        return body
