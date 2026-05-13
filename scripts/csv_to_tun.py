#!/usr/bin/env python3
"""Convert Ensoniq pitch table CSVs to AnaMark .tun files (Exact Tuning, V1-style)."""

from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NOTE_RE = re.compile(r"^([A-G])(-?\d+)(\+?)$")

# A=440 ET: MIDI 0 frequency (matches AnaMark TUN_Scale.cpp DefaultBaseFreqHz / InitEqual math)
INIT_EQUAL_MIDI = 69
INIT_EQUAL_HZ = 440.0
BASE_FREQ_HZ = INIT_EQUAL_HZ * 2.0 ** (-INIT_EQUAL_MIDI / 12.0)

# Matches AnaMark TUN_Scale.h FormatSpecs() string content.
FORMAT_SPECS = (
    "http:"
    + chr(92) * 2
    + "www.mark-henning.de"
    + chr(92)
    + "eternity"
    + chr(92)
    + "tuningspecs.html"
)


def parse_note(name: str) -> tuple[int, int]:
    """Return (octave, semitone_class 0..11) for names like C4, C4+, B3."""
    m = NOTE_RE.match(name.strip())
    if not m:
        raise ValueError(f"unrecognized note: {name!r}")
    letter, oct_s, sharp = m.groups()
    pc = LETTER_PC[letter] + (1 if sharp == "+" else 0)
    return int(oct_s), pc


def source_key_to_midi(source_key: str) -> int:
    """Ensoniq key to MIDI note (C4 = 60)."""
    oct_, pc = parse_note(source_key)
    return (oct_ + 1) * 12 + pc


def tun_escape(s: str) -> str:
    out: list[str] = []
    for ch in s:
        o = ord(ch)
        if ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif o < 0x20 or o == 0xFF:
            out.append(f"\\x{o:02x}")
        else:
            out.append(ch)
    return "".join(out)


def tun_quote(s: str) -> str:
    return '"' + tun_escape(s) + '"'


def load_rows(path: Path) -> dict[str, dict[str, str]]:
    by_key: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sk = row.get("source_key", "").strip()
            if not sk or sk == "source_key":
                continue
            by_key[sk] = row
    return by_key


def hz_from_csv_rows(by_key: dict[str, dict[str, str]]) -> dict[int, float]:
    """MIDI note -> frequency (Hz) from frequency_hz column."""
    out: dict[int, float] = {}
    for sk, row in by_key.items():
        try:
            m = source_key_to_midi(sk)
        except ValueError:
            continue
        out[m] = float(row["frequency_hz"].strip())
    return out


def hz_for_midi(midi: int, by_midi: dict[int, float]) -> float:
    """CSV Hz when present; otherwise A=440 12-TET (AnaMark InitEqual-style)."""
    if midi in by_midi:
        return by_midi[midi]
    return INIT_EQUAL_HZ * 2.0 ** ((midi - INIT_EQUAL_MIDI) / 12.0)


def hz_to_cents_from_base(hz: float, base_hz: float = BASE_FREQ_HZ) -> float:
    return 1200.0 * math.log(hz / base_hz, 2)


def build_tun_text(*, tuning_name: str, rel_from_csv: Path, by_midi: dict[int, float]) -> str:
    lines: list[str] = [
        ";",
        "; This is an AnaMark tuning map file V2.00",
        ";",
        "; Converted from Ensoniq pitch table CSV",
        ";",
        "",
        "",
        ";",
        "; Begin of tuning file and format declaration",
        ";",
        "[Scale Begin]",
        f"Format = {tun_quote('AnaMark-TUN')}",
        "FormatVersion = 200",
        f"FormatSpecs = {tun_quote(FORMAT_SPECS)}",
        "",
        "",
        ";",
        "; Scale informations",
        ";",
        "[Info]",
        f"Name = {tun_quote(tuning_name)}",
        f"Description = {tun_quote(f'Ensoniq pitch table {tuning_name}; csv/{rel_from_csv}; target_note + offset_cents vs 12-TET.')}",
        "",
        "",
        ";",
        "; Version 1:",
        "; AnaMark-specific section with exact tunings",
        ";",
        "[Exact Tuning]",
        f"BaseFreq = {BASE_FREQ_HZ:.10f}",
    ]
    for i in range(128):
        hz = hz_for_midi(i, by_midi)
        cents = hz_to_cents_from_base(hz)
        if abs(cents) < 1e-8:
            cents = 0.0
        lines.append(f"Note {i} = {cents:.10f}".rstrip("0").rstrip("."))
    lines.extend(["", "", ";", "; End of tuning file", ";", "[Scale End]", "", ""])
    return "\n".join(lines)


def csv_to_tun(csv_path: Path, out_path: Path, *, rel_from_csv: Path) -> None:
    by_key = load_rows(csv_path)
    by_midi = hz_from_csv_rows(by_key)
    if not by_midi:
        raise ValueError("no MIDI frequencies parsed")
    tuning = next(iter(by_key.values()))["tuning_name"].strip()
    text = build_tun_text(tuning_name=tuning, rel_from_csv=rel_from_csv, by_midi=by_midi)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_root = root / "csv"
    tun_root = root / "tun"
    if not csv_root.is_dir():
        print("No csv/ directory", file=sys.stderr)
        sys.exit(1)
    for csv_path in sorted(csv_root.rglob("*.csv")):
        rel = csv_path.relative_to(csv_root)
        out_path = tun_root / rel.with_suffix(".tun")
        try:
            csv_to_tun(csv_path, out_path, rel_from_csv=rel)
            print(out_path.relative_to(root))
        except Exception as e:
            print(f"FAIL {rel}: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
