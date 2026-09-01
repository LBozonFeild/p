#!/usr/bin/env python3
"""Crop real 5090 QP/MS, strip excess, pack leftover space, invert."""
from __future__ import annotations

import io
import re
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

ROOT = Path("/home/user/p")
OUT = ROOT / "Ch7_Ch13_Question_Bank.pdf"
DPI = 130
HEADER, FOOTER = 54, 786
SANSB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# (code, qnum, start_at, stop_at)
P2 = [
    ("s11_22", 6, None, None),
    ("s11_22", 7, None, "kept alive"),
    ("s12_21", 6, None, None),
    ("s12_21", 7, None, "human gametes"),
    ("s12_22", 3, "(b) List three structural", None),
    ("s12_22", 9, None, None),
    ("s16_21", 1, None, None),
    ("s17_21", 2, None, None),
    ("s18_21", 6, None, None),
    ("s20_21", 3, None, None),
    ("s21_21", 1, None, None),
    ("s21_21", 7, None, None),
    ("s21_22", 3, None, None),
    ("s22_21", 3, None, None),
    ("s22_22", 5, None, None),
    ("s22_22", 9, None, "dialysis"),
    ("s24_22", 4, None, None),
    ("s24_22", 6, None, None),
    ("s25_22", 7, None, None),
    ("w11_21", 8, None, None),
    ("w12_21", 1, None, None),
    ("w12_21", 6, None, None),
    ("w12_22", 7, None, "dialysis"),
    ("w13_21", 6, None, None),
    ("w13_22", 7, None, "kidneys maintain"),
    ("w14_21", 2, None, None),
    ("w14_21", 7, None, None),
    ("w14_22", 1, None, None),
    ("w15_21", 5, None, None),
    ("w15_21", 9, None, "dialysis"),
    ("w15_22", 7, None, None),
    ("w17_21", 2, None, "dialysis"),
    ("w19_21", 8, None, None),
    ("w20_22", 7, None, "dialysis"),
    ("w21_21", 3, None, "dialysis"),
    ("w22_21", 1, None, None),
    ("w22_21", 6, None, None),
    ("w22_22", 8, None, None),
    ("w23_21", 7, None, None),
    ("w23_22", 3, None, None),
    ("w24_21", 1, None, None),
    ("w24_21", 4, None, None),
    ("w25_21", 3, None, None),
    ("w25_21", 4, "Mistletoe", None),
    ("w25_22", 2, "(b) A scientist", None),
]

P1_STRONG = re.compile(
    r"transpir|xylem|phloem|root hair|root-hair|translocat|\bwilt|"
    r"\burea\b|nephron|ureter|urethra|glomerul|deaminat|\bexcret|"
    r"Bowman|lignif|potometer",
    re.I,
)


def open_pdf(code: str, paper: int, what: str) -> pymupdf.Document:
    sess, var = code.split("_")
    name = f"5090_{sess}_{what}_{var}.pdf"
    for p in (ROOT / f"paper{paper}" / what / name, ROOT / name):
        if p.exists() and p.read_bytes()[:5] == b"%PDF-":
            try:
                return pymupdf.open(p)
            except Exception:
                continue
    raise FileNotFoundError(name)


def paper_code(code: str) -> str:
    sess, var = code.split("_")
    return f"5090/{var}/{'M/J' if sess[0]=='s' else 'O/N'}/{sess[1:]}"


def junk_page(page) -> bool:
    t = (page.get_text("text") or "").lower()
    if "blank page" in t and len(t) < 800:
        return True
    if "permission to reproduce" in t and len(t) < 1800:
        return True
    return False


def q_starts(doc):
    """True question numbers sit in the left margin (x ~ 50)."""
    raw = []
    for i, page in enumerate(doc):
        if junk_page(page):
            continue
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"]).strip()
                x0, y0, x1, y1 = l["bbox"]
                if x0 > 70:
                    continue
                m = re.match(r"^(\d{1,2})\s*$", t) or re.match(
                    r"^(\d{1,2})\s+(\(|[A-Z])", t
                )
                if not m:
                    continue
                q = int(m.group(1))
                if 1 <= q <= 40 and y0 >= HEADER and y0 <= FOOTER:
                    raw.append((q, i, y0))
    raw.sort(key=lambda t: (t[1], t[2]))
    seen, out = set(), []
    for s in raw:
        if s[0] in seen:
            continue
        seen.add(s[0])
        out.append(s)
    return out


