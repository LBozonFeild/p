# Paper 2 mark schemes: cut every mark scheme into labelled sections (1(a)(i), 8E(b) ...), guided by the label list that the
# first verification pass recorded in the tracker. Table-format schemes (2013 onwards) are read row by row using the ruled
# lines of the table; older schemes are read line by line.
from state import *
ROM = "i|ii|iii|iv|v|vi"
T_NUM = re.compile(r"^(\d{1,2})$")
T_LET = re.compile(r"^\(([a-h])\)$")
T_ROM = re.compile(r"^\((%s)\)$" % ROM)
T_COMB = re.compile(r"^(\d{1,2})([EO])?(?:\(?([a-h])\)?)?(?:\((%s)\))?$" % ROM)
T_LETROM = re.compile(r"^\(([a-h])\)\((%s)\)$" % ROM)
T_EO = re.compile(r"^(either|or|e|o)$", re.I)

def rulings(page):
    m = page.rotation_matrix
    V = {}; H = {}
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "re":
                r = fitz.Rect(it[1]) * m; r.normalize()
                if r.width < 2.5 and r.height > 8: V.setdefault(round(r.x0), []).append((r.y0, r.y1))
                elif r.height < 2.5 and r.width > 30: H.setdefault(round(r.y0), []).append((r.x0, r.x1))
                elif dr.get("type") in ("s", "fs") and r.width > 30 and r.height > 8:
                    # a stroked cell rectangle: use its four edges
                    V.setdefault(round(r.x0), []).append((r.y0, r.y1)); V.setdefault(round(r.x1), []).append((r.y0, r.y1))
                    H.setdefault(round(r.y0), []).append((r.x0, r.x1)); H.setdefault(round(r.y1), []).append((r.x0, r.x1))
            elif it[0] == "l":
                a = fitz.Point(it[1]) * m; b = fitz.Point(it[2]) * m
                if abs(a.x - b.x) < 1 and abs(a.y - b.y) > 8: V.setdefault(round(a.x), []).append((min(a.y, b.y), max(a.y, b.y)))
                elif abs(a.y - b.y) < 1 and abs(a.x - b.x) > 30: H.setdefault(round(a.y), []).append((min(a.x, b.x), max(a.x, b.x)))
    def merge(D, tol=2, vert=False):
        ks = sorted(D); out = []
        for k in ks:
            tot = sum(b - a for a, b in D[k] if not (vert and b < 72))   # ignore the page-header box at the top
            if out and k - out[-1][0] <= tol:
                out[-1] = (out[-1][0], out[-1][1] + tot)
            else:
                out.append((k, tot))
        return out
    return merge(V, vert=True), merge(H)

def parse_label_tokens(tokens):
    """tokens: list of strings (leading label-like tokens). returns (q, eo, a, r, nconsumed)"""
    q = eo = a = r = None; n = 0
    i = 0
    if i < len(tokens):
        t = tokens[i]
        m = T_COMB.match(t)
        if m and (m.group(3) or m.group(4)):
            q = int(m.group(1)); eo = m.group(2); a = m.group(3); r = m.group(4); i += 1
            return q, eo, a, r, i
        mne = re.match(r"^(\d{1,2})([EO])$", t)
        if mne:
            q = int(mne.group(1)); eo = mne.group(2); i += 1
        elif T_NUM.match(t):
            q = int(t); i += 1
            if i < len(tokens) and T_EO.match(tokens[i]):
                eo = tokens[i][0].upper(); i += 1
    if i < len(tokens):
        m = T_LETROM.match(tokens[i])
        if m:
            a, r = m.group(1), m.group(2); i += 1
            return q, eo, a, r, i
    if i < len(tokens) and T_LET.match(tokens[i]) and not (tokens[i] == "(i)"):
        a = T_LET.match(tokens[i]).group(1); i += 1
    if i < len(tokens) and T_ROM.match(tokens[i]):
        r = T_ROM.match(tokens[i]).group(1); i += 1
    return q, eo, a, r, i

def lab(q, eo, a, r):
    return "%s%s%s%s" % (q, eo or "", "(%s)" % a if a else "", "(%s)" % r if r else "")

