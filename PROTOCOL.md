# IQOS USB protocol notes

Reverse-engineering notes for the **IQOS ILUMA i ONE** over USB, as used by
IQOS Bar. Everything here is read-only and was confirmed on a device the
author owns.

The command layer (report ID, `get()` builder, response field offsets) was
worked out by the **[iqos-scope](https://github.com/SabriEzzine/iqos-scope)**
project — credit to them. This file documents what IQOS Bar relies on, plus a
couple of details specific to reading over `hidapi`.

## Device identity

| Field | Value |
|-------|-------|
| USB Vendor ID | `0x2759` (Philip Morris Products S.A.) |
| USB Product ID | `0x0003` |
| Product string | `IQOS ILUMA i ONE` |
| Interface | HID, vendor usage page `0xFF00`, 2 interrupt endpoints (64 B) |
| HID report ID | `0x3F` |

The same VID/PID has been used by Philip Morris since at least 2016 (the older
"Zurich FPD 4.x Charger" enumerates identically).

## Framing

Host → device, on report ID `0x3F`:

```
0x3F  <len>  <command bytes...>        (padded to 63 bytes)
```

Device → host is also report `0x3F`. **Note on transport offsets:** WebHID
strips the report ID into a separate field, so iqos-scope indexes responses
from byte 0. `hidapi` (what IQOS Bar uses) *prepends* the report ID, so every
offset shifts by one: address bytes land at `r[3]&3` / `r[4]`, and the payload
starts at `r[5]`.

A response also carries a length byte at `r[1]` (counted from `r[2]`); the last
payload byte is a CRC. Bytes past the declared length belong to a background
status/log stream and should be ignored.

## Command builder

```python
def crc8(b):               # poly 0x07, init 0, no reflection, no final XOR
    c = 0
    for x in b:
        c ^= x
        for _ in range(8):
            c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
    return c

def get(net, reg):         # read a register
    a = [reg & 3, (reg >> 2) & 0xFF]
    return [net, *a, crc8(a)]
```

## Read commands used by IQOS Bar

Payload offsets below are **relative to `r[5]`** (the hidapi-adjusted payload
start). `u16(i)` = `r[5+i] | r[5+i+1] << 8`.

| Field | Command | Parse |
|-------|---------|-------|
| Battery % | `get(0xC0, 0x90)` | `u16(0)` |
| Voltage | `get(0xC9, 0x83)` | `u16(0)` |
| Temperature | `get(0xC0, 0x84)` | `u16(0)` |
| Counters | `get(0xC9, 0x86)` | sticks `u16(0)`, **puffs `u16(10)`**, usage¼s `u16(8)<<16 \| u16(6)` |
| Serial | `get(0xC0, 0x0C)` | ASCII of payload |
| Model code | `get(0xC9, 0x88)` | ASCII of payload |

### Verified example

On the author's device, `get(0xC9, 0x86)` returned (with report ID):

```
3f 1c 08 8e 21 44 03 00 00 44 03 22 19 09 00 b8 2e 00 00 10 ...
```

→ sticks `0x0344` = **836**, puffs `0x2EB8` = **11960** (≈14.3 puffs/stick),
and `get(0xC0, 0x0C)` decodes to the exact serial reported by the OS. These
cross-checks confirm the offsets.

The device reports **lifetime totals only** — there is no per-day history on
the device. IQOS Bar derives daily consumption by logging these totals over
time and differencing them.

## Scope

This document covers only reading state. It intentionally does not cover
writing settings, firmware, or anything affecting heating or charging.
