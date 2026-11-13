#!/usr/bin/env python3
"""Biology 5090 dark-mode whole-question bank builder.

- Sources are used as-is: they are already dark-mode pages (light text on
  dark ground); no colour inversion is applied.
- Questions are arranged newest to oldest.
- Paper 1 (MCQ): the correct answer is written as plain text on the entry;
  no mark-scheme screenshot is used. The answer letter is parsed from the
  official mark-scheme text and cross-checked against the tracker keys.
- Paper 2 (Theory): the whole question is followed by its official
  mark-scheme section, clipped from the source scheme pages.
"""
import fitz, json, re, sys, os
from collections import defaultdict
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'biology-5090')
OUT = os.path.join(ROOT, '.rebuilt.pdf')
MANIFEST = os.path.join(ROOT, '.manifest.json')
STATS = os.path.join(ROOT, '.stats.json')
LOG = open(os.path.join(ROOT, 'build.log'), 'w', buffering=1)

def log(*a):
    print(*a, file=LOG)

# ---------------------------------------------------------------- tracker ---
HINT = re.compile(r'^Original visual referenced: (5090_\w+\.pdf), page (\d+)(?:[\u2013-](\d+))? Q(\d+)$')

def parse_tracker():
    groups = {}
    for ln in open(os.path.join(SRC, 'biology_5090_question_bank_tracker.txt'), encoding='utf-8'):
        f = ln.rstrip('\n').split('\t')
        if len(f) < 13 or f[12] != 'INCLUDED':
            continue
        rid, year, sess, var, paper, qnum = f[0], int(f[1]), f[2], f[3], f[4], int(f[5])
        ms_file, ms_sec, hint = f[8], f[9], f[10]
        m = HINT.match(hint)
        if not m:
            raise ValueError('bad hint: ' + hint)
        qp_file, p0, p1, hq = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2)), int(m.group(4))
        if hq != qnum:
            raise ValueError('hint q mismatch ' + rid)
        key = (year, sess, var, paper, qnum)
        g = groups.setdefault(key, dict(year=year, sess=sess, var=var, paper=paper, qnum=qnum,
                                        qp=qp_file, p0=p0, p1=p1, ms=ms_file,
                                        secs=set(), tkeys=set()))
        g['secs'].add(ms_sec)
        km = re.match(r'^Question \d+ / key ([A-D])$', ms_sec)
        if km:
            g['tkeys'].add(km.group(1))
        if g['qp'] != qp_file or g['ms'] != ms_file:
            raise ValueError('source mismatch ' + rid)
    return groups

SESS_RANK = {'October/November': 2, 'May/June': 1, 'February/March': 0}

def sort_key(g):
    return (-g['year'], -SESS_RANK[g['sess']], int(g['paper']), int(g['var']), g['qnum'])

def label_of(g):
    return f"{g['sess']} {g['year']} \u2022 Paper {g['paper']} \u2022 Variant {g['var']} \u2022 Question {g['qnum']}"

# ------------------------------------------------------- source documents ---
DOCS = {}
REPAIRED = set()

def get_doc(name):
    if name not in DOCS:
        DOCS[name] = fitz.open(os.path.join(SRC, name))
        log('open', name)
    return DOCS[name]

def repair_streams(doc, pno, aggressive):
    """Force text-bearing streams to start in black so the trailing
    difference-blend fill turns text visible white on dark ground."""
    page = doc[pno]
    for x in page.get_contents():
        s = doc.xref_stream(x)
        if s.startswith(b'%ArenaInvertBase') or b'%ArenaInvertInvert' in s:
            continue
        if b'BT' not in s:
            continue
        new = b'0 g\n0 G\n' + s
        if aggressive:
            new = new.replace(b'1 1 1 rg', b'0 0 0 rg').replace(b'1 1 1 g', b'0 0 0 g')
        if new != s:
            doc.update_stream(x, new)
    REPAIRED.add((doc.name, pno, aggressive))

WORD_CACHE = {}
LINE_CACHE = {}
PAPERNO_CACHE = {}

