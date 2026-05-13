#!/usr/bin/env python3
"""
Build MIDI Tuning Standard (MTS) non-real-time bulk tuning dump SysEx files
from Ensoniq-style CSV pitch tables.

Format (MMA / universal SysEx):
  F0 7E <device> 08 01 <program> <16-byte name> <xx yy zz> * 128 <checksum> F7

Frequency packing matches ODDSound MTS-ESP's client parser: three 7-bit data
bytes form a 21-bit word; the high 7 bits are the retune MIDI note, the low
14 bits are the fractional semitone, scaled by **16383** (not 16384) when
converting to/from a 0..1 detune factor — see ``parseMIDIData`` / ``eBulk`` in
`Client/libMTSClient.cpp` in https://github.com/ODDSound/MTS-ESP .

Each note uses three 7-bit data bytes (xx yy zz) for frequency relative to
12-TET with A4 (MIDI 69) = 440 Hz (same reference as ``updateTuning`` in that
client implementation).
"""

from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NOTE_RE = re.compile(r"^([A-G])(-?\d+)(\+?)$")

# MIDI note 0 frequency when A4 (69) = 440 Hz, 12-TET.
MIDI0_REF_HZ = 440.0 * 2.0 ** (-69.0 / 12.0)

# Fractional semitone denominator used by ODDSound MTS-ESP Client (libMTSClient.cpp).
MTS_FRAC_DENOM = 16383


def parse_note(name: str) -> tuple[int, int]:
    m = NOTE_RE.match(name.strip())
    if not m:
        raise ValueError(f"unrecognized note: {name!r}")
    letter, oct_s, sharp = m.groups()
    pc = LETTER_PC[letter] + (1 if sharp == "+" else 0)
    return int(oct_s), pc


def source_key_to_midi(source_key: str) -> int:
    oct_, pc = parse_note(source_key)
    return (oct_ + 1) * 12 + pc


def et_midi_freq(m: int, f0: float = MIDI0_REF_HZ) -> float:
    return f0 * (2.0 ** (m / 12.0))


def hz_to_mts_triplet(f_hz: float, f0: float = MIDI0_REF_HZ) -> tuple[int, int, int]:
    """Three 7-bit bytes for one note; 7F 7F 7F means 'no change' (not used here)."""
    if f_hz <= 0 or not math.isfinite(f_hz):
        return (0, 0, 0)

    # Largest MIDI index m in 0..127 with ET(m) <= f_hz
    lo, hi = 0, 127
    base = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if et_midi_freq(mid, f0) <= f_hz + 1e-12:
            base = mid
            lo = mid + 1
        else:
            hi = mid - 1

    f_lo = et_midi_freq(base, f0)
    if f_hz <= f_lo + 1e-15:
        fs = 0.0
    else:
        fs = 12.0 * math.log2(f_hz / f_lo)  # fractional semitones in [0, ~1)

    frac14 = int(round(fs * float(MTS_FRAC_DENOM)))
    if frac14 >= MTS_FRAC_DENOM + 1 and base < 127:
        base += 1
        f_lo = et_midi_freq(base, f0)
        if f_hz <= f_lo + 1e-15:
            fs = 0.0
        else:
            fs = 12.0 * math.log2(f_hz / f_lo)
        frac14 = int(round(fs * float(MTS_FRAC_DENOM)))

    frac14 = max(0, min(MTS_FRAC_DENOM, frac14))
    b0 = base & 0x7F
    b1 = (frac14 >> 7) & 0x7F
    b2 = frac14 & 0x7F
    return (b0, b1, b2)


def mts_triplet_to_hz(b0: int, b1: int, b2: int, f0: float = MIDI0_REF_HZ) -> float:
    base = b0 & 0x7F
    frac14 = ((b1 & 0x7F) << 7) | (b2 & 0x7F)
    f_lo = et_midi_freq(base, f0)
    fs = frac14 / float(MTS_FRAC_DENOM)
    return f_lo * (2.0 ** (fs / 12.0))


def tuning_name_field(name: str) -> bytes:
    """Exactly 16 bytes, ASCII, space-padded (0x20)."""
    s = name.strip().encode("ascii", errors="replace")[:16]
    return s.ljust(16, b" ")