def find_phrase(doc, phrase):
    if not phrase:
        return None
    for i, page in enumerate(doc):
        hits = page.search_for(phrase)
        if not hits:
            hits = page.search_for(phrase.title()) or page.search_for(phrase.lower())
        if hits:
            return i, hits[0].y0
    return None


def q_spans(doc, qnum, start_at=None, stop_at=None):
    starts = q_starts(doc)
    idx = next((i for i, s in enumerate(starts) if s[0] == qnum), None)
    if idx is None:
        return []
    p0, y0 = starts[idx][1], starts[idx][2]
    if idx + 1 < len(starts):
        p1, y1 = starts[idx + 1][1], starts[idx + 1][2] - 2
    else:
        p1 = next(
            (i for i in range(doc.page_count - 1, p0 - 1, -1) if not junk_page(doc[i])),
            p0,
        )
        y1 = FOOTER
    sa = find_phrase(doc, start_at)
    st = find_phrase(doc, stop_at)
    if sa:
        p0, y0 = sa
    if st:
        p1, y1 = st[0], st[1] - 2
    # cut copyright / next-section banners that sit after this question
    for phrase in ("Permission to reproduce", "Section B", "Section C"):
        for i, page in enumerate(doc):
            if i < p0 or i > p1:
                continue
            for h in page.search_for(phrase) or []:
                if i > p0 or h.y0 > y0 + 70:
                    if i < p1 or (i == p1 and h.y0 < y1):
                        p1, y1 = i, h.y0 - 2
    spans = []
    for pi in range(p0, p1 + 1):
        if junk_page(doc[pi]):
            continue
        h = doc[pi].rect.height
        top = y0 if pi == p0 else HEADER
        bot = y1 if pi == p1 else FOOTER
        top = max(8, min(top, h - 30))
        bot = max(top + 18, min(bot, h - 28))
        spans.append((pi, top, bot))
    return spans


def render_clip(page, y0, y1, x0=30, dpi=DPI) -> Image.Image:
    h, w = page.rect.height, page.rect.width
    clip = pymupdf.Rect(x0, max(0, y0), w - 12, min(h, y1))
    if clip.height < 8 or clip.width < 8:
        return None
    mat = pymupdf.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def trim_empty_bands(img: Image.Image, drop_min=14, keep_gap=4) -> Image.Image:
    g = img.convert("L")
    w, h = g.size
    px = g.tobytes()
    content = [False] * h
    for y in range(h):
        row = px[y * w : (y + 1) * w]
        dark = 0
        run = maxrun = 0
        for v in row:
            if v < 175:
                dark += 1
                run += 1
                if run > maxrun:
                    maxrun = run
            else:
                run = 0
        frac = dark / w
        if frac > 0.055 or (frac > 0.012 and maxrun >= 12):
            content[y] = True
    keep = [False] * h
    y = 0
    while y < h:
        if content[y]:
            keep[y] = True
            y += 1
            continue
        y0 = y
        while y < h and not content[y]:
            y += 1
        if (y - y0) <= drop_min:
            for i in range(y0, y):
                keep[i] = True
        else:
            for i in range(y0, min(y, y0 + keep_gap)):
                keep[i] = True
    rows = [i for i in range(h) if keep[i]]
    if len(rows) < 6:
        return img
    src, out = img.load(), Image.new("RGB", (w, len(rows)), (255, 255, 255))
    dst = out.load()
    for i, yy in enumerate(rows):
        for x in range(w):
            dst[x, i] = src[x, yy]
    g2, nh = out.convert("L"), out.size[1]
    gp = g2.load()

    def col_dark(x):
        return sum(1 for yy in range(nh) if gp[x, yy] < 175) / nh > 0.004

    left, right = 0, w - 1
    while left < right and not col_dark(left):
        left += 1
    while right > left and not col_dark(right):
        right -= 1
    pad = 6
    return out.crop((max(0, left - pad), 0, min(w, right + pad + 1), nh))


def vstack(imgs, gap=3):
    if not imgs:
        return None
    w = max(i.size[0] for i in imgs)
    h = sum(i.size[1] for i in imgs) + gap * (len(imgs) - 1)
    out = Image.new("RGB", (w, h), (255, 255, 255))
    y = 0
    for im in imgs:
        out.paste(im, (0, y))
        y += im.size[1] + gap
    return out