def words_display(page):
    k = (page.parent.name, page.number)
    if k not in WORD_CACHE:
        rm = page.rotation_matrix
        ws = []
        for w in page.get_text('words'):
            r = fitz.Rect(w[:4]) * rm
            ws.append((r, w[4], w[5], w[6], w[7]))
        WORD_CACHE[k] = ws
    return WORD_CACHE[k]

class Line:
    __slots__ = ('tokens', 'x0', 'x1', 'y0', 'y1', 'page', 'block', 'ln')

def lines_display(page):
    k = (page.parent.name, page.number)
    if k not in LINE_CACHE:
        by = defaultdict(list)
        for r, t, b, l, wn in words_display(page):
            by[(b, l)].append((r, t, wn))
        out = []
        for (b, l), ws in by.items():
            ws.sort(key=lambda z: (z[0].x0, z[2]))
            ln = Line()
            ln.tokens = [t for _, t, _ in ws]
            ln.x0 = min(z[0].x0 for z in ws); ln.x1 = max(z[0].x1 for z in ws)
            ln.y0 = min(z[0].y0 for z in ws); ln.y1 = max(z[0].y1 for z in ws)
            ln.page = page.number; ln.block = b; ln.ln = l
            # drop rotated side-margin warnings: tall narrow text
            if (ln.y1 - ln.y0) > 3 * (ln.x1 - ln.x0) + 12 and (ln.x1 - ln.x0) < 90:
                continue
            out.append(ln)
        out.sort(key=lambda l: (l.y0, l.x0))
        LINE_CACHE[k] = out
    return LINE_CACHE[k]

