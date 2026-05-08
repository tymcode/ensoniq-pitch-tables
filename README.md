# Ensoniq Microtonal Pitch Tables and Live Set Guide

These are microtonal pitch tables for use with vintage Ensoniq samplers like the EPS-16+ and the ASR-10, and the ASR-V emulator. (Probably many Ensoniq synthesizers as well.) Ensoniq pitch tables are transposition-mapped to nearest naturals or sharps with an offset of cents (sharpening – positive numbers only). These tables focus on makam/maqam and Balkan tables because those are the ones I like.

Rows read like so:

`F4+,F4,50,359.46,F4+=F4 50 cents,arabic_bayati_a_approx`

The first column is the name of the keyboard key.  The second is the target chromatic note, the third is the offset in cents.  The remaining columns are ancillary; frequency, how it appears in the keyboard's display, and the name of the table.

The above example would look like so in the keyboard's display:

![Editing Pitch Table](./pitchtable.png)

## Tonic Folders

The *note*_tonic folders are for use when your drone/home tone is *note*

## Suggested 4-Table Live Set (per tonic folder)

- `arabic_bayati_*` -> warm, vocal, introspective, neutral-second color
- `turkish_hicaz_*` -> tense, dramatic, ornamental lead lines
- `balkan_gaida_thracian_*` or related gaida table -> drone-forward folk color
- `balkan_hijaz_*` -> dance/drive with stronger altered-second pull

## Quick Performance Workflow

1. Pick the tonic folder matching your current song center.
2. Start with Bayati for stable melodic passages.
3. Switch to Hicaz for tension sections or cadential lift.
4. Use Gaida/Balkan variants for folk-heavy tunes and drone textures.

On an Ensoniq keyboard the best way to do this is to duplicate layers and set the different pitch tables for each layer.  Then set each to be active with specific combinations of the patch select buttons of your choosing.  Note that you can set a foot switch to activate a patch select and switch tables with your foot.

## Acknowledgements / Sources

- Turkish makam pitch logic (including comma-based practice and AEU framing): Arel-Ezgi-Uzdilek theory literature and modern explanatory summaries of that system.
- Arabic maqam practical intonation references: Ali Jihad Racy and Johnny Farraj / Sami Abu Shumays style pedagogical treatments of jins/maqam intonation and performance practice.
- Comparative Middle Eastern tuning context: Habib Hassan Touma, *The Music of the Arabs*.
- Balkan modal/intonation performance context (gaida/hijaz-type color): ethnomusicology and regional practice-oriented descriptions of Bulgarian/Macedonian/Thracian traditions.
- Just-intonation baseline references used for the "just major" style table: 5-limit interval ratio practice (common tuning theory sources).
- Indonesian slendro/pelog approximation basis: standard gamelan interval-distribution descriptions, then mapped to the Ensoniq keyboard limitations.
