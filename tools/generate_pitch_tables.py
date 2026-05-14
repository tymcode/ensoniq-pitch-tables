from __future__ import annotations

import csv
import math
from pathlib import Path

# Ensoniq display convention: sharps show as trailing "+" after octave.
# Example: F#4 is "F4+"
PITCH_CLASS_TO_NAME = [
    ("C", False),
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
]

# 61-key Ensoniq-style span (common C-to-C keyboard range).
START_MIDI = 36  # C2
KEY_COUNT = 61


def midi_to_name(midi_note: int) -> str:
    pitch_class = midi_note % 12
    octave = (midi_note // 12) - 1
    letter, sharp = PITCH_CLASS_TO_NAME[pitch_class]
    return f"{letter}{octave}{'+' if sharp else ''}"


def encode_target_from_deviation(midi_note: int, deviation_cents: float) -> tuple[str, int]:
    """
    Convert a desired tuning (in cents deviation from 12-TET key pitch) into:
    - target chromatic note name with octave (naturals/sharps only)
    - positive cents offset in [0, 99]
    """
    desired_cents = (midi_note * 100.0) + deviation_cents
    target_note = int(desired_cents // 100)
    cents = int(round(desired_cents - (target_note * 100)))

    if cents == 100:
        target_note += 1
        cents = 0
    elif cents < 0:
        target_note -= 1
        cents += 100

    pitch_class = target_note % 12
    octave = (target_note // 12) - 1
    letter, sharp = PITCH_CLASS_TO_NAME[pitch_class]
    return f"{letter}{octave}{'+' if sharp else ''}", cents


def build_table_rows(name: str, deviations_by_pc: dict[int, float]) -> list[list[str]]:
    rows: list[list[str]] = []
    for midi_note in range(START_MIDI, START_MIDI + KEY_COUNT):
        pitch_class = midi_note % 12
        source = midi_to_name(midi_note)
        deviation = deviations_by_pc.get(pitch_class, 0.0)
        target_note, cents = encode_target_from_deviation(midi_note, deviation)
        frequency_hz = 440.0 * math.pow(2.0, ((midi_note - 69) + (deviation / 100.0)) / 12.0)
        # Avoid ambiguity since "+" is also used to display sharps (e.g. "F4+").
        mapping = f"{source}={target_note} {cents:02d} cents"
        rows.append([source, target_note, f"{cents:02d}", f"{frequency_hz:.2f}", mapping, name])
    return rows


# Full MIDI pitch range (note numbers 0–127 inclusive).
MIDI_FULL_RANGE = range(0, 128)

# Standard 88-key piano range (inclusive).
MIDI_88_A0 = 21
MIDI_88_C8 = 108
MIDI_88_RANGE = range(MIDI_88_A0, MIDI_88_C8 + 1)


def _edo_degree_offsets(step_pattern: tuple[int, ...], n: int) -> tuple[int, ...]:
    """Scale degrees 0..n-1 (unique) from one period of a step cycle summing to n."""
    if sum(step_pattern) != n:
        raise ValueError(f"step pattern must sum to n={n}, got {sum(step_pattern)}")
    cum = 0
    offs: list[int] = [0]
    for s in step_pattern:
        cum += s
        offs.append(cum % n)
    return tuple(sorted(set(offs)))


def build_subset_nearest_88key_rows(
    name: str,
    n: int,
    step_pattern: tuple[int, ...],
    *,
    description_comment: str = "",
) -> list[list[str]]:
    """
    Map each chromatic MIDI key on an 88-key (A0–C8) span to the **nearest**
    pitch in the repeating n-EDO MOS defined by ``step_pattern`` (sums to n).

    Tonic: MIDI 69 (A4) = 440 Hz at EDO step 0. Each candidate pitch is
    ``440 * 2 ** (d / n)`` for integer step d = degree + j*n.

    ``description_comment`` is unused in CSV; kept for caller documentation.
    """
    _ = description_comment
    degrees = _edo_degree_offsets(step_pattern, n)
    rows: list[list[str]] = []

    # Precompute candidate steps near the 88-key band (in units of n-EDO steps from A4).
    j_lo, j_hi = -24, 24
    candidates: list[int] = []
    for j in range(j_lo, j_hi + 1):
        for deg in degrees:
            candidates.append(deg + j * n)

    for midi_note in MIDI_88_RANGE:
        f_et = 440.0 * math.pow(2.0, (midi_note - 69) / 12.0)
        d_want = (midi_note - 69) * (n / 12.0)
        best_d = min(candidates, key=lambda d: abs(d - d_want))
        f_hz = 440.0 * math.pow(2.0, best_d / float(n))
        deviation = 1200.0 * math.log2(f_hz / f_et) if f_et > 0 else 0.0
        source = midi_to_name(midi_note)
        target_note, cents = encode_target_from_deviation(midi_note, deviation)
        mapping = f"{source}={target_note} {cents:02d} cents"
        rows.append([source, target_note, f"{cents:02d}", f"{f_hz:.2f}", mapping, name])
    return rows


def build_linear_edo_rows(name: str, n: int) -> list[list[str]]:
    """
    Linear n-EDO mapped to the chromatic MIDI keyboard: each +1 MIDI note raises
    pitch by exactly one step of n-EDO (so one physical octave spans 12/n octaves).
    A4 (MIDI 69) = 440 Hz. Deviations are expressed vs 12-TET for Ensoniq encoding.

    Rows cover **MIDI 0–127** (128 notes), including C-1 through G9+ naming, so
    `.tun` exports need no synthetic fill inside standard MIDI.
    """
    rows: list[list[str]] = []
    for midi_note in MIDI_FULL_RANGE:
        deviation = (midi_note - 69) * 100.0 * (12.0 / n - 1.0)
        source = midi_to_name(midi_note)
        target_note, cents = encode_target_from_deviation(midi_note, deviation)
        frequency_hz = 440.0 * math.pow(2.0, ((midi_note - 69) + (deviation / 100.0)) / 12.0)
        mapping = f"{source}={target_note} {cents:02d} cents"
        rows.append([source, target_note, f"{cents:02d}", f"{frequency_hz:.2f}", mapping, name])
    return rows


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["source_key", "target_note", "offset_cents", "frequency_hz", "display_mapping", "tuning_name"]
        )
        writer.writerows(rows)


def transpose_deviations_by_pc(deviations_by_pc: dict[int, float], semitones: int) -> dict[int, float]:
    return {(pc + semitones) % 12: cents for pc, cents in deviations_by_pc.items()}


def main() -> None:
    out_dir = Path("csv")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pitch-class keys:
    # C=0, C+=1, D=2, D+=3, E=4, F=5, F+=6, G=7, G+=8, A=9, A+=10, B=11
    arabic_bayati_a = {6: -50, 11: -50}
    turkish_hicaz_a = {1: -14, 2: -2, 4: 2, 5: 14, 7: -12, 10: 13}
    balkan_gaida_thracian_a = {0: 15, 4: -35, 6: 10, 11: -35}
    balkan_hijaz_a = {11: -70, 2: 18, 5: -70, 7: -20}

    tunings = {
        # Useful neutral baseline for comparison.
        "12tet_reference": {},
        # 24-TET style split where each sharp key is raised by 50 cents.
        "arabic_24tet_quartertone_grid": {1: 50, 3: 50, 6: 50, 8: 50, 10: 50},
        # Common practical approximation of C Rast: E and B half-flat.
        "arabic_rast_c_approx": {4: -50, 11: -50},
        # Common practical approximation of D Bayati flavor: E half-flat, B half-flat.
        "arabic_bayati_d_approx": {4: -50, 11: -50},
        # Native A-centered Bayati flavor (transposed practical mapping).
        "arabic_bayati_a_approx": arabic_bayati_a,
        # Native G-centered Bayati flavor.
        "arabic_bayati_g_approx": transpose_deviations_by_pc(arabic_bayati_a, -2),
        # Native E-centered Bayati flavor.
        "arabic_bayati_e_approx": transpose_deviations_by_pc(arabic_bayati_a, -5),
        # D Saba-flavored approximation: E half-flat, F# half-flat, B half-flat.
        "arabic_saba_d_approx": {4: -50, 6: -50, 11: -50},
        # Turkish AEU-flavored C Rast approximation (comma-based -> nearest cent).
        "turkish_rast_c_aeu_approx": {2: 4, 4: -15, 5: -2, 7: 2, 9: 6, 11: -23},
        # Turkish AEU-flavored D Hicaz approximation.
        "turkish_hicaz_d_aeu_approx": {0: -12, 3: 13, 6: -14, 7: -2, 9: 2, 10: 14},
        # Native A-centered Turkish Hicaz approximation (transposed from D-centered profile).
        "turkish_hicaz_a_aeu_approx": turkish_hicaz_a,
        # Native G-centered Turkish Hicaz approximation.
        "turkish_hicaz_g_aeu_approx": transpose_deviations_by_pc(turkish_hicaz_a, -2),
        # Native E-centered Turkish Hicaz approximation.
        "turkish_hicaz_e_aeu_approx": transpose_deviations_by_pc(turkish_hicaz_a, -5),
        # Persian D Shur-ish practical mapping (koron-like lowered 2nd above tonic context).
        "persian_shur_d_approx": {4: -50, 11: -30},
        # Persian D Homayun-ish flavor (lowered 2nd and 6th regions).
        "persian_homayun_d_approx": {4: -50, 9: -35, 11: -50},
        # 5-limit just major reference around C (global pitch-class temperament flavor).
        "indian_just_major_c_5limit": {2: -4, 4: -14, 5: 2, 7: 2, 9: -16, 11: -12},
        # Slendro-like 5-tone spread adapted to 12-key keyboard map.
        "indonesian_slendro_approx": {2: 40, 4: -20, 7: 20, 9: -40},
        # Pelog-like uneven 7-tone spread adapted to 12-key keyboard map.
        "indonesian_pelog_approx": {2: -30, 4: 20, 6: -40, 7: 10, 9: -20, 11: 30},
        # Balkan gaida-style intonation tendency (slightly low 3rd and 7th).
        "balkan_gaida_c_approx": {4: -30, 11: -30},
        # Balkan Hijaz-style practical approximation on D with neutralized 2nd/6th inflection.
        "balkan_hijaz_d_approx": {4: -70, 6: -20, 9: -70, 1: -20},
        # Performance pack: tighter Balkan / gaida-oriented variants.
        # Thracian gaida flavor centered on A drone tendency (low 3rd, high 4th touch, low 7th).
        "balkan_gaida_thracian_a_centered": balkan_gaida_thracian_a,
        # Thracian gaida flavor centered on G.
        "balkan_gaida_thracian_g_centered": transpose_deviations_by_pc(balkan_gaida_thracian_a, -2),
        # Thracian gaida flavor centered on E.
        "balkan_gaida_thracian_e_centered": transpose_deviations_by_pc(balkan_gaida_thracian_a, -5),
        # Macedonian gaida flavor centered on G (compressed 2nd, low 3rd, low 6th).
        "balkan_gaida_macedonian_g_centered": {9: -25, 11: -35, 2: -15, 4: 5},
        # Bulgarian kaba gaida flavor centered on D (low 3rd and 7th, slightly bright 4th).
        "balkan_kaba_gaida_d_centered": {4: -35, 6: 12, 11: -30},
        # Balkan Hijaz variant centered on A (deeper lowered 2nd and 6th, brightened 3rd).
        "balkan_hijaz_a_centered": balkan_hijaz_a,
        # Balkan Hijaz variant centered on G.
        "balkan_hijaz_g_centered": transpose_deviations_by_pc(balkan_hijaz_a, -2),
        # Balkan Hijaz variant centered on E.
        "balkan_hijaz_e_from_a_centered": transpose_deviations_by_pc(balkan_hijaz_a, -5),
        # Balkan Hijaz variant centered on E (common dance-melody register orientation).
        "balkan_hijaz_e_centered": {7: -65, 10: 15, 1: -65, 3: -15},
        # Balkan Ussak-ish practical flavor centered on D (neutral 3rd and low 7th tendencies).
        "balkan_ussak_d_centered": {4: -45, 11: -35, 1: -10},
    }

    for tuning_name, deviations in tunings.items():
        rows = build_table_rows(tuning_name, deviations)
        write_csv(out_dir / f"{tuning_name}.csv", rows)

    # n-EDO assets live under csv/19-edo/ and csv/31-edo/ (linear + 88-key subset maps).
    edo19 = out_dir / "19-edo"
    edo31 = out_dir / "31-edo"
    edo19.mkdir(parents=True, exist_ok=True)
    edo31.mkdir(parents=True, exist_ok=True)

    # Linear: each MIDI semitone = one n-EDO step; A4 = 440 Hz.
    write_csv(edo19 / "edo_19_linear.csv", build_linear_edo_rows("edo_19_linear", 19))
    write_csv(edo31 / "edo_31_linear.csv", build_linear_edo_rows("edo_31_linear", 31))

    # 88-key (A0–C8): nearest pitch on a heptatonic MOS (LLsLLLs) inside n-EDO.
    # 19-EDO: L=3, s=2 → 3+3+2+3+3+3+2 = 19.
    write_csv(
        edo19 / "diatonic7_88key.csv",
        build_subset_nearest_88key_rows(
            "edo_19_diatonic7_88key",
            19,
            (3, 3, 2, 3, 3, 3, 2),
            description_comment="19-EDO heptatonic MOS LLsLLLs (L=3,s=2); nearest to 12-TET per key",
        ),
    )
    # 31-EDO: L=5, s=3 → 5+5+3+5+5+5+3 = 31.
    write_csv(
        edo31 / "diatonic7_88key.csv",
        build_subset_nearest_88key_rows(
            "edo_31_diatonic7_88key",
            31,
            (5, 5, 3, 5, 5, 5, 3),
            description_comment="31-EDO heptatonic MOS LLsLLLs (L=5,s=3); nearest to 12-TET per key",
        ),
    )
    # 31-EDO 9-note MOS: 5×3 + 4×4 = 31 (five small 3, four large 4). Step cycle:
    # 3,3,4,3,3,4,3,4,4 — common unequal 9-step pattern on 31.
    write_csv(
        edo31 / "orwell9_88key.csv",
        build_subset_nearest_88key_rows(
            "edo_31_orwell9_88key",
            31,
            (3, 3, 4, 3, 3, 4, 3, 4, 4),
            description_comment="31-EDO 9-step MOS (5×3 + 4×4); nearest to 12-TET per key",
        ),
    )


if __name__ == "__main__":
    main()
