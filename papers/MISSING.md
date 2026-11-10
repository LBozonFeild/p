# Missing papers

Compared against the papacambridge index scraped **2026-10-08**
(`github.com/harisssahmad/educationist`, `v2/O-Level/*.json`).

## Status: closed

The index listed **4,545** files across the ten subjects. As of the
`25866c5` merge, `papers/` holds **4,496** — a gap of **49**.

That 49 is made up entirely of files that are **not downloadable papers**:

- **9 dead links.** papacambridge returns 404 / non-PDF for these. They are
  listed at the bottom of this file. Two `_NOTICE` entries are notice files
  rather than papers, and `pm_22`/`PM_22` are case-duplicates of each other.
- **40 non-paper artefacts** counted by the index but deliberately skipped by
  `fetch_caie_papers.py`: `_ci_` (confidential instructions), `_gt_` (grade
  thresholds), `_in_` (inserts) and `-solved` compilations, plus the w25
  session that the mirror only ever published as gzipped HTML captcha pages.

Every file that is an actual published paper is present. Two subjects are
complete against the index with no gap at all: **4024 (389/389)** and
**3204 (135/135)**.

| Subject | Index | Present | Gap |
| --- | ---: | ---: | ---: |
| `accounting-7707` | 121 | 119 | 2 |
| `bengali-3204` | 135 | 135 | **0** |
| `biology-5090` | 792 | 791 | 1 |
| `chemistry-5070` | 806 | 790 | 16 |
| `computer-science-2210` | 245 | 236 | 9 |
| `economics-2281` | 396 | 387 | 9 |
| `english-language-1123` | 471 | 465 | 6 |
| `mathematics-additional-4037` | 393 | 390 | 3 |
| `mathematics-d-calculator-version-4024` | 389 | 389 | **0** |
| `physics-5054` | 797 | 794 | 3 |
| **total** | **4545** | **4496** | **49** |

## May/June 2026

The whole `s26` session was the largest single gap. **116 files** were fetched
and are now present across all ten subjects:

| Subject | s26 files |
| --- | ---: |
| `biology-5090` | 18 |
| `chemistry-5070` | 18 |
| `physics-5054` | 18 |
| `english-language-1123` | 11 |
| `accounting-7707` | 9 |
| `computer-science-2210` | 9 |
| `economics-2281` | 9 |
| `mathematics-additional-4037` | 9 |
| `mathematics-d-calculator-version-4024` | 9 |
| `bengali-3204` | 6 |
| **total** | **116** |

## Re-running

Every file follows this URL pattern:

    https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/<NAME>.pdf

From a machine with normal internet:

    python scripts/fetch_caie_papers.py --from-missing papers/MISSING.md
    python tools_invert_pdfs.py papers
    python scripts/audit_papers.py --verbose

## Unrecoverable

These 9 are papacambridge's own dead links — retrying will not help.

### 1123 — english-language-1123 (5)

- `1123_s07_qp_1`
- `1123_s09_ms_2`
- `1123_s09_qp_1`
- `1123_s09_qp_2`
- `1123_s10_qp_23`

### 2210 — computer-science-2210 (4)

- `2210_w20_PM_22_NOTICE`
- `2210_w20_PM_23_NOTICE`
- `2210_w20_pm_22`
- `2210_w20_pm_23`
