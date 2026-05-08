from __future__ import annotations

import csv
from pathlib import Path

NOTE_NAMES = ["C", "C+", "D", "D+", "E", "F", "F+", "G", "G+", "A", "A+", "B"]

# 61-key Ensoniq-style span (common C-to-C keyboard range).
START_MIDI = 36  # C2
KEY_COUNT = 61


def midi_to_name(midi_note: int) -> str:
    pitch_class = midi_note % 12
    octave = (midi_note // 12) - 1
    return f"{NOTE_NAMES[pitch_class]}{octave}"


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
    return f"{NOTE_NAMES[pitch_class]}{octave}", cents


def build_table_rows(name: str, deviations_by_pc: dict[int, float]) -> list[list[str]]:
    rows: list[list[str]] = []
    for midi_note in range(START_MIDI, START_MIDI + KEY_COUNT):
        pitch_class = midi_note % 12
        source = midi_to_name(midi_note)
        deviation = deviations_by_pc.get(pitch_class, 0.0)
        target_note, cents = encode_target_from_deviation(midi_note, deviation)
        mapping = f"{source}={target_note}+{cents:02d} cents"
        rows.append([source, target_note, f"{cents:02d}", mapping, name])
    return rows


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source_key", "target_note", "offset_cents", "display_mapping", "tuning_name"])
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


if __name__ == "__main__":
    main()