class Guided:
    def __init__(self, expected):
        self.exp = expected; self.pos = {l: i for i, l in enumerate(expected)}
        self.cur = (None, None, None, None); self.idx = -1; self.label = None
        self.sections = {l: [] for l in expected}; self.pages = {}
        self.rejected = []; self.pre = []; self.notes = []
    def offer(self, q, eo, a, r, where):
        """returns True if a label change/continuation was accepted"""
        cq, ceo, ca, cr = self.cur
        if q is not None:
            new = (q, eo, a, r)
        elif a is not None:
            new = (cq, ceo, a, r)
        elif r is not None:
            new = (cq, ceo, ca, r)
        else:
            return False
        if new[0] is None: return False
        cands = [new]
        # an E/O question whose alternative marker was not printed on this line
        if new[1] is None:
            cands = ([(new[0], ceo, new[2], new[3])] if (ceo and new[0] == cq) else []) + [new, (new[0], "E", new[2], new[3]), (new[0], "O", new[2], new[3])]
        for c in cands:
            l = lab(*c)
            if l in self.pos and self.pos[l] >= self.idx and self.pos[l] - self.idx <= 8:
                self.cur = c; self.idx = self.pos[l]; self.label = l
                self.pages.setdefault(l, where)
                return True
        # prefix of a later expected label (e.g. "(b)" printed on its own line before "(i)")
        for c in cands:
            l = lab(*c)
            for i in range(max(self.idx, 0), min(len(self.exp), self.idx + 9)):
                if self.exp[i].startswith(l + "(") or (c[1] is None and re.match(r"^%d[EO]" % c[0], self.exp[i]) and c[2] is None):
                    if i > self.idx:
                        cc = c
                        if c[1] is None and re.match(r"^%d([EO])" % c[0], self.exp[i]) and c[2] is None and not self.exp[i].startswith(l + "("):
                            cc = (c[0], None, None, None)
                        self.cur = cc; self.idx = i; self.label = self.exp[i]
                        self.pages.setdefault(self.exp[i], where)
                        return True
                    elif i == self.idx:
                        self.cur = c; return True
        # question number not printed on a new question's first row: "(a)" seen while expecting N+1(a)
        if q is None and a is not None and self.idx + 1 < len(self.exp) and cq is not None:
            for eo2 in (None, "E", "O"):
                c = (cq + 1, eo2, a, r)
                if lab(*c) == self.exp[self.idx + 1]:
                    self.cur = c; self.idx += 1; self.label = lab(*c)
                    self.pages.setdefault(self.label, where)
                    self.notes.append("question number %d not printed in the mark scheme (p.%s); label inferred from sequence" % (cq + 1, where))
                    return True
        self.rejected.append((lab(*new), where))
        return False
    def add(self, line):
        if self.label is None: self.pre.append(line)
        else: self.sections[self.label].append(line)

def fmt_line(a, m, g):
    s = a
    if m: s += "  {%s}" % m
    if g: s += "  ‖ " + g
    return s.strip()

SKIP_NT = re.compile(r"(^Page \d+\s+Mark Scheme|Mark Scheme.*Syllabus\s+Paper|GCE O LEVEL|^BIOLOGY\s*[–-]\s*(JUNE|NOVEMBER)|©\s*(UCLES|University of Cambridge|Cambridge International)|Cambridge O Level\s*[–-]|^Syllabus\s+Paper)", re.I)

