#!/usr/bin/env python3
"""Crop 2015–2025 P2 + P3-written ion/gas questions with MS, invert, make PDF."""
from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageOps, ImageDraw, ImageFont
import io

ROOT = Path("/home/user/p")
OUT = ROOT / "notes" / "ion-gas-identification-qp-ms-inverted.pdf"
DPI_M = fitz.Matrix(2.2, 2.2)
A4 = (1190, 1684)  # ~2x 595x842
MARGIN = 36
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (180, 180, 180)

try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    FONT_SM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    FONT_TINY = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
except OSError:
    FONT = FONT_SM = FONT_TINY = ImageFont.load_default()


def norm(s):
    return " ".join(s.replace("\u2009", " ").replace("\u00a0", " ").split()).lower()


def text_lines(page):
    """Group PDF words into lines using tight word boxes (works on MS tables)."""
    words = page.get_text("words")  # x0, y0, x1, y1, word, block, line, wordno
    groups = {}
    for w in words:
        key = (w[5], w[6])
        groups.setdefault(key, []).append(w)
    out = []
    for ws in groups.values():
        ws.sort(key=lambda w: w[0])
        t = " ".join(w[4] for w in ws)
        if not t.strip():
            continue
        y0 = min(w[1] for w in ws)
        y1 = max(w[3] for w in ws)
        out.append((y0, y1, t))
    out.sort(key=lambda r: (round(r[0], 1), r[1]))
    return out


def find_y_range(page, start, end, start_i=0, end_i=0):
    lines = text_lines(page)
    ns, ne = norm(start), norm(end) if end else ""
    starts = []
    for i, (y0, y1, t) in enumerate(lines):
        if ns in norm(t):
            starts.append(i)
    # phrase may be split across neighbouring lines
    if not starts:
        joined = [(i, norm(lines[i][2] + " " + (lines[i + 1][2] if i + 1 < len(lines) else ""))) for i in range(len(lines))]
        starts = [i for i, t in joined if ns in t]
    if not starts:
        raise ValueError(f"start not found: {start!r}")
    si = starts[min(start_i, len(starts) - 1)]
    y0 = lines[si][0]
    y1 = lines[si][1]
    if end:
        ends = []
        for j in range(si + 1, len(lines)):
            if ne in norm(lines[j][2]):
                ends.append(j)
        if not ends:
            # take a window of ~10 lines
            last = min(len(lines) - 1, si + 12)
            y1 = lines[last][1]
        else:
            ei = ends[min(end_i, len(ends) - 1)]
            y1 = lines[ei][1]
    else:
        last = min(len(lines) - 1, si + 10)
        y1 = lines[last][1]
    return y0, y1


