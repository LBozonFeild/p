# CAIE O Level past papers (inverted)

Source: github.com/Upppllld/OpenPastPapers (mirror of Cambridge International past
papers), topped up from papacambridge for the May/June 2026 session and older holes.
Colours inverted for dark reading with tools_invert_pdfs.py; text stays selectable.

Verified in full: all 4,496 files open, all 47,063 pages render dark, 65.8 M
characters of text still extract. Every page carries the `/ArenaInvert` marker, so
re-running the inverter is a no-op.

| Folder | Files | Pages | Size |
| --- | ---: | ---: | ---: |
| `accounting-7707/` | 119 | 1457 | 51 MB |
| `bengali-3204/` | 135 | 890 | 66 MB |
| `biology-5090/` | 791 | 7982 | 421 MB |
| `chemistry-5070/` | 790 | 8581 | 375 MB |
| `computer-science-2210/` | 236 | 2479 | 157 MB |
| `economics-2281/` | 387 | 3424 | 120 MB |
| `english-language-1123/` | 465 | 4042 | 200 MB |
| `mathematics-additional-4037/` | 390 | 4489 | 229 MB |
| `mathematics-d-calculator-version-4024/` | 389 | 5171 | 259 MB |
| `physics-5054/` | 794 | 8548 | 404 MB |
| **total** | **4496** | **47063** | **2281 MB** |

File names follow the CAIE convention: `SERIES_YEAR_KIND_VARIANT.pdf`
(`s`=May/June, `w`=Oct/Nov, `m`=Feb/March; `qp`=question paper, `ms`=mark scheme,
`er`=examiner report, `in`=insert, `ci`=confidential instructions, `gt`=grade thresholds).

## Known gaps

See `MISSING.md` for the full breakdown. In short: 4,496 of the 4,545 files in the
papacambridge index are present. The 49-file difference is dead links (9), notice
files, and non-paper artefacts (`ci`/`gt`/`in`/`-solved` compilations) that the
fetcher skips by design. The w25 session was never published as PDFs by the mirror.

`4024` and `3204` are complete with no gap.

## Scanned papers

15 files are image-only scans with no text layer — that comes from the source, not
from the inversion. They have zero font objects in the original PDFs, so there is no
text to preserve:

| Folder | Files |
| --- | --- |
| `biology-5090/` (s19 qp_22, s20 qp_12, s21 qp_61) | 3 |
| `chemistry-5070/` (s20 qp_12, s21 qp_41) | 2 |
| `computer-science-2210/` (s18 qp_21, w20 qp_12) | 2 |
| `english-language-1123/` (s19 qp_21) | 1 |
| `mathematics-additional-4037/` (s21 qp_11, w20 qp_22) | 2 |
| `mathematics-d-calculator-version-4024/` (s20 qp_12, w19 qp_22) | 2 |
| `physics-5054/` (s20 qp_11, s21 qp_12, w19 qp_41) | 3 |

They render correctly and are fully readable, just not selectable.
