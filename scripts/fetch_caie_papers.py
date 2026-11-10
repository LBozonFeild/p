#!/usr/bin/env python3
"""
Download CAIE (Cambridge International) O Level past papers, then invert them.

The sandbox this repo is developed in cannot reach cambridgeinternational.org,
so this script is meant to be run on your own machine. It does two things:

  1. downloads every paper / mark scheme / insert / examiner report linked from
     each subject's "past papers" page (the pages only carry the most recent
     session that Cambridge publishes publicly - their site states this is
     "only a selection of our papers"), and
  2. inverts the colours of every PDF it downloaded, using the same
     vector-preserving Difference-blend method already used in this repo
     (tools_invert_pdfs.py), so text stays selectable and searchable.

Usage
-----
    python3 scripts/fetch_caie_papers.py                 # download + invert
    python3 scripts/fetch_caie_papers.py --no-invert     # download only
    python3 scripts/fetch_caie_papers.py --subject 5090 5070
    python3 scripts/fetch_caie_papers.py --restore       # undo the inversion

Requirements
------------
    pip install requests beautifulsoup4 pikepdf

Layout
------
    papers/<code>_<slug>/<code>_<session>_<kind>_<variant>.pdf

e.g. papers/5090_biology/5090_s24_qp_11.pdf
     papers/5090_biology/5090_s24_ms_11.pdf
     papers/5090_biology/5090_s24_er.pdf
     papers/5090_biology/5090_s24_ci_31.pdf   (confidential instructions)
     papers/5090_biology/5090_spec23_qp_1.pdf  (specimen)

Files that already exist with a non-zero size are skipped, so re-running only
fetches what is missing.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    sys.exit("Missing dependencies. Run: pip install requests beautifulsoup4 pikepdf")

BASE = "https://www.cambridgeinternational.org"
PAST_PAPERS = "/programmes-and-qualifications/{slug}/past-papers/"

SUBJECTS = {
    "5090": ("cambridge-o-level-biology-5090", "biology"),
    "5070": ("cambridge-o-level-chemistry-5070", "chemistry"),
    "2210": ("cambridge-o-level-computer-science-2210", "computer_science"),
    "2281": ("cambridge-o-level-economics-2281", "economics"),
    "5054": ("cambridge-o-level-physics-5054", "physics"),
    "4037": ("cambridge-o-level-mathematics-additional-4037", "mathematics_additional"),
    "4024": ("cambridge-o-level-mathematics-d-4024", "mathematics_d"),
    "3204": ("cambridge-o-level-bengali-3204", "bengali"),
    "7707": ("cambridge-o-level-accounting-7707", "accounting"),
    "1123": ("cambridge-o-level-english-language-1123", "english_language"),
}

SESSION_CODES = {
    "june": "s", "may": "s", "may/june": "s",
    "october": "w", "november": "w", "october/november": "w",
    "march": "m",
}

# link text is like: "June 2024 Question Paper 11 (PDF, 579KB)"
LINK_RE = re.compile(
    r"(?P<session>January|March|May/June|June|October/November|November)\s+"
    r"(?P<year>\d{4})\s+"
    r"(?P<kind>[A-Za-z][A-Za-z ]*?)"
    r"(?:\s+(?P<variant>\d+[A-Z]?))?\s*\(PDF",
    re.I,
)
YEAR_FIRST_RE = re.compile(
    r"(?P<year>\d{4})\s+(?P<kind>[A-Za-z][A-Za-z ]*?)(?:\s+(?P<variant>\d+[A-Z]?))?\s*\(PDF",
    re.I,
)

KIND_CODES = [
    ("confidential instructions", "ci"),
    ("mark scheme", "ms"),
    ("question paper", "qp"),
    ("examiner report", "er"),
    ("insert", "in"),
    ("specimen mark scheme", "ms"),
    ("specimen paper", "qp"),
    ("mark scheme", "ms"),
]


# Folder names as they actually exist in papers/ (e.g. papers/biology-5090).
FOLDER_SLUGS = {
    "5090": "biology-5090",
    "5070": "chemistry-5070",
    "2210": "computer-science-2210",
    "2281": "economics-2281",
    "5054": "physics-5054",
    "4037": "mathematics-additional-4037",
    "4024": "mathematics-d-calculator-version-4024",
    "3204": "bengali-3204",
    "7707": "accounting-7707",
    "1123": "english-language-1123",
}


def folder_name(code: str) -> str:
    return FOLDER_SLUGS[code]


def kind_code(text: str) -> str:
    t = " ".join(text.lower().split())
    for needle, code in KIND_CODES:
        if needle in t:
            return code
    return re.sub(r"[^a-z]+", "_", t).strip("_")[:4] or "doc"


def parse_name(text: str):
    """Return (year, session, kind, variant) parsed from a link's text."""
    m = LINK_RE.search(text)
    if m:
        session = SESSION_CODES.get(m.group("session").lower().strip(), "x")
        return m.group("year"), session, kind_code(m.group("kind")), (m.group("variant") or "").strip()
    m = YEAR_FIRST_RE.search(text)
    if m:
        kind = kind_code(m.group("kind"))
        # "2023 Specimen Paper 1" -> specimen
        session = "spec" if "specimen" in text.lower() else "x"
        return m.group("year"), session, kind, (m.group("variant") or "").strip()
    return None, None, None, None