def crop_question(doc, qnum, start_at=None, stop_at=None):
    # Keep the QP's own line spacing — do not collapse dotted answer lines.
    parts = []
    for pi, y0, y1 in q_spans(doc, qnum, start_at, stop_at):
        im = render_clip(doc[pi], y0, y1)
        if im is not None and im.size[1] > 10:
            parts.append(im)
    return vstack(parts, gap=0)


def disp(page, rect):
    return rect * page.rotation_matrix


def ms_labels(page):
    """(qnum, y0_display, word) in the question column only."""
    labels = []
    pw = page.rect.width
    for w in page.get_text("words"):
        word = w[4].replace(" ", "")
        m = re.match(r"^(\d{1,2})(\([a-z]+\))?(\([ivx]+\))?$", word, re.I)
        if not m:
            continue
        r = disp(page, pymupdf.Rect(w[:4]))
        # part-labels 4(a)(i) sit further left than answer-point numbers 1,2,3
        limit = pw * (0.18 if "(" in word else 0.14)
        if r.x0 > limit:
            continue
        q = int(m.group(1))
        if 1 <= q <= 40:
            labels.append((q, r.y0, word))
    labels.sort(key=lambda t: t[1])
    return labels


def crop_ms_question(doc, qnum: int):
    parts = []
    # modern MS uses 4(a)(i); ignore lone '4' in the marks column
    has_paren = False
    for page in doc:
        for _, _, wd in ms_labels(page):
            if wd.startswith(f"{qnum}("):
                has_paren = True
                break
        if has_paren:
            break
    started = False
    for page in doc:
        labs = ms_labels(page)
        if has_paren:
            mine = [y for q, y, wd in labs if q == qnum and wd.startswith(f"{qnum}(")]
            nxt = [y for q, y, wd in labs if q > qnum and "(" in wd]
        else:
            mine = [y for q, y, _ in labs if q == qnum]
            nxt = [y for q, y, _ in labs if q > qnum]
        if not mine:
            hits = []
            for n in (f"{qnum}(a)", f"{qnum} (a)", f"{qnum}("):
                hits += page.search_for(n) or []
            mine = [disp(page, h).y0 for h in hits]
            if not mine:
                if started:
                    break
                continue
        started = True
        y0 = max(28, min(mine) - 10)
        later = [y for y in nxt if y > min(mine) + 8]
        y1 = min(later) - 3 if later else page.rect.height - 30
        if y1 <= y0 + 12:
            continue
        im = render_clip(page, y0, y1, x0=14, dpi=120)
        if im is not None and im.size[1] > 10:
            parts.append(im)
        if later:
            break
    return vstack(parts)


def crop_p1_ms(doc, qnums):
    """One block per MS page covering the selected question rows."""
    want = set(qnums)
    parts = []
    for page in doc:
        labs = ms_labels(page)
        ys = [y for q, y, _ in labs if q in want]
        if not ys:
            continue
        last = max(ys)
        after = [y for q, y, _ in labs if y > last + 3]
        y0 = max(36, min(ys) - 6)
        y1 = (min(after) - 2) if after else min(page.rect.height - 32, last + 28)
        im = render_clip(page, y0, y1, x0=30, dpi=120)
        if im is None:
            continue
        if im.size[1] > 8:
            parts.append(im)
    return vstack(parts)


def p1_hits(doc):
    starts = q_starts(doc)
    out = []
    for i, (q, p, y) in enumerate(starts):
        if i + 1 < len(starts) and starts[i + 1][1] == p:
            bot = starts[i + 1][2]
        else:
            bot = FOOTER
        t = doc[p].get_text("text", clip=pymupdf.Rect(0, y, doc[p].rect.width, bot)) or ""
        if (
            P1_STRONG.search(t)
            and "dialysis" not in t.lower()
            and not re.search(
                r"fetus|umbilical|sperm|pregnan|food chain|reproductive system",
                t,
                re.I,
            )
        ):
            out.append(q)
    return out


SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def scale_w(im, max_w):
    if im.size[0] <= max_w:
        return im
    nh = max(1, int(im.size[1] * max_w / im.size[0]))
    return im.resize((max_w, nh), Image.LANCZOS)


