"""Raw frame dumper for contributors reverse-engineering the USB protocol.

Sends read-only register queries and prints the raw responses, so new fields
can be mapped. See PROTOCOL.md for the framing and offsets.

Usage:  python tools/dump.py
"""

from __future__ import annotations

import time

import hid

VID, PID = 0x2759, 0x0003
REPORT_ID = 0x3F


def crc8(data) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def get(net: int, reg: int) -> list[int]:
    addr = [reg & 3, (reg >> 2) & 0xFF]
    return [net, *addr, crc8(addr)]


# Read-only register queries (name -> command bytes). Add more as discovered.
READ_COMMANDS = {
    "battery_percent": get(0xC0, 0x90),
    "voltage": get(0xC9, 0x83),
    "temperature": get(0xC0, 0x84),
    "counters": get(0xC9, 0x86),
    "session": get(0xC9, 0x85),
    "serial": get(0xC0, 0x0C),
    "model_code": get(0xC9, 0x88),
    "stick_inserted": get(0xC0, 0x81),
    "error_state": get(0xC0, 0x82),
}


def main() -> None:
    infos = hid.enumerate(VID, PID)
    if not infos:
        raise SystemExit("IQOS device not found.")
    dev = hid.device()
    dev.open_path(infos[0]["path"])
    dev.set_nonblocking(True)

    for name, command in READ_COMMANDS.items():
        payload = bytes([len(command)]) + bytes(command)
        payload = payload + bytes(63 - len(payload))
        dev.write([REPORT_ID, *payload])
        want_lo, want_hi = command[1] & 3, command[2]
        response = None
        deadline = time.time() + 0.6
        while time.time() < deadline:
            report = dev.read(64)
            if report:
                r = bytes(report)
                if len(r) >= 5 and (r[3] & 3) == want_lo and r[4] == want_hi:
                    response = r
                    break
            else:
                time.sleep(0.005)
        print(f"{name:16} tx={bytes(command).hex():10} rx={response.hex() if response else None}")


if __name__ == "__main__":
    main()
