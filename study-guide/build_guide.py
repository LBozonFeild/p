#!/usr/bin/env python3
"""
Build the Cambridge O Level Computer Science 2210 (Paper 2 focus) study guide PDF.

Theme: black-and-white dark mode (dark background, light text, no colours),
no headers or footers on any page.

Content sources: guide_part1.txt, guide_part2.txt (same folder).
Markup (blocks separated by blank lines):
  # / ## / ###   headings
  - item          bullet list
  ``` fenced      code block (also allowed inside Q/A blocks)
  Q:(n) ...       practice question carrying n marks (auto-numbered per section)
  A: ...          model answer / mark scheme (auto-numbered to match questions)
  N: ...          highlighted note/tip box
  T:              table; following lines are rows like | cell | cell | (first row = header)
  plain lines     paragraph
Inline: **bold**, __mono__ or `mono`   (characters < > & are escaped automatically)
"""
import os
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Preformatted,
    Spacer, Table, TableStyle, PageBreak, HRFlowable,
)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
OUT = os.path.join(HERE, "computer-science-2210-study-guide.pdf")

pdfmetrics.registerFont(TTFont("DejaVu", f"{FONT_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", f"{FONT_DIR}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuMono", f"{FONT_DIR}/DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuMono-Bold", f"{FONT_DIR}/DejaVuSansMono-Bold.ttf"))
pdfmetrics.registerFontFamily(
    "DejaVu", normal="DejaVu", bold="DejaVu-Bold",
    italic="DejaVu", boldItalic="DejaVu-Bold",
)

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# ------------------------------------------------- dark monochrome palette
BG        = colors.HexColor("#0b0b0b")   # page background
PANEL     = colors.HexColor("#161616")   # code / question panels
PANEL_ALT = colors.HexColor("#1e1e1e")   # answer panels
LINE      = colors.HexColor("#4a4a4a")   # borders
LINE_DIM  = colors.HexColor("#333333")
TEXT      = colors.HexColor("#e8e8e8")   # body text
TEXT_DIM  = colors.HexColor("#a8a8a8")   # secondary text
TEXT_HEAD = colors.HexColor("#ffffff")   # headings
CODE_TXT  = colors.HexColor("#d6d6d6")

# ---------------------------------------------------------------- styles
def S(name, **kw):
    base = dict(fontName="DejaVu", fontSize=9.5, leading=13.2,
                textColor=TEXT, spaceAfter=6)
    base.update(kw)
    return ParagraphStyle(name, **base)

st_title    = S("title", fontName="DejaVu-Bold", fontSize=27, leading=32,
                textColor=TEXT_HEAD, spaceAfter=10)
st_subtitle = S("subtitle", fontName="DejaVu", fontSize=14, leading=19,
                textColor=colors.HexColor("#bdbdbd"), spaceAfter=6)
st_covermeta = S("covermeta", fontSize=10, leading=15,
                 textColor=TEXT_DIM, spaceAfter=4)
st_h1 = S("h1", fontName="DejaVu-Bold", fontSize=16.5, leading=20,
          textColor=TEXT_HEAD, spaceBefore=16, spaceAfter=8, keepWithNext=True)
st_h2 = S("h2", fontName="DejaVu-Bold", fontSize=12.5, leading=16,
          textColor=colors.HexColor("#d0d0d0"), spaceBefore=11, spaceAfter=5,
          keepWithNext=True)
st_h3 = S("h3", fontName="DejaVu-Bold", fontSize=10.5, leading=14,
          textColor=colors.HexColor("#b8b8b8"), spaceBefore=8, spaceAfter=4,
          keepWithNext=True)
st_body = S("body")
st_bullet = S("bullet", leftIndent=14, bulletIndent=3, spaceAfter=3)
st_code = S("code", fontName="DejaVuMono", fontSize=8.1, leading=11,
            textColor=CODE_TXT, backColor=PANEL,
            borderColor=LINE_DIM, borderWidth=0.6,
            borderPadding=(6, 8, 6, 8), spaceBefore=4, spaceAfter=8, leftIndent=2)
st_qhead = S("qhead", fontName="DejaVu-Bold", fontSize=9.8, leading=13.5,
             textColor=TEXT_HEAD, spaceAfter=4)
