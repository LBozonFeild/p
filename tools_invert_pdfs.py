#!/usr/bin/env python3
"""Invert the colours of every page of every PDF (dark mode) without re-encoding
the embedded images or touching the text layer.

Per page, the existing content stream is wrapped in

    q
    <media box> re W n  1 1 1 rg  <media box> re f    # opaque white base
    ... original content ...
    /ArenaInv gs  1 1 1 rg  <media box> re f           # white rect, Difference
    Q

The final rect uses the /Difference blend mode, so it paints 1 - backdrop over
everything underneath it: vector text, rules and colour graphics as well as the
scanned raster images all invert, while text stays selectable and searchable.
Pages that already carry the /ArenaInvert marker are skipped, so the script can
safely be re-run (it will not double-invert).

  python3 invert_pdfs.py FILE...            # invert
  python3 invert_pdfs.py --restore FILE...  # undo the inversion
"""
import argparse
import re
import sys

import pikepdf


MARKER = '/ArenaInvert'
GS_NAME = 'ArenaInv'


def _norm(data: bytes) -> bytes:
    """Canonical form of a wrapper stream: line endings + ExtGState name."""
    data = data.replace(b"\r\n", b"\n")
    return _GS_RE.sub(b"/" + GS_NAME.encode(), data)


_GS_RE = re.compile(rb"/" + GS_NAME.encode() + rb"\d*")


def _box(page):
    mb = [float(v) for v in page.MediaBox]
    w, h = mb[2] - mb[0], mb[3] - mb[1]
    return f"{mb[0]:g} {mb[1]:g} {w:g} {h:g}".encode()


def _templates(page):
    """Content-stream wrappers.

    The original content is sandwiched in its own q/Q so that a leaked clipping
    path inside it cannot clip the inversion rectangle (which is what happens on
    a handful of CAMBRIDGE examiner reports). The % comment lines let a later
    --restore find the wrappers regardless of how they were built.
    """
    box = _box(page)
    prefix = (b"%ArenaInvertBase\nq\n" + box + b" re W n\n1 1 1 rg\n" + box + b" re f\nq\n")
    suffix = (b"\nQ\n%ArenaInvertInvert\n/" + GS_NAME.encode() + b" gs\n1 1 1 rg\n"
              + box + b" re f\nQ\n")
    return prefix, suffix


def _legacy_templates(page):
    """Templates produced by the first version of this tool (no q/Q isolation)."""
    box = _box(page)
    prefix = b"q\n" + box + b" re W n\n1 1 1 rg\n" + box + b" re f\n"
    suffix = b"\n/" + GS_NAME.encode() + b" gs\n1 1 1 rg\n" + box + b" re f\nQ\n"
    return prefix, suffix


def _streams(page):
    c = page.Contents
    if c is None:
        return []
    return list(c) if isinstance(c, pikepdf.Array) else [c]


def invert_page(pdf, page):
    if page.get(MARKER):
        return False

    prefix, suffix = _templates(page)

    resources = page.Resources
    extg = resources.get('/ExtGState')
    if extg is None:
        extg = pikepdf.Dictionary()
        resources.ExtGState = extg
    name = '/' + GS_NAME
    i = 0
    while pikepdf.Name(name) in extg:
        i += 1
        name = f'/{GS_NAME}{i}'
    extg[pikepdf.Name(name)] = pdf.make_indirect(
        pikepdf.Dictionary(Type=pikepdf.Name('/ExtGState'), BM=pikepdf.Name('/Difference'))
    )
    # the suffix stream refers to the state we just created
    suffix = suffix.replace(('/' + GS_NAME).encode(), name.encode(), 1)

    # force a DeviceRGB page group so CMYK blacks become white, not grey
    grp = page.get('/Group')
    if grp is None:
        page.Group = pdf.make_indirect(pikepdf.Dictionary(
            S=pikepdf.Name('/Transparency'), CS=pikepdf.Name('/DeviceRGB'), I=True, K=False))
    else:
        grp.CS = pikepdf.Name('/DeviceRGB')

    new = pikepdf.Array([pdf.make_stream(prefix)])
    new.extend(_streams(page))
    new.append(pdf.make_stream(suffix))
    page.Contents = pdf.make_indirect(new)
    page[MARKER] = True
    return True


def restore_page(pdf, page):
    """Remove the inversion wrapper added by invert_page()."""
    if not page.get(MARKER):
        return False

    lprefix, lsuffix = _legacy_templates(page)
    known = {_norm(lprefix), _norm(lsuffix)}
    kept = []
    for st in _streams(page):
        data = st.read_bytes()
        if b"%ArenaInvertBase" in data or b"%ArenaInvertInvert" in data:
            continue
        if _norm(data) in known:
            continue
        kept.append(st)

    if len(kept) == 1:
        page.Contents = pdf.make_indirect(kept[0])
    elif kept:
        page.Contents = pdf.make_indirect(pikepdf.Array(kept))

    extg = page.Resources.get('/ExtGState')
    if extg is not None:
        for n in [str(k) for k in extg.keys()]:
            if n.lstrip('/').startswith(GS_NAME):
                del extg[n]

    del page[MARKER]
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    op = restore_page if args.restore else invert_page
    total_files = total_pages = 0
    failures = []
    for path in args.paths:
        try:
            with pikepdf.open(path, allow_overwriting_input=True) as pdf:
                changed = sum(1 for pg in pdf.pages if op(pdf, pg))
                if changed:
                    pdf.save(path, object_stream_mode=pikepdf.ObjectStreamMode.generate)
        except Exception as exc:  # keep going, report at the end
            failures.append((path, exc))
            print(f"FAILED  {path}: {exc}", file=sys.stderr, flush=True)
            continue
        total_files += 1
        total_pages += changed
        if not args.quiet:
            print(f"{changed:4d} pages  {path}", flush=True)

    verb = "restored" if args.restore else "inverted"
    print(f"\nDONE: {total_files} files, {total_pages} pages {verb}, {len(failures)} failures", flush=True)


if __name__ == '__main__':
    main()
