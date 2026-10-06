"""Read-only USB HID reader for IQOS ILUMA (i) ONE devices.

The device shows up as a vendor HID device (VID 0x2759 / PID 0x0003). We only
send read commands and parse the replies — nothing here writes to the device.

Register map and framing are from iqos-scope
(https://github.com/SabriEzzine/iqos-scope); see PROTOCOL.md.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import hid

VID = 0x2759
PID = 0x0003
REPORT_ID = 0x3F


def crc8(data: list[int] | bytes) -> int:
    """CRC-8, polynomial 0x07, init 0, no reflection, no final XOR."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def get(net: int, reg: int) -> list[int]:
    """Build a read command for a register `reg` on network `net`."""
    addr = [reg & 3, (reg >> 2) & 0xFF]
    return [net, *addr, crc8(addr)]


@dataclass
class Snapshot:
    """A single read of device state. Fields are None when unavailable."""

    connected: bool = False
    battery_percent: int | None = None
    voltage_mv: int | None = None
    temperature: int | None = None
    total_sticks: int | None = None
    total_puffs: int | None = None
    usage_seconds: int | None = None
    serial: str | None = None
    model_code: str | None = None
    product: str | None = None


class IqosReader:
    def __init__(self) -> None:
        self._dev: hid.device | None = None
        self._product: str | None = None

    def open(self) -> bool:
        for info in hid.enumerate(VID, PID):
            try:
                dev = hid.device()
                dev.open_path(info["path"])
                dev.set_nonblocking(True)
            except OSError:
                # Device present but briefly held by another process; try later.
                return False
            self._dev = dev
            self._product = info.get("product_string") or None
            return True
        return False

    def close(self) -> None:
        if self._dev is not None:
            try:
                self._dev.close()
            except OSError:
                pass
            self._dev = None

    @property
    def is_open(self) -> bool:
        return self._dev is not None

    def _cmd(self, body: list[int], wait: float = 0.45) -> bytes | None:
        """Send a command and return the first matching response, or None.

        Framing: report ID 0x3F, then [length, body...] padded to 63 bytes.
        hidapi prepends the report id to reads, so responses are one byte
        further along than in a WebHID (reportId-stripped) transport: the
        address bytes land at r[3]&3 / r[4] and the payload starts at r[5].
        """
        payload = bytes([len(body)]) + bytes(body)
        payload = payload + bytes(63 - len(payload))
        self._dev.write([REPORT_ID, *payload])

        want_lo, want_hi = body[1] & 3, body[2]
        deadline = time.time() + wait
        while time.time() < deadline:
            report = self._dev.read(64)
            if not report:
                time.sleep(0.005)
                continue
            r = bytes(report)
            if len(r) >= 5 and (r[3] & 3) == want_lo and r[4] == want_hi:
                return r
        return None

    # Payload offsets are relative to r[5] (first byte after the report id,
    # length, and address bytes).
    @staticmethod
    def _u16(r: bytes | None, i: int) -> int | None:
        if r is None or len(r) <= 5 + i + 1:
            return None
        return r[5 + i] | (r[5 + i + 1] << 8)

    @staticmethod
    def _val8(r: bytes | None) -> int | None:
        if r is None or len(r) <= 5:
            return None
        return r[5]

    @staticmethod
    def _ascii(r: bytes | None) -> str | None:
        if r is None or len(r) <= 5:
            return None
        # r[1] is the payload length (counted from r[2]); the last byte is a
        # CRC. Everything after that belongs to the streaming log, so bound
        # the scan to the declared payload to avoid trailing garbage.
        end = min(len(r), 2 + r[1])
        text = bytes(b for b in r[5:end] if 32 <= b < 127).decode("ascii", "ignore")
        return text.strip() or None

    def read(self) -> Snapshot:
        if self._dev is None and not self.open():
            return Snapshot(connected=False)

        try:
            battery = self._u16(self._cmd(get(0xC0, 0x90)), 0)
            voltage = self._u16(self._cmd(get(0xC9, 0x83)), 0)
            temp = self._u16(self._cmd(get(0xC0, 0x84)), 0)

            counters = self._cmd(get(0xC9, 0x86))
            sticks = self._u16(counters, 0)
            puffs = self._u16(counters, 10)
            lo, hi = self._u16(counters, 6), self._u16(counters, 8)
            usage_s = ((hi << 16) | lo) // 4 if lo is not None and hi is not None else None

            serial = self._ascii(self._cmd(get(0xC0, 0x0C)))
            model = self._ascii(self._cmd(get(0xC9, 0x88)))
        except OSError:
            self.close()
            return Snapshot(connected=False)

        return Snapshot(
            connected=True,
            battery_percent=battery if (battery is None or battery <= 100) else None,
            voltage_mv=voltage,
            temperature=temp,
            total_sticks=sticks,
            total_puffs=puffs,
            usage_seconds=usage_s,
            serial=serial,
            model_code=model,
            product=self._product,
        )


if __name__ == "__main__":
    reader = IqosReader()
    if not reader.open():
        raise SystemExit("IQOS device not found over USB.")
    s = reader.read()
    print(f"Model:    {s.model_code}")
    print(f"Serial:   {s.serial}")
    print(f"Battery:  {s.battery_percent}%  ({s.voltage_mv} mV)")
    print(f"Temp:     {s.temperature}")
    print(f"Sticks:   {s.total_sticks} (lifetime)")
    print(f"Puffs:    {s.total_puffs} (lifetime)")
    print(f"Usage:    {s.usage_seconds} s (lifetime)")