def parse_ms(fn, expected, pages=None, year=None):
    import collections
    from itertools import groupby
    d = opendoc(fn)
    G = Guided(expected)
    info = {"table_pages": 0, "plain_pages": 0, "warn": []}
    marks = {}
    rng = range(len(d)) if not pages else range(pages[0] - 1, pages[1])
    HDR = lambda lines: [L for L in lines if re.match(r"^\s*Question\b", L["text"]) and re.search(r"Answer|Mark Scheme|Expected|Mark", L["text"])]
    cache = {}
    for pno in rng:
        p = d[pno]
        lines = page_lines(p)
        V, H = rulings(p)
        cache[pno] = (lines, V, H, HDR(lines), sorted(x for x, tot in V if tot > 18))
    ntab = sum(1 for pno in rng if len(cache[pno][4]) >= 4)
    nhdr = sum(1 for pno in rng if len(cache[pno][4]) >= 4 and cache[pno][3])
    table_doc = ntab >= 3
    need_hdr = table_doc and (year or 0) >= 2017      # 2017+ schemes repeat the header row on every answer page; earlier ones do not
    # label columns of plain-format schemes
    cn = collections.Counter(); cl = collections.Counter()
    if not table_doc:
        for pno in rng:
            for L in cache[pno][0]:
                ws = L["words"]
                if len(ws) >= 2 and re.match(r"^\d{1,2}[EO]?$", ws[0][2]) and (T_LET.match(ws[1][2]) or T_EO.match(ws[1][2])):
                    cn[round(ws[0][0])] += 1
                    if T_LET.match(ws[1][2]): cl[round(ws[1][0])] += 1
                elif T_LET.match(ws[0][2]) and ws[0][2] != "(i)":
                    cl[round(ws[0][0])] += 1
    numx = cn.most_common(1)[0][0] if cn else None
    letx = cl.most_common(1)[0][0] if cl else None
    info["numx"] = numx; info["letx"] = letx; info["table_doc"] = table_doc
    roles_prev = None
    def addmarks(cols):
        if G.label:
            for t in cols["M"]:
                mm = re.match(r"^\[?(\d{1,2})\]?$", t)
                if mm: marks[G.label] = marks.get(G.label, 0) + int(mm.group(1))
    for pno in rng:
        lines, V, H, hdr, Vl = cache[pno]
        if table_doc:
            if len(Vl) < 4 or (need_hdr and not hdr):
                continue
            if hdr and re.search(r"Modification", hdr[0]["text"]):
                info["warn"].append("p%d appendix (modified-paper guidance) skipped" % (pno + 1)); continue
            info["table_pages"] += 1
            bounds = Vl
            ncol = len(bounds) - 1
            def col(xc):
                for i in range(ncol):
                    if bounds[i] - 1 <= xc < bounds[i + 1]: return i
                return 0 if xc < bounds[0] else ncol - 1
            roles = None
            if hdr:
                hl = hdr[0]; roles = {}
                for x0, x1, t in hl["words"]:
                    c = col((x0 + x1) / 2); tl = t.lower()
                    if tl.startswith("question"): roles[c] = "Q"
                    elif tl in ("answer", "answers", "expected", "scheme"): roles[c] = "A"
                    elif tl in ("marks", "mark") and roles.get(c) != "A": roles.setdefault(c, "M")
                    elif tl in ("guidance", "clarification", "additional"): roles[c] = "G"
                if "Q" not in roles.values() or "A" not in roles.values():
                    info["warn"].append("p%d header roles %s" % (pno + 1, roles)); roles = None
            if roles is None:
                if roles_prev and max(roles_prev) < ncol: roles = roles_prev
                else: roles = {0: "Q", 1: "A", 2: "M", 3: "G"}
            roles_prev = roles
            width = bounds[-1] - bounds[0]
            wide = sorted(y for y, tot in H if tot > 0.7 * width)
            if hdr:
                top = hdr[0]["y1"] - 2
            else:
                # first ruling of the table itself (the page-header box is narrower than the table)
                top = (wide[0] - 2) if wide else 60
            body = [L for L in lines if L["y0"] > top and not (hdr and L is hdr[0])]
            body = [L for L in body if not re.search(r"©\s*(UCLES|Cambridge)|^Page \d+ of \d+$", L["text"])]
            edges = [y for y in wide if y > top - 14]
            if len(edges) >= 2:
                rows = [(sum(1 for e in edges if e <= L["yc"]), L) for L in body]
            else:
                info["warn"].append("p%d no horizontal rulings" % (pno + 1))
                rows = [(i, L) for i, L in enumerate(body)]
            for k, grp in groupby(rows, key=lambda x: x[0]):
                grp = [L for _, L in grp]
                recs = []
                for L in grp:
                    cols = {"Q": [], "A": [], "M": [], "G": []}
                    for x0, x1, t in L["words"]:
                        cols[roles.get(col((x0 + x1) / 2), "A")].append(t)
                    recs.append((L, cols))
                rowtext = " ".join(L["text"] for L in grp)
                if re.search(r"\bTotal\b", rowtext) and len(rowtext) < 40:
                    continue
                events = {}
                for i, (L, cols) in enumerate(recs):
                    if cols["Q"]:
                        qs = re.sub(r"[\s()]", "", "".join(cols["Q"]))
                        mq = re.match(r"^(\d{1,2})?([EO])?([a-h])?(vi|iv|v|iii|ii|i)?$", qs)
                        if mq and qs:
                            events[i] = (int(mq.group(1)) if mq.group(1) else None, mq.group(2), mq.group(3), mq.group(4))
                        else: cols["A"] = cols["Q"] + cols["A"]
                if len(events) == 1:
                    G.offer(*list(events.values())[0], where=pno + 1)
                    events = {}
                for i, (L, cols) in enumerate(recs):
                    if i in events:
                        G.offer(*events[i], where=pno + 1)
                    s = fmt_line(" ".join(cols["A"]), " ".join(cols["M"]), " ".join(cols["G"]))
                    if s: G.add(s)
                    addmarks(cols)
        else:
            info["plain_pages"] += 1
            for L in lines:
                t = L["text"]
                if SKIP_NT.search(t) and L["y0"] < 75: continue
                if re.search(r"©\s*(UCLES|University of Cambridge|Cambridge International)", t): continue
                if re.match(r"^\[?\s*Total\b", t.strip(), re.I) and len(t) < 30: continue
                ws = L["words"]
                toks = []
                for x0, x1, w in ws[:4]:
                    if T_NUM.match(w) or T_LET.match(w) or T_ROM.match(w) or T_EO.match(w) or T_COMB.match(w) or T_LETROM.match(w): toks.append(w)
                    else: break
                n = 0
                if toks:
                    x0 = ws[0][0]; t0 = ws[0][2]
                    if re.match(r"^\d", t0):
                        okpos = numx is None or abs(x0 - numx) <= 14
                    elif T_ROM.match(t0):
                        okpos = letx is None or (letx - 10 <= x0 <= letx + 70)
                    elif T_LET.match(t0) or T_LETROM.match(t0):
                        okpos = letx is None or (letx - 12 <= x0 <= letx + 68)
                    else:
                        okpos = False
                    if okpos:
                        q, eo, a, r, n = parse_label_tokens(toks)
                        if n and not G.offer(q, eo, a, r, where=pno + 1):
                            n = 0
                parts = []
                for j in range(n, len(ws)):
                    if j > n and ws[j][0] - ws[j - 1][1] > 22: parts.append("‖")
                    parts.append(ws[j][2])
                s = " ".join(parts)
                if s.strip(): G.add(s.strip())
    return G, info, marks

