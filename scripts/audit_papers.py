#!/usr/bin/env python3
"""
Audit papers/ : what is there, what is inverted, and what is still missing.

Run this after any download so you know the real state of the collection rather
than trusting a download log.

    python3 scripts/audit_papers.py               # summary table
    python3 scripts/audit_papers.py --verbose     # per-subject detail
    python3 scripts/audit_papers.py --rewrite-missing
                                                  # regenerate papers/MISSING.md
                                                  # from what is actually on disk

It checks three things:
  1. every *.pdf really starts with %PDF (no saved Cloudflare pages)
  2. every page carries the inversion marker, and opens cleanly
  3. which names from papers/MISSING.md are still absent
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

try:
    import pikepdf
except ImportError:
    sys.exit("pip install pikepdf")

REPO = Path(__file__).resolve().parent.parent
PAPERS = REPO / "papers"
MANIFEST = PAPERS / "MISSING.md"
NAME_RE = re.compile(r"`([0-9]{4}_[smw][0-9]{2}_[A-Za-z0-9_\-]+)`")


def subject_dirs() -> list[Path]:
    return sorted(p for p in PAPERS.iterdir() if p.is_dir())


def audit() -> dict:
    info = {}
    for d in subject_dirs():
        files = sorted(d.glob("*.pdf"))
        bad_header, not_inverted, unreadable, pages = [], [], [], 0
        for f in files:
            with open(f, "rb") as fh:
                if fh.read(4) != b"%PDF":
                    bad_header.append(f.name)
                    continue
            try:
                with pikepdf.open(str(f)) as pdf:
                    pages += len(pdf.pages)
                    if any(not pg.get("/ArenaInvert") for pg in pdf.pages):
                        not_inverted.append(f.name)
            except Exception:
                unreadable.append(f.name)
        info[d.name] = dict(files=len(files), pages=pages, bad_header=bad_header,
                            not_inverted=not_inverted, unreadable=unreadable)
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--rewrite-missing", action="store_true")
    args = ap.parse_args()

    info = audit()
    have = {n for d in info for n in
            {f[:-4] for f in [p.name for p in (PAPERS / d).glob("*.pdf")]}}

    total_f = sum(v["files"] for v in info.values())
    total_p = sum(v["pages"] for v in info.values())
    print(f"{'folder':<42}{'files':>7}{'pages':>9}{'problems':>10}")
    for name, v in info.items():
        problems = len(v["bad_header"]) + len(v["not_inverted"]) + len(v["unreadable"])
        print(f"{name:<42}{v['files']:>7}{v['pages']:>9}{problems:>10}")
        if args.verbose and problems:
            for label, key in (("not a PDF", "bad_header"), ("not inverted", "not_inverted"),
                               ("unreadable", "unreadable")):
                if v[key]:
                    print(f"    {label}: {', '.join(v[key][:8])}"
                          + (f" (+{len(v[key])-8} more)" if len(v[key]) > 8 else ""))
    print(f"{'TOTAL':<42}{total_f:>7}{total_p:>9}")

    missing: list[str] = []
    if MANIFEST.exists():
        listed = sorted(set(NAME_RE.findall(MANIFEST.read_text())))
        missing = [n for n in listed if n not in have]
        print(f"\nmissing per papers/MISSING.md: {len(missing)} of {len(listed)} listed")
        if missing:
            by = collections.Counter(n.split("_")[0] for n in missing)
            print("  by subject:", dict(sorted(by.items())))
            if args.verbose:
                for n in missing:
                    print("   ", n)

        if args.rewrite_missing and missing:
            text = MANIFEST.read_text()
            body_start = text.index("## ")
            header = text[:body_start]
            # group the still-missing names by subject dir
            dir_for = {}
            for d in info:
                code = d.split("-")[-1] if d.split("-")[-1].isdigit() else d[:4]
                dir_for[code] = d
            out = [header.rstrip(), ""]
            by_sub = collections.defaultdict(list)
            for n in missing:
                by_sub[n.split("_")[0]].append(n)
            for code in sorted(by_sub):
                out.append(f"## {code} — {dir_for.get(code, code)}  ({len(by_sub[code])} missing)")
                out.append("")
                out.extend(f"- `{n}`" for n in sorted(by_sub[code]))
                out.append("")
            MANIFEST.write_text("\n".join(out))
            print(f"\nrewrote {MANIFEST} with {len(missing)} names")

    return 0


if __name__ == "__main__":
    sys.exit(main())