st_qbody = S("qbody", fontSize=9.5, leading=13.2, textColor=TEXT, spaceAfter=2)
st_ahead = S("ahead", fontName="DejaVu-Bold", fontSize=9.8, leading=13.5,
             textColor=TEXT_HEAD, spaceAfter=4)
st_abody = S("abody", fontSize=9.5, leading=13.2, textColor=TEXT, spaceAfter=2)
st_note = S("note", fontSize=9.2, leading=12.8,
            textColor=colors.HexColor("#d8d8d8"), spaceAfter=2)
st_tbl = S("tbl", fontName="DejaVuMono", fontSize=8.1, leading=11,
           textColor=CODE_TXT, spaceAfter=0)
st_tblhead = S("tblhead", fontName="DejaVuMono-Bold", fontSize=8.1, leading=11,
               textColor=TEXT_HEAD, spaceAfter=0)
st_toc0 = S("toc0", fontName="DejaVu-Bold", fontSize=10.5, leading=17,
            textColor=TEXT_HEAD, spaceAfter=2)
st_toc1 = S("toc1", fontSize=9.3, leading=14.5, leftIndent=16,
            textColor=TEXT_DIM, spaceAfter=1)

# ------------------------------------------------------------- text utils
def esc(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r'<font name="DejaVuMono">\1</font>', text)
    text = re.sub(r"`(.+?)`", r'<font name="DejaVuMono">\1</font>', text)
    return text

def para(text, style=st_body):
    return Paragraph(esc(text).replace("\n", "<br/>"), style)

def code_block(lines):
    return Preformatted("\n".join(lines), st_code)

# ------------------------------------------------------------- doc template
def paint_background(canv, doc):
    """Full-page dark background — no headers, no footers."""
    canv.saveState()
    canv.setFillColor(BG)
    canv.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    canv.restoreState()

class GuideDoc(BaseDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, pagesize=A4,
                         leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=16 * mm, bottomMargin=16 * mm, **kw)
        frame = Frame(MARGIN, 16 * mm, CONTENT_W, PAGE_H - 32 * mm, id="body",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="all", frames=[frame], onPage=paint_background),
        ])

    def afterFlowable(self, flowable):
        if hasattr(flowable, "toc_level"):
            self.notify("TOCEntry", (flowable.toc_level, flowable.getPlainText(), self.page))

def heading(text, level):
    p = para(text, [st_h1, st_h2, st_h3][level])
    p.toc_level = 0 if level == 0 else 1
    return p

# ------------------------------------------------------------- block parser
def split_blocks(text):
    blocks, cur = [], []
    for line in text.splitlines():
        if line.strip() == "":
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line.rstrip())
    if cur:
        blocks.append(cur)
    return blocks

def split_chunks(lines):
    """Split a block into ('text', [lines]) / ('code', [lines]) chunks at ``` fences."""
    chunks, cur, in_code = [], [], False
    for ln in lines:
        if ln.strip().startswith("```"):
            if cur:
                chunks.append(("code" if in_code else "text", cur))
                cur = []
            in_code = not in_code
            continue
        cur.append(ln)
    if cur:
        chunks.append(("code" if in_code else "text", cur))
    return chunks

def chunk_flowables(lines, text_style):
    flows = []
    for kind, lns in split_chunks(lines):
        if kind == "code":
            flows.append(code_block(lns))
        else:
            joined = "\n".join(lns)
            flows.append(Paragraph(esc(joined).replace("\n", "<br/>"), text_style))
    return flows

def make_table(lines):
    rows = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        cells = [c.strip() for c in s.split("|")]
        rows.append(cells)
    if not rows:
        return Spacer(1, 1)
    ncols = max(len(r) for r in rows)
    data = []
    for i, r in enumerate(rows):
        r = r + [""] * (ncols - len(r))
        style = st_tblhead if i == 0 else st_tbl
        data.append([Paragraph(esc(c), style) for c in r])
    colw = CONTENT_W / ncols
    t = Table(data, colWidths=[colw] * ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b2b2b")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#141414")),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE_DIM),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t