def label_strip(text, width):
    im = Image.new("RGB", (width, 14), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.text((2, 1), text, font=ImageFont.truetype(SANSB, 10), fill=(0, 0, 0))
    return im


def pack_units(units):
    """Plain packed crops. MS follows its question. New page only if it will not fit."""
    pw, ph = int(A4[0] * DPI / 72), int(A4[1] * DPI / 72)
    margin, gap = 10, 6
    max_w = pw - 2 * margin
    pages = []
    canvas = Image.new("RGB", (pw, ph), (255, 255, 255))
    y = margin

    def flush():
        nonlocal canvas, y
        pages.append(canvas)
        canvas = Image.new("RGB", (pw, ph), (255, 255, 255))
        y = margin

    def place(im):
        nonlocal y
        canvas.paste(im, (margin, y))
        y += im.size[1] + gap

    def need_place(im):
        nonlocal y
        if y > margin and y + im.size[1] > ph - margin:
            flush()
        if im.size[1] > ph - 2 * margin:
            sc = (ph - 2 * margin) / im.size[1]
            im = im.resize((max(1, int(im.size[0] * sc)), max(1, int(im.size[1] * sc))), Image.LANCZOS)
        place(im)

    for title, qim, msim in units:
        qim = scale_w(qim.convert("RGB"), max_w)
        qblock = Image.new("RGB", (max_w, 14 + qim.size[1]), (255, 255, 255))
        qblock.paste(label_strip(title, max_w), (0, 0))
        qblock.paste(qim, (0, 14))
        need_place(qblock)
        if msim is None:
            continue
        msim = scale_w(msim.convert("RGB"), max_w)
        msblock = Image.new("RGB", (max_w, 14 + msim.size[1]), (255, 255, 255))
        msblock.paste(label_strip("MS  " + title, max_w), (0, 0))
        msblock.paste(msim, (0, 14))
        need_place(msblock)
    pages.append(canvas)
    return pages


def to_pdf(pages):
    c = pdfcanvas.Canvas(str(OUT), pagesize=A4)
    aw, ah = A4
    for im in pages:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=80, optimize=True)
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=aw, height=ah)
        c.showPage()
    c.save()


def main():
    units = []

    for code, qnum, start_at, stop_at in P2:
        try:
            qp = open_pdf(code, 2, "qp")
        except FileNotFoundError as e:
            print("missing QP", e)
            continue
        qim = crop_question(qp, qnum, start_at, stop_at)
        qp.close()
        if qim is None:
            print("no QP", paper_code(code), qnum)
            continue
        msim = None
        try:
            ms = open_pdf(code, 2, "ms")
            msim = crop_ms_question(ms, qnum)
            ms.close()
        except FileNotFoundError as e:
            print("missing MS", e)
        lab = f"{paper_code(code)}   Q{qnum}"
        print("unit", lab, qim.size, None if msim is None else msim.size)
        units.append((lab, qim, msim))

    p1_selected = []
    for y in range(20, 26):
        for s in ("s", "w"):
            for v in ("11", "12"):
                code = f"{s}{y:02d}_{v}"
                try:
                    doc = open_pdf(code, 1, "qp")
                except FileNotFoundError:
                    continue
                for q in p1_hits(doc):
                    p1_selected.append((code, q))
                doc.close()

    ms_cache = {}
    for code, qnum in p1_selected:
        qp = open_pdf(code, 1, "qp")
        qim = crop_question(qp, qnum)
        qp.close()
        if qim is None:
            continue
        if code not in ms_cache:
            try:
                ms_cache[code] = open_pdf(code, 1, "ms")
            except FileNotFoundError:
                ms_cache[code] = None
        msim = None
        if ms_cache[code] is not None:
            msim = crop_ms_question(ms_cache[code], qnum)
        lab = f"{paper_code(code)}   Q{qnum}"
        print("P1 unit", lab, qim.size, None if msim is None else msim.size)
        units.append((lab, qim, msim))
    for doc in ms_cache.values():
        if doc is not None:
            doc.close()

    pages = pack_units(units)
    pages = [ImageOps.invert(p.convert("RGB")) for p in pages]
    to_pdf(pages)
    print("wrote", OUT, "pages", len(pages), "bytes", OUT.stat().st_size, "units", len(units))


if __name__ == "__main__":
    main()
