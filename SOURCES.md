# Sources and Bibliography

This project uses practical, performance-oriented approximations of multiple microtonal traditions, adapted to Ensoniq pitch-table patterns.

## Turkish Makam

- Arel, Huseyin Saadettin; Ezgi, Suphi; Uzdilek, Salih Murat. Arel-Ezgi-Uzdilek (AEU) theoretical framework for Turkish makam pitch organization (comma-based model; widely used in conservatory pedagogy).
- Signell, Karl L. *Makam: Modal Practice in Turkish Art Music*. Da Capo Press, 1977.
- Feldman, Walter. *Music of the Ottoman Court: Makam, Composition and the Early Ottoman Instrumental Repertoire*. VWB, 1996.

## Arabic Maqam

- Touma, Habib Hassan. *The Music of the Arabs*. Amadeus Press, 1996.
- Racy, Ali Jihad. *Making Music in the Arab World: The Culture and Artistry of Tarab*. Cambridge University Press, 2003.
- Farraj, Johnny; Abu Shumays, Sami. *Inside Arabic Music: Arabic Maqam Performance and Theory in the 20th Century*. Oxford University Press, 2019.

## Balkan Modal / Intonation Practice

- Rice, Timothy. *May It Fill Your Soul: Experiencing Bulgarian Music*. University of Chicago Press, 1994.
- Pettan, Svanibor (ed.). *Balkan Popular Culture and Ottoman Ecumene: Music, Image, and Regional Political Discourse*. Scarecrow Press, 2010.
- Regional gaida and Balkan dance-music intonation references were additionally informed by practice-oriented ethnomusicology literature and performer traditions.

## Indonesian Tuning Context (Slendro / Pelog)

- Tenzer, Michael. *Gamelan Gong Kebyar: The Art of Twentieth-Century Balinese Music*. University of Chicago Press, 2000.
- Kunst, Jaap. *Music in Java: Its History, Its Theory and Its Technique*. 3rd ed., Martinus Nijhoff, 1973.

## General Tuning / Intonation Theory

- Duffin, Ross W. *How Equal Temperament Ruined Harmony (and Why You Should Care)*. W. W. Norton, 2007.
- Barbour, J. Murray. *Tuning and Temperament: A Historical Survey*. Dover, 2004 (reprint).
- 5-limit just-intonation interval-ratio practice (for the `indian_just_major_c_5limit` style reference table).

These references inform interval tendencies and modal color, not strict one-to-one transcription of any single school.

## MIDI Tuning Standard (`.mts` bulk SysEx exports)

The `mts/` bulk tuning dumps are aligned with the **non-real-time bulk tuning** message layout and **21-bit frequency word** interpretation used in the wild. Verification was done against the reference **MTS-ESP** client implementation:

- **ODDSound / MTS-ESP** — [https://github.com/ODDSound/MTS-ESP](https://github.com/ODDSound/MTS-ESP). In particular, `Client/libMTSClient.cpp` function `parseMIDIData` (bulk / `eBulk` branch): `F0` … `7E` … `08` `01`, 16-byte tuning name, then 128 triplets assembled as `(b0<<14)|(b1<<7)|b2`, coarse pitch `(sysex_value >> 14) & 127`, fractional semitone `(sysex_value & 16383) / 16383.0`, applied as `440.0 * pow(2.0, ((retuneNote + detune) - 69.0) / 12.0)`. The project’s `scripts/csv_to_mts.py` uses that same **16383** fractional denominator and the same A4=440 reference so generated files decode the same way as that client. The MTS-ESP README also describes loading `.scl`, `.kbm`, `.tun`, and MTS SysEx for host-wide retuning.