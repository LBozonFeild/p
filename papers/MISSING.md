# Missing papers

Compared against the papacambridge index scraped **2026-10-08**
(`github.com/harisssahmad/educationist`, `v2/O-Level/*.json`).

**426 files missing** â€” 116 are the whole May/June 2026 session, 310 are older holes.

Every file is at this URL pattern:

    https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/<NAME>.pdf

Fetch and invert all of them in one command, from a machine with normal internet:

    python3 scripts/fetch_caie_papers.py --from-missing papers/MISSING.md

## 1123 — english-language-1123  (5 missing)

- `1123_s07_qp_1`
- `1123_s09_ms_2`
- `1123_s09_qp_1`
- `1123_s09_qp_2`
- `1123_s10_qp_23`

## 2210 — computer-science-2210  (4 missing)

- `2210_w20_PM_22_NOTICE`
- `2210_w20_PM_23_NOTICE`
- `2210_w20_pm_22`
- `2210_w20_pm_23`