def mts_checksum(data: bytes) -> int:
    """Lower 7 bits: (sum(data) + checksum) % 128 == 0."""
    s = sum(data) % 128
    return (128 - s) % 128


def build_bulk_tuning_dump(
    *,
    device_id: int = 0x7F,
    program: int,
    tuning_name: str,
    hz_by_midi: list[float],
) -> bytes:
    if len(hz_by_midi) != 128:
        raise ValueError(f"expected 128 frequencies, got {len(hz_by_midi)}")
    program &= 0x7F
    name16 = tuning_name_field(tuning_name)

    inner = bytearray([0x7E, device_id & 0x7F, 0x08, 0x01, program])
    inner.extend(name16)
    for i in range(128):
        b0, b1, b2 = hz_to_mts_triplet(hz_by_midi[i])
        inner.extend((b0, b1, b2))

    chk = mts_checksum(inner)
    return bytes([0xF0]) + bytes(inner) + bytes([chk, 0xF7])


def load_hz_list_ordered(csv_path: Path) -> tuple[list[float], str]:
    by_m: dict[int, float] = {}
    tuning_name = ""
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sk = row.get("source_key", "").strip()
            if not sk or sk == "source_key":
                continue
            m = source_key_to_midi(sk)
            by_m[m] = float(row["frequency_hz"].strip())
            tuning_name = row.get("tuning_name", "").strip() or tuning_name
    missing = [i for i in range(128) if i not in by_m]
    if missing:
        raise ValueError(f"{csv_path}: missing MIDI notes: {missing[:8]}… ({len(missing)} total)")
    return [by_m[i] for i in range(128)], tuning_name


def csv_to_mts(
    csv_path: Path,
    out_path: Path,
    *,
    program: int,
    display_name: str,
) -> None:
    hz128, _t = load_hz_list_ordered(csv_path)
    syx = build_bulk_tuning_dump(program=program, tuning_name=display_name, hz_by_midi=hz128)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(syx)


def _self_test() -> None:
    f440 = 440.0
    t = hz_to_mts_triplet(f440)
    assert t[0] == 69 and t[1] == 0 and t[2] == 0, t
    assert abs(mts_triplet_to_hz(*t) - f440) < 1e-6

    # Same frequency as ODDSound updateTuning(note, retune, detune):
    #   440 * 2^((retune + detune - 69) / 12)
    b0, b1, b2 = t
    frac = ((b1 & 0x7F) << 7) | (b2 & 0x7F)
    det = frac / float(MTS_FRAC_DENOM)
    odds = 440.0 * (2.0 ** ((b0 + det - 69.0) / 12.0))
    assert abs(odds - f440) < 1e-9

    f261 = et_midi_freq(60)
    t2 = hz_to_mts_triplet(f261)
    assert abs(mts_triplet_to_hz(*t2) - f261) < 0.02, (t2, mts_triplet_to_hz(*t2), f261)

    # checksum property (sum(inner)+chk) % 128 == 0
    inner = bytes(range(1, 8))
    c = mts_checksum(inner)
    assert (sum(inner) + c) % 128 == 0


def main() -> None:
    if "--test" in sys.argv:
        _self_test()
        print("mts self-test ok")
        return

    root = Path(__file__).resolve().parents[1]
    csv_root = root / "csv"
    mts_root = root / "mts"
    if not csv_root.is_dir():
        print("No csv/ directory", file=sys.stderr)
        sys.exit(1)

    # EDO linear tables only (full MIDI 0–127 rows required).
    jobs = (
        ("edo_19_linear.csv", "edo_19_linear.mts", 19, "19-EDO linear"),
        ("edo_31_linear.csv", "edo_31_linear.mts", 31, "31-EDO linear"),
    )
    for csv_name, out_name, prog, label in jobs:
        csv_path = csv_root / csv_name
        if not csv_path.is_file():
            print(f"skip missing {csv_path}", file=sys.stderr)
            continue
        out_path = mts_root / out_name
        try:
            csv_to_mts(csv_path, out_path, program=prog, display_name=label)
            print(out_path.relative_to(root))
        except Exception as e:
            print(f"FAIL {csv_name}: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
