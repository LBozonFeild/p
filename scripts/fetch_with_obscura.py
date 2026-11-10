#!/usr/bin/env python3
"""
Fetch the missing CAIE papers through Obscura, then invert them.

Why Obscura: papacambridge sits behind Cloudflare, which can challenge plain
`curl`-style clients. Obscura is a real headless browser engine (V8 + CDP) with
its own TLS stack, JS execution and `--stealth` fingerprinting, so it looks like
a browser to Cloudflare, and it can be pointed at a proxy with `--proxy` if your
network needs one.

The binary is not on PyPI/npm, so this script looks for it in three places:

  1. `obscura` on PATH
  2. $OBSCURA_BIN
  3. ./bin/obscura next to this repository

Get a binary from https://github.com/h4ckf0r0day/obscura/releases:

    # Linux x86_64
    curl -LO https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-x86_64-linux.tar.gz
    tar xzf obscura-x86_64-linux.tar.gz && mkdir -p bin && mv obscura obscura-worker bin/

Usage
-----
    # fetch the 116 May/June 2026 papers listed in papers/MISSING.md, then invert
    python3 scripts/fetch_with_obscura.py --session s26

    # everything still missing (426 files)
    python3 scripts/fetch_with_obscura.py --all

    # go through a proxy (Obscura accepts http:// or socks5://)
    python3 scripts/fetch_with_obscura.py --session s26 --proxy socks5://127.0.0.1:1080

    # be gentler / faster
    python3 scripts/fetch_with_obscura.py --session s26 --concurrency 4 --wait 2

    # just print what would be fetched
    python3 scripts/fetch_with_obscura.py --session s26 --dry-run

It reads the file names out of papers/MISSING.md, so the target list always
matches the gap report rather than being hard-coded again.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MISSING_MD = REPO / "papers" / "MISSING.md"
UPLOAD = "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/{name}.pdf"

FOLDERS = {
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

NAME_RE = re.compile(r"`([0-9]{4}_[smw][0-9]{2}_[A-Za-z0-9_\-]+)`")


def find_obscura() -> str | None:
    for cand in (os.environ.get("OBSCURA_BIN"), shutil.which("obscura"), str(REPO / "bin" / "obscura")):
        if cand and Path(cand).is_file() and os.access(cand, os.X_OK):
            return cand
    return None


def names_from_manifest(path: Path, session: str | None, everything: bool) -> list[str]:
    text = path.read_text()
    names = sorted(set(NAME_RE.findall(text)))
    if everything:
        return names
    if session:
        keep = [n for n in names if f"_{session}_" in n]
        return keep
    return [n for n in names if "_s26_" in n]


def already_have(name: str) -> bool:
    code = name.split("_")[0]
    dest = REPO / "papers" / FOLDERS[code] / f"{name}.pdf"
    return dest.exists() and dest.stat().st_size > 1024


def obscura_fetch(binary: str, url: str, dest: Path, args) -> str:
    """Fetch one URL through Obscura's JS engine and write the bytes out."""
    # Read the file as base64 so binary PDFs survive both `--dump` modes.
    js = (
        "fetch(location.href).then(r=>r.arrayBuffer())"
        ".then(b=>{let s='',u=new Uint8Array(b),C=0x8000;"
        "for(let i=0;i<u.length;i+=C){s+=String.fromCharCode.apply(null,u.subarray(i,i+C));}"
        "return btoa(s);})"
    )
    cmd = [binary, "fetch", url, "--eval", js, "--timeout", str(args.timeout), "--quiet"]
    if args.stealth:
        cmd.append("--stealth")
    if args.proxy:
        cmd += ["--proxy", args.proxy]
    if args.user_agent:
        cmd += ["--user-agent", args.user_agent]
    if args.wait:
        cmd += ["--wait", str(args.wait)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout + 60)
    except subprocess.TimeoutExpired:
        return "timeout"

    out = (proc.stdout or "").strip()
    if proc.returncode != 0 or not out:
        err = (proc.stderr or "").strip().splitlines()
        print(f"    ! obscura failed rc={proc.returncode} {err[-1][:100] if err else ''}")
        return "fail"

    # The eval result is JSON (a quoted string) unless --quiet printed raw base64.
    payload = out
    if payload.startswith('"') and payload.endswith('"'):
        payload = payload[1:-1]

    import base64
    import json

    try:
        data = base64.b64decode(payload, validate=True)
    except Exception:
        try:  # maybe it was JSON-escaped
            data = base64.b64decode(json.loads(out), validate=True)
        except Exception:
            return "not-base64"

    if not data.startswith(b"%PDF"):
        # Cloudflare interstitial or an error page came back instead of the file
        return "not-a-pdf"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default=None, help="session token, e.g. s26 (default: s26)")
    ap.add_argument("--all", action="store_true", help="fetch every name in MISSING.md")
    ap.add_argument("--manifest", default=str(MISSING_MD))
    ap.add_argument("--concurrency", type=int, default=1,
                    help="sequential by default; Obscura scrape can do more but binary PDFs "
                         "are easier to verify one at a time")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--wait", type=float, default=0)
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--stealth", action="store_true", default=True)
    ap.add_argument("--no-stealth", dest="stealth", action="store_false")
    ap.add_argument("--user-agent", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-invert", action="store_true")
    args = ap.parse_args()

    manifest = Path(args.manifest)
    if not manifest.exists():
        sys.exit(f"manifest not found: {manifest}")

    names = names_from_manifest(manifest, args.session or "s26", args.all)
    todo = [n for n in names if not already_have(n)]
    print(f"{len(names)} names selected, {len(todo)} still needed")

    if args.dry_run:
        for n in todo[:20]:
            print(f"  would fetch {FOLDERS[n.split('_')[0]]}/{n}.pdf")
        if len(todo) > 20:
            print(f"  ... and {len(todo)-20} more")
        return 0

    binary = find_obscura()
    if not binary:
        sys.exit(
            "obscura binary not found.\n"
            "  Put it at ./bin/obscura (plus obscura-worker) or set OBSCURA_BIN.\n"
            "  Download: https://github.com/h4ckf0r0day/obscura/releases/latest"
        )
    print(f"using {binary}")
    ver = subprocess.run([binary, "--version"], capture_output=True, text=True).stdout.strip()
    print(f"  {ver}")

    got: list[Path] = []
    stats: dict[str, int] = {}
    t0 = time.time()
    for i, name in enumerate(todo, 1):
        code = name.split("_")[0]
        dest = REPO / "papers" / FOLDERS[code] / f"{name}.pdf"
        url = UPLOAD.format(name=name)
        status = obscura_fetch(binary, url, dest, args)
        stats[status] = stats.get(status, 0) + 1
        if status == "ok":
            got.append(dest)
            print(f"[{i}/{len(todo)}] + {FOLDERS[code]}/{name}.pdf", flush=True)
        else:
            print(f"[{i}/{len(todo)}] x {name}: {status}", flush=True)

    print(f"\n{len(got)} downloaded, {len(todo)-len(got)} failed in {time.time()-t0:.0f}s")
    print("  " + ", ".join(f"{k}={v}" for k, v in sorted(stats.items())))

    if args.no_invert or not got:
        return 0

    # reuse the verified inverter
    sys.path.insert(0, str(REPO))
    import importlib.util
    spec = importlib.util.spec_from_file_location("inv", REPO / "tools_invert_pdfs.py")
    inv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inv)
    import pikepdf

    pages = 0
    for path in got:
        try:
            with pikepdf.open(str(path), allow_overwriting_input=True) as pdf:
                n = sum(1 for pg in pdf.pages if inv.invert_page(pdf, pg))
                if n:
                    pdf.save(str(path), object_stream_mode=pikepdf.ObjectStreamMode.generate)
                pages += n
        except Exception as exc:
            print(f"  ! invert {path.name}: {exc}")
    print(f"inverted {pages} pages across {len(got)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
