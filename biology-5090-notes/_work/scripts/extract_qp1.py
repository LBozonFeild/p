# Paper 1 question papers: locate questions 1-40 (number printed at the left margin) and keep text, page and vertical extent.
from state import *
import collections
FOOT = re.compile(r"(©\s*UCLES|UCLES \d{4}|5090/\d+/[A-Z]/[A-Z]/\d+|\[Turn over|BLANK PAGE|Permission to reproduce|reasonable effort has been made|publisher will be pleased|is part of the Cambridge Assessment|Cambridge Local Examinations Syndicate|To avoid the issue of disclosure|Copyright Acknowledgements|is freely available to download|Cambridge Assessment International Education|University of Cambridge International Examinations is part)", re.I)
def parse_qp1(fn, nq=40):
    d = opendoc(fn)
    pages = []
    cx = collections.Counter()
    for pno in range(1, len(d)):
        lines = [L for L in page_lines(d[pno]) if not FOOT.search(L["text"]) and not (L["y0"] < 52 and re.match(r"^\d{1,2}$", L["text"].strip()))]
        pages.append((pno, lines))
        for L in lines:
            if re.match(r"^\d{1,2}$", L["words"][0][2]) and len(L["words"]) > 1:
                cx[round(L["words"][0][0])] += 1
    margin = min(x for x, c in cx.items() if c >= 3) if cx else 50
    qs = []; n = 1; cur = None
    for pno, lines in pages:
        H = d[pno].rect.height
        for L in lines:
            w0 = L["words"][0]
            if n <= nq and w0[2] == str(n) and abs(w0[0] - margin) <= 6:
                if cur: 
                    if cur["page"] == pno + 1: cur["y1"] = L["y0"] - 2
                    qs.append(cur)
                cur = dict(n=n, page=pno + 1, y0=L["y0"] - 3, y1=None, lines=[" ".join(t for _, _, t in L["words"][1:])], pages=[pno + 1])
                n += 1
            elif cur is not None:
                if pno + 1 not in cur["pages"]: cur["pages"].append(pno + 1)
                cur["lines"].append(L["text"])
    if cur: qs.append(cur)
    for q in qs:
        q["text"] = "\n".join(q["lines"]); del q["lines"]
    return qs, margin

if __name__ == "__main__":
    pairs = load_pairs(); res = {}; bad = 0
    for p in pairs:
        if p["paper"] != 1: continue
        qs, margin = parse_qp1(p["qp"])
        if len(qs) != 40:
            bad += 1; print("PROBLEM", p["id"], len(qs), "margin", margin, "last", qs[-1]["n"] if qs else None)
        res[p["id"]] = qs
    jsave("data/qp1_items.json", res)
    print("papers", len(res), "questions", sum(len(v) for v in res.values()), "problem papers", bad)