def crop_page(path, page_1, start, end, start_i=0, end_i=0, pad_top=10, pad_bot=12, xpad=8):
    doc = fitz.open(path)
    page = doc[page_1 - 1]
    try:
        y0, y1 = find_y_range(page, start, end, start_i, end_i)
    except ValueError as e:
        doc.close()
        raise ValueError(f"{Path(path).name} p{page_1}: {e}") from e
    y0 = max(16, y0 - pad_top)
    y1 = min(page.rect.height - 16, y1 + pad_bot)
    if y1 - y0 < 16:
        y1 = y0 + 28
    clip = fitz.Rect(28 + xpad, y0, page.rect.width - 28, y1)
    pix = page.get_pixmap(matrix=DPI_M, clip=clip, colorspace=fitz.csRGB, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    if img.height < 4:
        raise ValueError(f"{Path(path).name} p{page_1}: empty crop for {start!r}")
    return ImageOps.invert(img)


def fit_width(img, max_w, max_h=None):
    w, h = img.size
    if w < 1 or h < 1:
        return img
    scale = max_w / w
    if max_h and max_h > 0:
        scale = min(scale, max_h / h)
    if scale >= 1:
        return img
    nw, nh = int(w * scale), int(h * scale)
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def new_page():
    return Image.new("RGB", A4, BLACK)


def draw_header(im, title, subtitle):
    d = ImageDraw.Draw(im)
    d.text((MARGIN, 28), title, font=FONT, fill=WHITE)
    d.text((MARGIN, 64), subtitle, font=FONT_SM, fill=GREY)
    d.line((MARGIN, 96, A4[0] - MARGIN, 96), fill=(80, 80, 80), width=2)
    return 110


def paste(im, piece, y, label=None):
    d = ImageDraw.Draw(im)
    max_w = A4[0] - 2 * MARGIN
    remain = A4[1] - y - 40
    if label:
        d.text((MARGIN, y), label, font=FONT_TINY, fill=GREY)
        y += 24
        remain -= 24
    piece = fit_width(piece, max_w, max(80, remain))
    # slight border
    im.paste(piece, (MARGIN, y))
    return y + piece.size[1] + 16, piece.size[1] > remain - 10


ITEMS = [
    # One Paper 2 question per test type (no repeats).
    dict(
        paper="Paper 2",
        ref="5070/21 O/N/19  Q2(e)(iii)",
        topic="Chloride ions  Cl⁻",
        qp=(ROOT / "paper2/qp/5070_w19_qp_21_(1).pdf", 4, "(iii)  Describe a test for chloride ions.", "[Total: 13]"),
        ms=(ROOT / "paper2/ms/5070_w19_ms_21.pdf", 5, "2(e)(iii)", "Question"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 O/N/23  Q4(c)",
        topic="Bromide ions  Br⁻",
        qp=(ROOT / "paper2/qp/5070_w23_qp_21_(1).pdf", 8, "Describe a test for aqueous bromide ions.", "test"),
        ms=(ROOT / "paper2/ms/5070_w23_ms_21.pdf", 7, "4(c)", "4(d)(i)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/22 M/J/19  Q7(c)",
        topic="Iodide ions  I⁻",
        qp=(ROOT / "paper2/qp/5070_s19_qp_22_(1).pdf", 10, "Describe a chemical test for the iodide ion.", "observation"),
        ms=(ROOT / "paper2/ms/5070_s19_ms_22.pdf", 10, "7(c)", "7(d)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/22 O/N/17  Q B8(b)",
        topic="Sulfate ions  SO₄²⁻",
        qp=(ROOT / "paper2/qp/5070_w17_qp_22.pdf", 16, "Describe a test for sulfate ions.", "test"),
        ms=(ROOT / "paper2/ms/5070_w17_ms_22.pdf", 6, "B8(b)", "B8(c)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 M/J/25  Q1(c)",
        topic="Nitrate ions  NO₃⁻",
        qp=(ROOT / "paper2/qp/5070_s25_qp_21_(1).pdf", 2, "reacts with warm aqueous sodium hydroxide and aluminium foil", "damp red litmus paper blue"),
        ms=(ROOT / "paper2/ms/5070_s25_ms_21.pdf", 7, "1(c)", "1(d)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 M/J/19  Q7(c)",
        topic="Ammonium ions  NH₄⁺  /  ammonia gas",
        qp=(ROOT / "paper2/qp/5070_s19_qp_21_(1).pdf", 10, "Describe a chemical test for the ammonium ion.", "[2]"),
        ms=(ROOT / "paper2/ms/5070_s19_ms_21.pdf", 8, "7(c)", "7(d)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 O/N/25  Q3(b)",
        topic="Carbon dioxide  CO₂",
        qp=(ROOT / "paper2/qp/5070_w25_qp_21.pdf", 4, "Describe a chemical test for carbon dioxide.", "test"),
        ms=(ROOT / "paper2/ms/5070_w25_ms_21.pdf", 7, "3(b)", "3(c)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 M/J/16  Q B10(c)(ii)",
        topic="Sulfur dioxide  SO₂",
        qp=(ROOT / "paper2/qp/5070_s16_qp_21.pdf", 19, "Describe the chemical test for sulfur dioxide.", "test"),
        ms=(ROOT / "paper2/ms/5070_s16_ms_21.pdf", 7, "B10(c)(ii)", "Total:"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 M/J/18  Q2(c)",
        topic="Chlorine gas  Cl₂",
        qp=(ROOT / "paper2/qp/5070_s18_qp_21_(1).pdf", 4, "Describe the chemical test for chlorine gas.", "test"),
        ms=(ROOT / "paper2/ms/5070_s18_ms_21.pdf", 4, "2(c)", "2(d)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/22 O/N/25  Q3(b)",
        topic="Hydrogen  H₂",
        qp=(ROOT / "paper2/qp/5070_w25_qp_22.pdf", 4, "Describe a chemical test for hydrogen.", "test"),
        ms=(ROOT / "paper2/ms/5070_w25_ms_22.pdf", 8, "3(b)", "3(c)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 O/N/21  Q2(d)",
        topic="Oxygen  O₂",
        qp=(ROOT / "paper2/qp/5070_w21_qp_21_(1).pdf", 3, "Describe the test for oxygen.", "test"),
        ms=(ROOT / "paper2/ms/5070_w21_ms_21.pdf", 5, "2(d)", "2(e)(i)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 O/N/22  Q5(d)",
        topic="Fe²⁺ / Fe³⁺",
        qp=(ROOT / "paper2/qp/5070_w22_qp_21_(1).pdf", 8, "Describe a chemical test to distinguish between aqueous iron(II) ions and aqueous iron(III) ions.", "test"),
        ms=(ROOT / "paper2/ms/5070_w22_ms_21.pdf", 8, "iron(II) ions give green precipitate", "iron(III) ions give red-brown precipitate"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 O/N/20  Q3(b)",
        topic="Copper(II) ions  Cu²⁺",
        qp=(ROOT / "paper2/qp/5070_w20_qp_21.pdf", 5, "Describe a test for copper(II) ions.", "test"),
        ms=(ROOT / "paper2/ms/5070_w20_ms_21.pdf", 6, "dark blue solution formed in excess ammonia", "3(c)(i)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/22 O/N/25  Q9(b)",
        topic="Zinc ions  Zn²⁺",
        qp=(ROOT / "paper2/qp/5070_w25_qp_22.pdf", 14, "Aqueous ammonia is added dropwise until in excess to a small volume of aqueous zinc chloride.", "Describe the observations during this addition."),
        ms=(ROOT / "paper2/ms/5070_w25_ms_22.pdf", 12, "9(b)", "9(c)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/22 M/J/22  Q6(b)",
        topic="Aluminium ions  Al³⁺",
        qp=(ROOT / "paper2/qp/5070_s22_qp_22_(1).pdf", 9, "Describe a chemical test for aluminium ions.", "[2]"),
        ms=(ROOT / "paper2/ms/5070_s22_ms_22.pdf", 9, "6(b)", "6(c)"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 M/J/23  Q2(c)",
        topic="Flame  Na⁺  yellow",
        qp=(ROOT / "paper2/qp/5070_s23_qp_21_(1).pdf", 3, "A sample of sodium chloride is tested using a flame test.", "State the colour of the flame seen in this test."),
        ms=(ROOT / "paper2/ms/5070_s23_ms_21.pdf", 7, "2(c)", "Question"),
    ),
    dict(
        paper="Paper 2",
        ref="5070/21 O/N/24  Q1(a)(ii)",
        topic="Flame  K⁺  lilac",
        qp=(ROOT / "paper2/qp/5070_w24_qp_21_(1).pdf", 3, "an atom that forms an ion that gives a lilac colour in a flame test", "[1]"),
        ms=(ROOT / "paper2/ms/5070_w24_ms_21.pdf", 5, "1(a)(ii)", "1(a)(iii)"),
    ),
    # Paper 3 only where Paper 2 has no write-in of that type.
    dict(
        paper="Paper 3",
        ref="5070/31 M/J/21  Q2(a)",
        topic="Chromium(III)  Cr³⁺",
        qp=(ROOT / "paper3/qp/5070_s21_qp_31.pdf", 5, "You are provided with solutions R and S.", "anion"),
        ms=(ROOT / "paper3/ms/5070_s21_ms_31.pdf", 7, "2(a)(ii)", "2(a)(iii)"),
    ),
    dict(
        paper="Paper 3",
        ref="5070/32 M/J/25  Q2(a)",
        topic="Flame method  +  Cu²⁺  blue-green",
        qp=(ROOT / "paper3/qp/5070_s25_qp_32.pdf", 6, "Do a flame test on one sample of A. Describe the method you use.", "[4]"),
        ms=(ROOT / "paper3/ms/5070_s25_ms_32.pdf", 8, "2(a)", "2(b)(i)"),
    ),
]


def crop_spec(spec, pad_top=10, pad_bot=28):
    path, page, start, end = spec[:4]
    return crop_page(str(path), page, start, end, pad_top=pad_top, pad_bot=pad_bot)


def render_full(path, page_1):
    doc = fitz.open(path)
    page = doc[page_1 - 1]
    pix = page.get_pixmap(matrix=DPI_M, colorspace=fitz.csRGB, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return ImageOps.invert(img)


def banner(img, title, subtitle):
    bar = 78
    canvas = Image.new("RGB", (img.width, img.height + bar), BLACK)
    d = ImageDraw.Draw(canvas)
    d.text((24, 12), title, font=FONT_SM, fill=WHITE)
    d.text((24, 44), subtitle, font=FONT_TINY, fill=GREY)
    canvas.paste(img, (0, bar))
    return canvas


def img_to_pdf_page(doc, img):
    w_pt = img.width / 2.2
    h_pt = img.height / 2.2
    page = doc.new_page(width=w_pt, height=h_pt)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    buf.seek(0)
    page.insert_image(page.rect, stream=buf.getvalue())


def main():
    pages = []
    failures = []

    # cover
    cover = new_page()
    d = ImageDraw.Draw(cover)
    y = 220
    lines = [
        "Cambridge O Level Chemistry  5070",
        "",
        "Ion tests and gas tests",
        "Question paper extracts  +  mark schemes",
        "",
        "2015 – 2025   ·   one question per test",
        "Paper 2, plus Paper 3 only if Paper 2 has no write-in",
        "Colours inverted.",
        "",
        "Cl⁻ Br⁻ I⁻ SO₄²⁻ NO₃⁻  NH₄⁺/NH₃  CO₂ SO₂ Cl₂ H₂ O₂",
        "Fe²⁺/Fe³⁺  Cu²⁺  Zn²⁺  Al³⁺  Cr³⁺",
        "Flame  Na yellow  K lilac  Cu blue-green",
    ]
    for line in lines:
        d.text((MARGIN + 20, y), line, font=FONT_SM if line.startswith("Types") or "Anions" in line or "Cations" in line or "Gases" in line or "Flame" in line else FONT, fill=WHITE if line and not line.startswith(" ") else GREY)
        y += 36 if line else 18
    pages.append(cover)

    n_ok = 0
    for i, item in enumerate(ITEMS, 1):
        print(f"[{i}/{len(ITEMS)}] {item['ref']}  {item['topic']}")
        try:
            qp_img = crop_spec(item["qp"])
            if "qp2" in item:
                qp_img2 = crop_spec(item["qp2"])
                w = max(qp_img.width, qp_img2.width)
                h = qp_img.height + 16 + qp_img2.height
                stacked = Image.new("RGB", (w, h), BLACK)
                stacked.paste(qp_img, (0, 0))
                stacked.paste(qp_img2, (0, qp_img.height + 16))
                qp_img = stacked
            ms_path, ms_page = item["ms"][0], item["ms"][1]
            ms_img = render_full(str(ms_path), ms_page)
        except Exception as e:
            failures.append((item["ref"], str(e)))
            print("  FAIL", e)
            continue

        q_page = new_page()
        y = draw_header(q_page, f"{item['paper']}   ·   {item['topic']}", item["ref"] + "   ·   QUESTION")
        paste(q_page, qp_img, y, None)
        pages.append(q_page)

        pages.append(
            banner(
                ms_img,
                f"MARK SCHEME   ·   {item['topic']}",
                item["ref"] + "   ·   look for this question number on the page",
            )
        )
        n_ok += 1

    toc = new_page()
    d = ImageDraw.Draw(toc)
    y = draw_header(toc, "Contents", "2015–2025  ·  inverted extracts")
    for n, item in enumerate(ITEMS, 1):
        line = f"{n:02d}   {item['paper'][:7]:<8}  {item['topic']}"
        d.text((MARGIN, y), line[:90], font=FONT_TINY, fill=WHITE)
        y += 22
        if y > A4[1] - 50:
            pages.insert(1, toc)
            toc = new_page()
            y = draw_header(toc, "Contents  (continued)", "")
    pages.insert(1, toc)

    doc = fitz.open()
    for im in pages:
        img_to_pdf_page(doc, im)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT), deflate=True)
    doc.close()
    print("WROTE", OUT, "image-pages", len(pages), "ok items", n_ok)
    print("FAILURES", len(failures))
    for f in failures:
        print(" ", f)


if __name__ == "__main__":
    main()
