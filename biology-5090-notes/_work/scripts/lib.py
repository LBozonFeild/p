# Shared helpers: PDF access (PyMuPDF), display-orientation words/lines, rendering without the ArenaInvert wrapper.
import os, re, json, sys, warnings
warnings.filterwarnings("ignore")
import fitz
# All paths are derived from the location of this file, so the scripts run in any checkout of the repository.
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # <repo>/biology-5090-notes/_work   (scripts, state, data, notes)
OUT = os.path.dirname(W)                                           # <repo>/biology-5090-notes         (the five deliverables)
SRC = os.path.join(os.path.dirname(OUT), "biology-5090")           # <repo>/biology-5090               (source PDFs)
IMG = os.environ.get("BIO5090_IMG", "/home/user/img")              # scratch PNGs, kept outside the repository
try:
    os.makedirs(IMG, exist_ok=True)
except OSError:
    import tempfile
    IMG = os.path.join(tempfile.gettempdir(), "bio5090_img"); os.makedirs(IMG, exist_ok=True)

def jload(p, default=None):
    p = p if p.startswith("/") else os.path.join(W, p)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)

def jsave(p, obj):
    p = p if p.startswith("/") else os.path.join(W, p)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, p)

def opendoc(fn, clean=False):
    d = fitz.open(os.path.join(SRC, fn))
    if clean:
        # The wrapper's first stream paints the page white and leaves WHITE as the fill colour, so anything the
        # original stream draws before it sets a colour of its own would be invisible. Both wrapper streams are
        # therefore reduced to balanced q / Q pairs (clean="old" keeps the first stream - only for comparison).
        for p in d:
            for x in p.get_contents():
                s = d.xref_stream(x)
                if b"%ArenaInvertInvert" in s:
                    d.update_stream(x, b"\nQ\nQ\n")
                elif b"%ArenaInvertBase" in s and clean != "old":
                    d.update_stream(x, b"q\nq\n")
    return d

def _words_from_chars(page):
    """rebuild words from single characters (for pages whose text is emitted in overlapping strips / fragments)"""
    m = page.rotation_matrix
    chars = []
    for b in page.get_text("rawdict")["blocks"]:
        if b["type"] != 0: continue
        for l in b["lines"]:
            for sp in l["spans"]:
                for c in sp["chars"]:
                    r = fitz.Rect(c["bbox"]) * m; r.normalize()
                    chars.append((r.x0, r.y0, r.x1, r.y1, c["c"], sp["size"]))
    chars.sort(key=lambda c: ((c[1] + c[3]) / 2, c[0]))
    lines = []
    for c in chars:
        yc = (c[1] + c[3]) / 2
        if lines and abs(lines[-1][0] - yc) <= 3: lines[-1][1].append(c)
        else: lines.append([yc, [c]])
    out = []
    for yc, cs in lines:
        cs.sort(key=lambda c: (c[0], c[4]))
        kept = []
        for c in cs:
            if any(k[4] == c[4] and abs(k[0] - c[0]) < 1.2 and abs(k[1] - c[1]) < 2 for k in kept[-6:]):
                continue
            kept.append(c)
        cur = None
        for c in kept:
            if c[4].strip() == "":
                if cur: out.append(tuple(cur)); cur = None
                continue
            if cur and c[0] - cur[2] > max(1.6, 0.22 * c[5]):
                out.append(tuple(cur)); cur = None
            if cur is None: cur = [c[0], c[1], c[2], c[3], c[4]]
            else:
                cur[2] = max(cur[2], c[2]); cur[1] = min(cur[1], c[1]); cur[3] = max(cur[3], c[3]); cur[4] += c[4]
        if cur: out.append(tuple(cur))
    return out

def page_words(page):
    """words in DISPLAY orientation: (x0,y0,x1,y1,text)"""
    m = page.rotation_matrix
    out = []
    for w in page.get_text("words"):
        r = fitz.Rect(w[:4]) * m
        r.normalize()
        out.append((r.x0, r.y0, r.x1, r.y1, w[4]))
    # fragmented page? (many words overlapping their neighbours on the same line)
    ws = sorted(out, key=lambda w: (round((w[1] + w[3]) / 2 / 3), w[0]))
    ov = sum(1 for a, b in zip(ws, ws[1:]) if abs((a[1] + a[3]) - (b[1] + b[3])) < 4 and b[0] < a[2] - 1.5)
    if ov > 12 and ov > 0.05 * len(ws):
        return _words_from_chars(page)
    return out

def page_lines(page, ytol=3.0, words=None):
    """group words into visual lines (display orientation). returns list of dict(y0,y1,x0,words=[(x0,x1,text)])"""
    ws = words if words is not None else page_words(page)
    ws = sorted(ws, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    lines = []
    for w in ws:
        yc = (w[1] + w[3]) / 2
        if lines and abs(lines[-1]["yc"] - yc) <= ytol:
            L = lines[-1]
            L["words"].append((w[0], w[2], w[4]))
            L["y0"] = min(L["y0"], w[1]); L["y1"] = max(L["y1"], w[3])
        else:
            lines.append({"yc": yc, "y0": w[1], "y1": w[3], "words": [(w[0], w[2], w[4])]})
    for L in lines:
        L["words"].sort()
        L["x0"] = L["words"][0][0]
        L["text"] = " ".join(t for _, _, t in L["words"])
    return lines

def render(fn, pno, clip=None, zoom=1.6, out=None):
    """render page pno (0-based) of fn without the colour-inversion wrapper. clip = (x0,y0,x1,y1) in DISPLAY coords."""
    d = opendoc(fn, clean=True)
    p = d[pno]
    mat = fitz.Matrix(zoom, zoom)
    if clip:
        r = fitz.Rect(clip) * ~p.rotation_matrix
        r.normalize()
        pix = p.get_pixmap(matrix=mat, clip=r)
    else:
        pix = p.get_pixmap(matrix=mat)
    out = out or os.path.join(IMG, "%s_p%d.png" % (fn.replace(".pdf", ""), pno + 1))
    pix.save(out)
    return out
