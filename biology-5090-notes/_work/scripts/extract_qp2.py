# Paper 2 question papers: split the running text at every printed mark allocation "[n]".
# Segment k (text between the (k-1)th and kth mark allocation) = question text of the kth mark-bearing part.
from state import *
HEADFOOT = re.compile(r"(©\s*UCLES|UCLES \d{4}|5090/\d+/[A-Z]/[A-Z]/\d+|\[Turn over|BLANK PAGE|Permission to reproduce|reasonable effort has been made|publisher will be pleased|is part of the Cambridge Assessment|Cambridge Local Examinations Syndicate|Cambridge Assessment International Education|To avoid the issue of disclosure|Cambridge International Examinations is part|Copyright Acknowledgements Booklet|is freely available to download|answer-related information)", re.I)
MARK = re.compile(r"^[.…·\s]*\[(\d{1,2})\]$")
TOTAL = re.compile(r"\[\s*Total\s*:?\s*(\d{1,2})\s*\]", re.I)
MARGIN = {"For", "Examiner’s", "Examiner's", "Use", "Examiner’s", "For Examiner’s", "Examiner’s Use"}
def qp_lines(fn):
    d = opendoc(fn)
    out = []
    for pno in range(1, len(d)):   # page 1 = cover
        p = d[pno]
        ws = [w for w in page_words(p) if not (w[4] in MARGIN and (w[0] > 515 or w[2] < 50))]
        for L in page_lines(p, words=ws):
            t = L["text"]
            if L["y0"] < 52 and re.match(r"^\d{1,2}$", t.strip()):   # page number
                continue
            if HEADFOOT.search(t):
                continue
            out.append((pno + 1, L))
    return out

def split_qp(fn):
    segs = []
    cur = []; curpages = set(); since_total = 0
    for pno, L in qp_lines(fn):
        ws = L["words"]
        idx = [i for i, (a, b, t) in enumerate(ws) if MARK.match(t)]
        hit = None; how = "printed"
        low = L["text"]
        mt = TOTAL.search(low)
        if mt:
            if since_total == 0 and cur:
                hit = int(mt.group(1)); how = "total-only"
            since_total = 0
            txt_words = []
            if hit is None:
                continue
        elif idx:
            i = idx[-1]
            hit = int(MARK.match(ws[i][2]).group(1))
            txt_words = [t for j, (a, b, t) in enumerate(ws) if j != i]
            since_total += 1
        else:
            txt_words = [t for a, b, t in ws]
        t = " ".join(txt_words)
        t = re.sub(r"[.…]{4,}", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            cur.append(t); curpages.add(pno)
        if hit is not None:
            curpages.add(pno)
            segs.append(dict(marks=hit, text="\n".join(cur), pages=sorted(curpages), end_page=pno, end_y=round(L["y1"]), how=how))
            cur = []; curpages = set()
    return segs, "\n".join(cur)

def align(want, segs):
    """min-cost alignment of wanted marks (tracker) onto printed allocations. Each wanted item takes 1 segment (equal marks),
    2-4 segments (marks sum) or 0 segments (allocation not printed)."""
    INF = 10 ** 9
    n, m = len(want), len(segs)
    best = [[INF] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    best[0][0] = 0
    for k in range(n):
        for j in range(m + 1):
            c = best[k][j]
            if c >= INF: continue
            # 0 segments
            if c + 5 < best[k + 1][j]:
                best[k + 1][j] = c + 5; back[k + 1][j] = (j, 0)
            s = 0
            for t in range(1, 5):
                if j + t > m: break
                s += segs[j + t - 1]["marks"]
                if s == want[k]:
                    cc = c + (0 if t == 1 else 1 + t)
                    if cc < best[k + 1][j + t]:
                        best[k + 1][j + t] = cc; back[k + 1][j + t] = (j, t)
    if best[n][m] >= INF:
        return None
    out = [None] * n
    j = m
    for k in range(n, 0, -1):
        pj, t = back[k][j]
        out[k - 1] = (pj, t)
        j = pj
    return out

if __name__ == "__main__":
    pairs = load_pairs(); dec = load_dec(); order_ = order()
    res = {}; nspecial = 0
    for p in pairs:
        if p["paper"] != 2: continue
        ids = [i for i in order_ if i.startswith(p["id"] + ":")]
        want = [dec[i]["marks"] for i in ids]
        segs, tail = split_qp(p["qp"])
        al = align(want, segs)
        if al is None:
            print("ALIGN FAILED", p["id"], want, [s["marks"] for s in segs]); continue
        items = {}
        for k, (j, t) in enumerate(al):
            if t == 1:
                s = segs[j]; items[ids[k]] = dict(text=s["text"], pages=s["pages"], end_page=s["end_page"], end_y=s["end_y"], how=("1:1" if s["how"] == "printed" else "marks from [Total] line"))
            elif t > 1:
                ss = segs[j:j + t]
                items[ids[k]] = dict(text="\n".join(s["text"] + " [%d]" % s["marks"] for s in ss), pages=sorted(set(sum((s["pages"] for s in ss), []))),
                                     end_page=ss[-1]["end_page"], end_y=ss[-1]["end_y"], how="sum of %d printed allocations" % t)
            else:
                nx = segs[j]["text"] if j < len(segs) else tail
                items[ids[k]] = dict(text="[allocation not printed separately in the QP; text shared with the following part]\n" + nx, pages=(segs[j]["pages"] if j < len(segs) else []),
                                     end_page=None, end_y=None, how="no printed allocation")
            if items[ids[k]]["how"] != "1:1":
                nspecial += 1; print("  special", ids[k], want[k], items[ids[k]]["how"])
        res[p["id"]] = items
    jsave("data/qp2_items.json", res)
    print("papers", len(res), "items", sum(len(v) for v in res.values()), "special", nspecial)