def display_bounds(page):
    """(x0,x1,ytop,ybot, col_x0s) of body text area, in display coords."""
    W, H = page.rect.width, page.rect.height
    lines = lines_display(page)
    body = [l for l in lines if l.y0 > 0.06 * H and l.y1 < 0.945 * H and l.tokens]
    if not body:
        return None
    x0 = min(l.x0 for l in body); x1 = max(l.x1 for l in body)
    y0 = min(l.y0 for l in body); y1 = max(l.y1 for l in body)
    # two-column detection: rich text lines starting in the right half AND
    # left lines that do not run across the page (which happens with tables
    # and with right-aligned mark totals on single-column pages)
    mid = (x0 + x1) / 2
    left = [l for l in body if l.x0 < mid - 10]
    right = [l for l in body if l.x0 > mid + 10]

    def is_rich(l):
        alpha = sum(1 for t in l.tokens if any(c.isalpha() for c in t))
        return len(l.tokens) >= 3 and alpha >= 2 and not l.tokens[0].startswith('[')

    two = False
    if left and right:
        rich_right = [l for l in right if is_rich(l)]
        cross_left = [l for l in left if l.x1 > mid + 5]
        med_x1 = sorted(l.x1 for l in left)[len(left) // 2]
        two = (len(rich_right) > 0.15 * len(body)
               and len(cross_left) < 0.25 * len(left)
               and med_x1 < mid - 2)
    cols = []
    for grp in (left, right) if two else [body]:
        if grp:
            cols.append(min(l.x0 for l in grp))
    return x0, x1, y0, y1, cols, two, mid

def page_paper_no(page):
    """Paper number from combined-mark-scheme page headers, else None."""
    k = (page.parent.name, page.number)
    if k in PAPERNO_CACHE:
        return PAPERNO_CACHE[k]
    res = None
    head = page.get_text()[:600]
    toks = re.findall(r'[\w/\u00a9\u2013.]+', head)

    def comp2paper(n):
        # component 11/12/21/22 ... -> paper 1/2; 01/02 ... -> paper 1/2
        return n // 10 if n >= 10 else n

    for i, t in enumerate(toks):
        if t == '5090' and i + 1 < len(toks) and re.fullmatch(r'\d{1,2}', toks[i + 1]):
            res = comp2paper(int(toks[i + 1])); break
        m = re.fullmatch(r'5090/(\d\d)', t)
        if m:
            # cover pages list several components; keep only unique hits
            nums = set(re.findall(r'5090/(\d\d)', head))
            if len(nums) == 1:
                res = comp2paper(int(m.group(1)))
            break
    PAPERNO_CACHE[k] = res
    return res


def ms_section_bounds(doc, paper):
    """(first, last) 1-based page range of the mark-scheme section for
    `paper` inside a possibly combined mark-scheme file. Header-less pages
    (covers, colophons) attach to the following section."""
    nums = [page_paper_no(doc[i]) for i in range(len(doc))]
    for i, n in enumerate(nums):
        if n == paper:
            j = i + 1
            while j < len(nums) and (nums[j] is None or nums[j] == paper):
                j += 1
            return (i + 1, j)
    return None

# ------------------------------------------------------------ clip region ---
def clip_jpeg(page, rect, zoom=None, quality=None):
    if zoom is None:
        zoom = ZOOM
    if quality is None:
        quality = QUALITY
    rect = fitz.Rect(rect) & page.rect
    if rect.is_empty:
        return None
    def render():
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect)
        return pix
    pix = render()
    if pix.n == 3:
        v = pix.samples
        step = max(1, len(v) // 6000)
        mean = sum(v[::step]) / len(v[::step])
    else:
        mean = 255
    if mean < 2.2:
        # invisible text (white painted before the difference fill): repair,
        # but only when words actually exist inside the clip
        has_words = any(r.intersects(rect) for r, *_ in words_display(page))
        if has_words:
            repair_streams(page.parent, page.number, aggressive=False)
            pix = render()
            v = pix.samples; step = max(1, len(v) // 6000)
            mean = sum(v[::step]) / len(v[::step])
    if mean < 2.2:
        has_words = any(r.intersects(rect) for r, *_ in words_display(page))
        if has_words:
            repair_streams(page.parent, page.number, aggressive=True)
            pix = render()
            v = pix.samples; step = max(1, len(v) // 6000)
            mean = sum(v[::step]) / len(v[::step])
            if mean < 2.2:
                log('WARN still-dark clip', page.parent.name, page.number, rect)
    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    import io
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=quality, optimize=True)
    return buf.getvalue()

# --------------------------------------------------------- marker finding ---
HDR = re.compile(r'(Mark Scheme|Syllabus|^Page \d|5090|BIOLOGY|^\u00a9|PUBLISHED|Cambridge|GCE|UCLES|MAXIMUM|SYLLABUS|UNIVERSITY|General Certificate)', re.I)

def is_headerish(l):
    return bool(HDR.search(' '.join(l.tokens[:4])))

def row_tokens(lines, i, two=False, mid=0):
    """Tokens of the whole visual row starting from line i (table cells on
    the same row are joined left to right; on two-column pages only cells
    within the same column are joined)."""
    l = lines[i]
    def same_row(o):
        if o is l:
            return True
        ov = min(l.y1, o.y1) - max(l.y0, o.y0)
        if ov < 0.5 * min(l.y1 - l.y0, o.y1 - o.y0):
            return False
        if two and ((l.x0 < mid) != (o.x0 < mid)):
            return False
        return o.x0 >= l.x0 - 2
    pieces = [o for o in lines if same_row(o)]
    pieces.sort(key=lambda o: o.x0)
    toks = []
    x_end = None
    first_gap = 0.0
    for k, o in enumerate(pieces):
        if x_end is not None:
            gap = o.x0 - x_end
            if k == 1:
                first_gap = gap
            limit = 150 if k == 1 else (80 if len(toks) <= 2 else 40)
            if gap > limit:
                break
        toks += o.tokens
        x_end = o.x1
    return toks, first_gap

def marker_candidates(page, q, kind):
    """Lines that could start question q (display coords). kind 'qp' or 'ms'."""
    out = []
    b = display_bounds(page)
    if not b:
        return out
    x0, x1, y0, y1, cols, two, mid = b
    lines = lines_display(page)
    for i, l in enumerate(lines):
        if not l.tokens:
            continue
        if l.y0 < y0 - 1 or l.y1 > y1 + 1 or is_headerish(l):
            continue
        t0 = l.tokens[0]
        rts, gap0 = row_tokens(lines, i, two, mid)
        isolated = len(rts) >= 2 and gap0 > 25
        row_y1 = max(o.y1 for o in lines
                     if o is l or (min(l.y1, o.y1) - max(l.y0, o.y0)) > 0.5 * min(l.y1 - l.y0, o.y1 - o.y0))
        below = [o for o in lines if o.y0 > row_y1 - 3]
        below.sort(key=lambda o: (o.y0, o.x0))
        nxt_line = below[0] if below else None
        nxt = nxt_line.tokens[0] if nxt_line is not None and nxt_line.tokens else ''
        above = [o for o in lines if o is not l and o.y1 <= l.y0 + 1]
        block_first = not any(l.y0 - o.y1 <= 3.5 for o in above)
        score = 0

        def strong(t):
            t = t.lstrip('\u2018\u2019\u201c\u201d"\'`')
            return t[:1].isupper() or t in ('Either', 'OR', 'Or')

        mnum = re.fullmatch(r'(\d{1,2})([EO]?)', t0)
        if mnum and int(mnum.group(1)) == q:
            if len(rts) >= 2 and rts[1].startswith('('):
                score = 55
            elif isolated:
                score = 55
            elif len(rts) >= 2 and strong(rts[1]):
                score = 50
            elif len(rts) == 1 and nxt.startswith('('):
                score = 60
            elif len(rts) == 1 and strong(nxt) \
                    and nxt_line is not None and len(nxt_line.tokens) >= 3:
                score = 40
            elif kind == 'ms' and len(rts) == 1 and nxt[:1].isalpha() \
                    and nxt_line is not None and len(nxt_line.tokens) >= 2:
                score = 45
            elif kind == 'ms' and len(l.tokens) <= 2 and len(rts) >= 2 \
                    and rts[1][:1].isalpha():
                score = 45
            if score and block_first:
                score += 5
        elif re.fullmatch(r'%d\([a-z]\)(\([ivx]+\))?' % q, t0):
            # first subpart label such as 7(a) or 1(a)(i)
            if '(a)' in t0:
                score = 70
        if not score:
            continue
        # x-position: must sit at a column start
        okx = l.x0 < x0 + 50
        if two and not okx:
            for cx in cols[1:]:
                if abs(l.x0 - cx) < 30:
                    okx = True
        if not okx:
            continue
        out.append((score, l))
    return out

def read_pos(page_no, l, mid):
    half = 0 if l.x0 < mid else 1
    return (page_no, half, l.y0)

def question_extent(doc, p0, p1, q, kind, hinted=True, boundary=None):
    """Return list of display rects covering question q, from its marker to
    the start of question q+1 (or the end of the hinted span).

    When hinted, the tracker's end page is the page where question q+1
    starts, so end-marker candidates on that page are strongly preferred.
    `boundary` limits marker search to (first, last) 1-based pages of the
    question's own mark-scheme section in combined scheme files."""
    lo = p0 - 1
    hi = min(p1, len(doc))
    if boundary is not None:
        lo = max(lo, boundary[0] - 1)
        hi = min(hi, boundary[1])
    pages = [doc[i] for i in range(lo, hi)]
    if not pages:
        return [], 'no-pages'
    best = None
    for pi in range(lo, hi):
        page = doc[pi]
        for sc, l in marker_candidates(page, q, kind):
            if pi == lo:
                sc += 5
            if best is None or sc > best[0]:
                best = (sc, pi, l)
    if best is None:
        # widen one page each way (still within the section boundary)
        for pi in (lo - 1, hi):
            if 0 <= pi < len(doc) and (boundary is None or boundary[0] - 1 <= pi < boundary[1]):
                for sc, l in marker_candidates(doc[pi], q, kind):
                    if best is None or sc > best[0]:
                        best = (sc - 5, pi, l)
    if best is None:
        return [], 'no-marker'
    _, spi, sl = best
    b = display_bounds(doc[spi])
    mid = b[6]
    start = read_pos(spi, sl, mid)

    # end marker: question q+1
    cand = []
    stop = min(p1, len(doc)) if hinted else len(doc)
    if boundary is not None:
        stop = min(stop, boundary[1])
    for pi in range(spi, stop):
        for sc, l in marker_candidates(doc[pi], q + 1, kind):
            if sc < 40:
                continue
            pos = read_pos(pi, l, mid)
            if pos > start:
                cand.append((sc, pos, l, pi))
    note = ''
    end, endl = None, None
    if cand and hinted:
        on_end_page = [c for c in cand if c[3] == min(p1, len(doc)) - 1]
        pool = on_end_page or cand
        pool.sort(key=lambda c: (-c[0], c[1]))
        sc, end, endl, _ = pool[0]
        if not on_end_page:
            note = 'early-end'
    elif cand:
        cand.sort(key=lambda c: (-c[0], c[1]))
        sc, end, endl, _ = cand[0]
    if end is None:
        if kind == 'ms':
            # combined schemes: stop at the next paper section; otherwise
            # run to the end of the document, skipping trailing blanks
            start_pn = page_paper_no(doc[spi])
            epi = spi
            mstop = min(len(doc), boundary[1]) if boundary is not None else len(doc)
            for pi in range(spi + 1, mstop):
                pn = page_paper_no(doc[pi])
                if pn is not None and start_pn is not None and pn != start_pn:
                    break
                if pn is not None and start_pn is None:
                    break
                epi = pi
        else:
            epi = min(p1, len(doc)) - 1
        while epi > spi:
            pg = doc[epi]
            b2 = display_bounds(pg)
            if b2 is not None and seg_is_blank(pg, fitz.Rect(b2[0] - 8, b2[2] - 2, b2[1] + 8, b2[3] + 3)):
                epi -= 1
            else:
                break
        if epi == spi:
            b2 = display_bounds(doc[spi])
            end = (spi, 2, b2[3] + 4)
        else:
            b2 = display_bounds(doc[epi])
            if b2 is None:
                epi -= 1
                b2 = display_bounds(doc[epi])
            end = (epi, 2, b2[3] + 4)
        note = 'bottom-end'
    # appendix pages terminate a mark scheme
    if kind == 'ms':
        for pi in range(spi, end[0] + 1):
            for l in lines_display(doc[pi]):
                if l.tokens and re.match(r'^appendix', l.tokens[0], re.I) and not is_headerish(l):
                    pos = read_pos(pi, l, mid)
                    if start < pos < end:
                        end, endl = pos, (pi, l)
                        note = 'appendix-end'
    return [s for s in segment_rects(doc, start, end, mid)
            if not seg_is_blank(doc[s[0]], s[1])], note

BOILER = re.compile(r'(?i)cambridge|examination|syndicate|university|department|papacambridge|5090/|\u00a9|ucles|do not write|margin|turn over|blank page|dfd|\*'
                    r'|permission|copyright|publisher|cleared|sought|opportunity|earliest|unauthorised|traceable|re-uploading|mirroring|re-hosting')
STOP = set('of the and is a which itself to be as part in for on at or turn over blank page'.split())

def seg_is_blank(page, rect):
    for l in lines_display(page):
        if l.tokens and ' '.join(l.tokens).lower().strip() == 'blank page':
            return True
    pix = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3), clip=rect)
    v = pix.samples
    n = max(1, len(v) // 3)
    bright = sum(1 for i in range(0, len(v), 3) if v[i] > 50 or v[i + 1] > 50 or v[i + 2] > 50)
    frac = bright / n
    cwords = 0
    for r, t, *_ in words_display(page):
        if not r.intersects(rect):
            continue
        if (r.y1 - r.y0) > 3 * (r.x1 - r.x0) + 12 and (r.x1 - r.x0) < 90:
            continue  # side-margin warning text
        tl = t.strip().lower().strip('[({,.;:!?')
        if not re.search(r'[a-z]', tl) or tl in STOP or BOILER.search(tl):
            continue
        cwords += 1
    if cwords >= 3:
        return False
    return frac < 0.015

def segment_rects(doc, start, end, mid):
    """Split [start,end] in reading order into column-aware display rects."""
    spi, sh, sy = start
    epi, eh, ey = end
    rects = []
    for pi in range(spi, epi + 1):
        page = doc[pi]
        b = display_bounds(page)
        if b is None:
            continue
        x0, x1, y0, y1, cols, two, midp = b
        halves = [(x0 - 6, midp + 2), (midp - 2, x1 + 6)] if two else [(x0 - 8, x1 + 8)]
        for h, (hx0, hx1) in enumerate(halves):
            ty0 = y0 - 2 if pi > spi or h > sh else sy - 1
            if (pi, h) == (spi, sh):
                ty0 = sy - 1
            if (pi, h) == (epi, eh):
                ty1 = ey
            else:
                ty1 = y1 + 3
            if (pi, h) < (spi, sh) or (pi, h) > (epi, eh):
                continue
            if ty1 > ty0 + 10:
                rects.append((pi, fitz.Rect(hx0, ty0, hx1, ty1)))
    return rects

# ------------------------------------------------------------- MCQ keys -----
def parse_keys(doc, paper):
    keys = {}
    want = int(paper)
    for page in doc:
        pn = page_paper_no(page)
        if pn is not None and pn != want:
            continue
        toks = re.findall(r'[A-Za-z0-9]+', page.get_text())
        for i in range(len(toks) - 1):
            a, b = toks[i], toks[i + 1]
            if re.fullmatch(r'\d{1,2}', a) and re.fullmatch(r'[A-D]', b):
                n = int(a)
                if 1 <= n <= 40 and n not in keys:
                    keys[n] = b
    return keys

KEYCACHE = {}

def answer_for(g):
    msf = g['ms']
    if msf not in KEYCACHE:
        doc = get_doc(msf)
        KEYCACHE[msf] = parse_keys(doc, g['paper'])
        log('keys parsed', msf, len(KEYCACHE[msf]))
    keys = KEYCACHE[msf]
    parsed = keys.get(g['qnum'])
    tr = sorted(g['tkeys'])
    tkey = tr[0] if tr else None
    if parsed and tkey and parsed != tkey:
        log('KEY MISMATCH', msf, g['qnum'], 'parsed', parsed, 'tracker', tkey)
    return parsed or tkey

# ---------------------------------------------------------- composition -----
PW, PH = 595.28, 841.89
M = 26.0
CW = PW - 2 * M
ZOOM = 1.55
QUALITY = 55

def build():
    groups = sorted(parse_tracker().values(), key=sort_key)
    log('groups', len(groups))
    out = fitz.open()
    page = None
    y = 0.0
    manifest = []
    cur_sess = None
    FAILED = []

    def new_page():
        nonlocal page, y
        page = out.new_page(width=PW, height=PH)
        page.draw_rect(page.rect, color=None, fill=(0, 0, 0))
        y = M

    new_page()
    toc = []
    np1 = np2 = nimg = 0

    for gi, g in enumerate(groups):
        if page is None:
            new_page()
        label = label_of(g)
        is_mcq = g['paper'] == '1'
        answer = answer_for(g) if is_mcq else None
        # bookmark session header
        sesskey = (g['year'], g['sess'])
        if sesskey != cur_sess:
            cur_sess = sesskey
            toc.append([1, f"{g['sess']} {g['year']}", out.page_count])
        # ---- extract content first so the header can travel with its clips
        missing = None
        parts = []
        rects, note = question_extent(get_doc(g['qp']), g['p0'], g['p1'], g['qnum'], 'qp')
        if not rects:
            missing = 'qp ' + (note or '')
        else:
            if note:
                log('qp note', label, note)
            parts = [('qp', g['qp'], rects)]
            if not is_mcq:
                mdoc = get_doc(g['ms'])
                mb = ms_section_bounds(mdoc, int(g['paper']))
                if mb is None:
                    mb = (1, len(mdoc))
                mrects, mnote = question_extent(mdoc, mb[0], mb[1], g['qnum'], 'ms',
                                               hinted=False, boundary=mb)
                if not mrects:
                    missing = 'ms ' + (mnote or '')
                    parts = []
                else:
                    if mnote:
                        log('ms note', label, mnote)
                    parts.append(('ms', g['ms'], mrects))
        if missing:
            log('FAIL', label, missing)
            FAILED.append(label + ' [' + missing + ']')

        def first_dh(rs):
            for pi, r in rs:
                h, w = r.y1 - r.y0, r.x1 - r.x0
                if h > 10 and w > 1:
                    return h * CW / w
            return 0.0

        fdh = 0.0
        for kind, fname, rs in parts:
            d = first_dh(rs)
            if d:
                fdh = d
                break
        # header lines (kept on the same page as the first clip)
        hdr = label
        need = 30 if is_mcq else 18
        if y > M + 2 and y + need + 8 + min(fdh, PH - 2 * M - need) > PH - M:
            new_page()
        entry_start = out.page_count
        if y > M + 2:
            y += 10  # gap between entries
        page.insert_text((M, y + 10), hdr, fontsize=8.6, fontname='helv', color=(0.82, 0.84, 0.86))
        y += 14
        if is_mcq:
            page.insert_text((M, y + 13), f"Correct answer: {answer}", fontsize=13, fontname='hebo',
                             color=(1, 1, 1))
            y += 22
        if missing:
            page.insert_text((M, y + 10), f"MISSING CONTENT ({missing}) — recorded in the exclusions file.",
                             fontsize=9, fontname='helv', color=(0.9, 0.5, 0.5))
            y += 18
        toc.append([2, f"Paper {g['paper']} V{g['var']} Q{g['qnum']}" +
                    (f" \u2014 answer {answer}" if is_mcq else ''), entry_start])

        mrec = dict(label=label, pages=[], items=[])

        for kind, fname, rs in parts:
            pgs = sorted({r[0] for r in rs})
            mrec['items'].append(dict(kind=kind, source=fname,
                                      source_pages=[p + 1 for p in (pgs[0], pgs[-1])]))
            for pi, r in rs:
                jpeg = clip_jpeg(get_doc(fname)[pi], r)
                if jpeg is None:
                    continue
                iw, ih = Image.open(__import__('io').BytesIO(jpeg)).size
                scale = CW / iw
                dh = ih * scale
                dw = CW
                if y + dh > PH - M:
                    if y > M + need + 2:
                        new_page()
                    avail = PH - M - y
                    if dh > avail:
                        dw = CW * avail / dh
                        dh = avail
                page.insert_image(fitz.Rect(M, y, M + dw, y + dh), stream=jpeg)
                y += dh + 6
                nimg += 1
            y += 4
        mrec['pages'] = [entry_start, out.page_count if y > M + 2 else out.page_count]
        manifest.append(mrec)
        if is_mcq:
            np1 += 1
        else:
            np2 += 1
        if (gi + 1) % 100 == 0:
            log('progress', gi + 1, 'pages', out.page_count)

    out.set_toc(toc)
    out.set_metadata({'title': 'Biology 5090 Question Bank (newest to oldest, dark mode)',
                      'subject': 'Whole questions with official mark schemes; MCQ answers in text'})
    out.save(OUT, garbage=3, deflate=True, clean=True)
    out.close()
    size = os.path.getsize(OUT) / 1048576
    stats = dict(pages=fitz.open(OUT).page_count, groups=len(groups), mcq=np1, theory=np2,
                 images=nimg, size_mib=round(size, 3), repaired_pages=len({(a, b) for a, b, _ in REPAIRED}),
                 failures=FAILED)
    json.dump(manifest, open(MANIFEST, 'w'), indent=1)
    json.dump(stats, open(STATS, 'w'), indent=1)
    log('DONE', stats)
    print('DONE', stats)

if __name__ == '__main__':
    only = os.environ.get('ONLY')
    if only:
        # quick subset mode: ONLY=<year>:<paper>:<qnum>
        yr, pp, qq = only.split(':')
        gl = [g for g in sorted(parse_tracker().values(), key=sort_key)
              if g['year'] == int(yr) and g['paper'] == pp and (qq == '*' or g['qnum'] == int(qq))]
        # monkey-patch build loop via env subset
        import types
        orig = parse_tracker
        parse_tracker = lambda: {(g['year'], g['sess'], g['var'], g['paper'], g['qnum']): g for g in gl}
        globals()['parse_tracker'] = parse_tracker
    build()