def boxed(flows, bg, border):
    t = Table([[flows]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(border)),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t

def build_story():
    story = []

    # ---------- cover ----------
    story.append(Spacer(1, 42 * mm))
    story.append(Paragraph("Beyond the Basics", st_title))
    story.append(Paragraph("Pseudocode &amp; Python · Flowcharts · Logic Gates", st_subtitle))
    story.append(HRFlowable(width="100%", thickness=1.2,
                            color=colors.HexColor("#8a8a8a"), spaceBefore=8, spaceAfter=14))
    story.append(Paragraph(
        "A subtopic-by-subtopic study guide for everything <b>after</b> the basics. Every subtopic "
        "follows the same recipe: an explanation built on analogies and worked through with real "
        "values, examples in pseudocode, Python and flowchart form, the common errors, and practice "
        "questions — with every answer collected at the back of the guide in full detail.", st_covermeta))
    story.append(Paragraph(
        "Based on the <b>Cambridge O Level Computer Science 2210</b> syllabus for 2026–2028, "
        "Paper 2: Algorithms, Programming and Logic (Topics 7–10), including the 15-mark "
        "scenario question.", st_covermeta))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Compiled 12 November 2026", st_covermeta))
    story.append(PageBreak())

    # ---------- table of contents ----------
    story.append(Paragraph("Contents", st_h1))
    toc = TableOfContents()
    toc.levelStyles = [st_toc0, st_toc1]
    story.append(toc)
    story.append(PageBreak())

    # ---------- content ----------
    qn = an = 0
    for part in ("guide_part1.txt", "guide_part2.txt", "guide_part3.txt"):
        with open(os.path.join(HERE, part), encoding="utf-8") as fh:
            blocks = split_blocks(fh.read())
        for block in blocks:
            first = block[0]
            if first.startswith("### "):
                story.append(heading(first[4:].strip(), 2))
            elif first.startswith("## "):
                story.append(heading(first[3:].strip(), 1))
            elif first.startswith("# "):
                story.append(heading(first[2:].strip(), 0))
            elif first.startswith("T:"):
                story.append(make_table(block[1:]))
                story.append(Spacer(1, 6))
            elif first.startswith("Q:"):
                qn += 1
                m = re.match(r"^Q:\((\d+)\)\s*(.*)$", first)
                marks, text = (int(m.group(1)), m.group(2)) if m else (0, first[2:].strip())
                mk = f"{marks} mark" + ("s" if marks != 1 else "")
                head = Paragraph(f'<b>Q{qn}.</b>  <font size="8" color="#9a9a9a">[{mk}]</font>',
                                 st_qhead)
                body_lines = [text] + block[1:]
                flows = chunk_flowables(body_lines, st_qbody)
                story.append(boxed([head] + flows, "#171717", "#4a4a4a"))
                story.append(Spacer(1, 7))
            elif first.startswith("A:"):
                an += 1
                head = Paragraph(f'<b>Answer {an}</b>', st_ahead)
                body_lines = [first[2:].strip()] + block[1:]
                flows = chunk_flowables(body_lines, st_abody)
                story.append(boxed([head] + flows, "#1e1e1e", "#6a6a6a"))
                story.append(Spacer(1, 7))
            elif first.startswith("N:"):
                rest = first[2:].strip()
                m = re.match(r"^\(([^)]+)\)\s*(.*)$", rest, re.S)
                label = m.group(1) if m else "Note"
                body_lines = ([m.group(2)] if m else [rest]) + block[1:]
                flows = chunk_flowables(body_lines, st_note)
                story.append(boxed([Paragraph(f"<b>{esc(label)}</b>", st_note)] + flows,
                                   "#212121", "#7a7a7a"))
                story.append(Spacer(1, 7))
            elif first.startswith("- "):
                for ln in block:
                    s = ln[2:].strip() if ln.startswith("- ") else ln.strip()
                    story.append(Paragraph(esc(s), st_bullet, bulletText="•"))
                story.append(Spacer(1, 4))
            else:
                for kind, lns in split_chunks(block):
                    if kind == "code":
                        story.append(code_block(lns))
                    else:
                        story.append(para("\n".join(lns)))
    return story


def main():
    doc = GuideDoc(OUT)
    doc.multiBuild(build_story())
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