if __name__ == "__main__":
    pairs = load_pairs(); dec = load_dec(); order_ = order()
    out = {}; rep = []
    only = sys.argv[1:] 
    for p in pairs:
        if p["paper"] != 2: continue
        if only and p["id"] not in only: continue
        ids = [i for i in order_ if i.startswith(p["id"] + ":")]
        expected = []
        for i in ids:
            for l in dec[i]["ms_labels"]:
                if l not in expected: expected.append(l)
        G, info, marks = parse_ms(p["ms"], expected, p.get("ms_pages"), p["year"])
        empty = [l for l in expected if not G.sections[l]]
        # compare ';' counts with the tracker
        diffs = []
        for i in ids:
            txt = "\n".join("\n".join(G.sections[l]) for l in dict.fromkeys(dec[i]["ms_labels"]))
            pts = txt.count(";")
            if pts != dec[i]["old_pts"]:
                diffs.append((i.split(":")[1], dec[i]["old_pts"], pts))
        out[p["id"]] = dict(sections=G.sections, pages=G.pages, marks=marks, pre=G.pre[:0], rejected=G.rejected, info=info)
        rep.append((p["id"], len(expected), len(empty), len(diffs)))
        print(p["id"], "labels", len(expected), "empty", empty[:6], "ptsdiff", len(diffs), diffs[:5], "rej", len(G.rejected), "tbl/plain", info["table_pages"], info["plain_pages"], info["warn"][:3])
    if not only:
        jsave("data/ms2_sections.json", out)
    print("papers", len(rep), "labels", sum(r[1] for r in rep), "empty", sum(r[2] for r in rep), "ptsdiff items", sum(r[3] for r in rep))