def collect_links(html: str, page_url: str):
    """Yield (url, link_text) for every PDF on a past-papers page."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/Images/" not in href and not href.lower().endswith(".pdf"):
            continue
        url = urljoin(page_url, href)
        if url in seen:
            continue
        seen.add(url)
        yield url, " ".join(a.get_text(" ", strip=True).split())


def fetch(session: requests.Session, url: str, dest: Path, retries: int = 3) -> str:
    if dest.exists() and dest.stat().st_size > 1024:
        return "skip"
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=60, headers={"User-Agent": session.headers["User-Agent"]})
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):
                return "not-a-pdf"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return "ok"
        except Exception as exc:  # noqa: BLE001
            if attempt == retries:
                print(f"    ! failed {dest.name}: {exc}")
                return "fail"
            time.sleep(1.5 * attempt)
    return "fail"



PAPA = "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/{name}.pdf"


def fetch_from_missing(manifest: Path, out_root: Path, session=requests.Session()) -> list[Path]:
    """Download the exact files named in papers/MISSING.md, then invert them.

    The manifest lists bare names such as 5090_s26_qp_11; the subject folder is
    derived from the syllabus code, so the layout matches the rest of papers/.
    """
    import re as _re
    text = manifest.read_text()
    found = _re.findall(r"`([0-9]{4}_[smw][0-9]{2}_[A-Za-z0-9_\-]+)`", text)
    want = sorted(set(found))
    print(f"{len(want)} files listed in {manifest}")

    folder_for = {code: folder_name(code) for code in SUBJECTS}
    got: list[Path] = []
    for name in want:
        code = name.split("_")[0]
        dest_dir = out_root / folder_for[code]
        dest = dest_dir / f"{name}.pdf"
        if dest.exists() and dest.stat().st_size > 1024:
            continue
        url = PAPA.format(name=name)
        status = fetch(session, url, dest)
        if status == "ok":
            got.append(dest)
            print(f"  + {dest_dir.name}/{name}.pdf", flush=True)
        elif status != "skip":
            print(f"  ? {name}: {status}", flush=True)
        time.sleep(0.3)
    return got


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", nargs="*", default=sorted(SUBJECTS),
                    help="syllabus codes to fetch (default: all ten)")
    ap.add_argument("--out", default="papers", help="output directory")
    ap.add_argument("--no-invert", action="store_true", help="download only")
    ap.add_argument("--restore", action="store_true", help="undo the colour inversion")
    ap.add_argument("--delay", type=float, default=0.4, help="seconds between requests")
    ap.add_argument("--from-missing", metavar="FILE",
                    help="download exactly the files named in papers/MISSING.md")
    args = ap.parse_args()

    out_root = Path(args.out)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "en-GB,en;q=0.9",
    })

    downloaded: list[Path] = []
    report: list[tuple[str, int, int]] = []

    if args.from_missing:
        downloaded = fetch_from_missing(Path(args.from_missing), out_root, session)
        print(f"\n{len(downloaded)} files downloaded from the manifest")
        if args.no_invert or not downloaded:
            return 0
        args.subject = []            # skip the subject-page crawl below

    for code in args.subject:
        if code not in SUBJECTS:
            print(f"!! unknown subject {code}, known: {', '.join(sorted(SUBJECTS))}")
            continue
        slug, name = SUBJECTS[code]
        page_url = BASE + PAST_PAPERS.format(slug=slug)
        subject_dir = out_root / f"{code}_{name}"
        print(f"\n=== {code} {name} ===")

        try:
            r = session.get(page_url, timeout=60)
            r.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            print(f"  ! could not load {page_url}: {exc}")
            continue

        links = list(collect_links(r.text, page_url))
        print(f"  {len(links)} PDF links found")

        count = 0
        for url, text in links:
            year, sess, kind, variant = parse_name(text)
            if year is None:
                stem = re.sub(r"[^A-Za-z0-9._-]+", "_", url.rsplit("/", 1)[-1])[:60]
                name_out = stem if stem.lower().endswith(".pdf") else stem + ".pdf"
            else:
                yy = year[-2:]
                parts = [code, f"{sess}{yy}" if sess not in ("x",) else yy, kind or "doc"]
                if variant:
                    parts.append(variant)
                name_out = "_".join(parts) + ".pdf"

            dest = subject_dir / name_out
            status = fetch(session, url, dest)
            if status == "ok":
                count += 1
                downloaded.append(dest)
                print(f"  + {name_out}  ({text[:52]})")
            elif status in ("not-a-pdf", "fail"):
                print(f"  ? {name_out}: {status} <{url}>")
            time.sleep(args.delay)

        size = sum(p.stat().st_size for p in subject_dir.glob("*.pdf")) if subject_dir.exists() else 0
        files = len(list(subject_dir.glob("*.pdf"))) if subject_dir.exists() else 0
        report.append((f"{code} {name}", files, size))
        print(f"  -> {count} new, {files} total, {size/1_048_576:.1f} MB")

    print("\n=== summary ===")
    for label, files, size in report:
        print(f"  {label:<28} {files:>4} files  {size/1_048_576:>7.1f} MB")

    if args.no_invert or not downloaded:
        return 0

    # ---- invert ----
    repo = Path(__file__).resolve().parent.parent
    script = next((c for c in (repo / "tools_invert_pdfs.py", repo / "scripts" / "invert_pdfs.py",
                               Path(__file__).with_name("invert_pdfs.py")) if c.exists()), None)
    if script is None:
        print("\n! inverter not found; expected tools_invert_pdfs.py at the repo root")
        return 0

    try:
        import pikepdf  # noqa: F401
    except ImportError:
        sys.exit("\npikepdf is required for inversion: pip install pikepdf")

    import importlib.util
    spec = importlib.util.spec_from_file_location("inverter", script)
    inverter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inverter)

    op = inverter.restore_page if args.restore else inverter.invert_page
    verb = "restored" if args.restore else "inverted"
    print(f"\n=== {verb} {len(downloaded)} PDFs ===")
    done = pages = 0
    for path in downloaded:
        try:
            with pikepdf.open(str(path), allow_overwriting_input=True) as pdf:
                changed = sum(1 for pg in pdf.pages if op(pdf, pg))
                if changed:
                    pdf.save(str(path), object_stream_mode=pikepdf.ObjectStreamMode.generate)
            done += 1
            pages += changed
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {path.name}: {exc}")
    print(f"  {done} files, {pages} pages {verb}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
