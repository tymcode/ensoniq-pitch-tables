#!/usr/bin/env python3
"""Convert Ensoniq pitch table CSVs to Scala .scl files."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# Ensoniq names: letter, octave, optional trailing '+' (sharp), e.g. C4+, F3.
NOTE_RE = re.compile(r"^([A-G])(\d+)(\+?)$")

# (letter, sharp): physical keys in one octave; last entry is C natural next octave.
SCALE_DEGREES: tuple[tuple[str, bool], ...] = (
    ("C", True),
    ("D", False),
    ("D", True),
    ("E", False),
    ("F", False),
    ("F", True),
    ("G", False),
    ("G", True),
    ("A", False),
    ("A", True),
    ("B", False),
    ("C", False),
)


def physical_key(letter: str, sharp: bool, octave: int) -> str:
    return f"{letter}{octave}{'+' if sharp else ''}"


def parse_note(name: str) -> tuple[int, int]:
    """Return (octave, semitone_class 0..11) for names like C4, C4+, B3."""
    m = NOTE_RE.match(name.strip())
    if not m:
        raise ValueError(f"unrecognized note: {name!r}")
    letter, oct_s, sharp = m.groups()
    pc = LETTER_PC[letter] + (1 if sharp == "+" else 0)
    return int(oct_s), pc


def target_pitch_cents(target_note: str, offset_cents: int) -> float:
    """Absolute cents from C0: 12-TET anchor of target + sharpening offset."""
    oct_, pc = parse_note(target_note)
    return oct_ * 1200.0 + pc * 100.0 + float(offset_cents)


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


def pitch_for_physical_key(by_key: dict[str, dict[str, str]], letter: str, sharp: bool, octave: int) -> float:
    key = physical_key(letter, sharp, octave)
    row = by_key[key]
    off = int(row["offset_cents"].strip())
    return target_pitch_cents(row["target_note"].strip(), off)


def build_scale_degrees(by_key: dict[str, dict[str, str]], ref_octave: int) -> list[float]:
    """Twelve cumulative cents from C(ref); implicit 0 at C same octave."""
    c0 = pitch_for_physical_key(by_key, "C", False, ref_octave)
    out: list[float] = []
    for i, (letter, sharp) in enumerate(SCALE_DEGREES):
        octave = ref_octave + 1 if i == len(SCALE_DEGREES) - 1 else ref_octave
        p = pitch_for_physical_key(by_key, letter, sharp, octave)
        out.append(p - c0)
    return out


def format_cents_line(c: float) -> str:
    """Scala treats a value as cents only if it contains a period."""
    s = f"{c:.5f}".rstrip("0").rstrip(".")
    if "." not in s:
        s += ".0"
    return " " + s


def csv_to_scl(csv_path: Path, out_path: Path, *, rel_from_csv: Path, ref_octave: int = 4) -> None:
    by_key = load_rows(csv_path)
    missing: list[str] = []
    for i, (letter, sharp) in enumerate(SCALE_DEGREES):
        oct_ = ref_octave + 1 if i == len(SCALE_DEGREES) - 1 else ref_octave
        k = physical_key(letter, sharp, oct_)
        if k not in by_key:
            missing.append(k)
    if missing:
        raise ValueError(f"missing source_key rows: {missing}")

    degrees = build_scale_degrees(by_key, ref_octave)
    tuning = next(iter(by_key.values()))["tuning_name"].strip()
    desc = (
        f"Ensoniq pitch table {tuning} "
        f"(chromatic from C{ref_octave}, implicit 0 = physical C)"
    )
    lines: list[str] = [
        f"! {csv_path.name}",
        "!",
        f"! Converted from csv/{rel_from_csv}",
        "! Ensoniq: each key -> 12-TET target_note + offset_cents (sharpen).",
        desc,
        str(len(degrees)),
        "!",
    ]
    for d in degrees:
        lines.append(format_cents_line(d))
    lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_root = root / "csv"
    scl_root = root / "scl"
    if not csv_root.is_dir():
        print("No csv/ directory", file=sys.stderr)
        sys.exit(1)
    for csv_path in sorted(csv_root.rglob("*.csv")):
        rel = csv_path.relative_to(csv_root)
        out_path = scl_root / rel.with_suffix(".scl")
        try:
            csv_to_scl(csv_path, out_path, rel_from_csv=rel)
            print(out_path.relative_to(root))
        except Exception as e:
            print(f"FAIL {rel}: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
