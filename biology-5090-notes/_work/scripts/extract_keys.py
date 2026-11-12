"""Independent re-extraction of every Paper 1 answer key from the official key source and comparison with decisions.json."""
import sys, os, re, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
def keys_from(fn, pages=None):
    doc = opendoc(fn); found = collections.OrderedDict(); dup = []
    rng = range(len(doc)) if not pages else range(pages[0] - 1, pages[1])
    for pno in rng:
        page = doc[pno]
        for ln in page_lines(page, 3, page_words(page)):
            txt = ln if isinstance(ln, str) else (ln.get("text") if isinstance(ln, dict) else " ".join(w[4] for w in ln))
            for m in re.finditer(r"(?<![\w.])(\d{1,2})\s+([ABCD])(?![\w/])", txt):
                q = int(m.group(1))
                if 1 <= q <= 40:
                    if q in found:
                        if found[q] != m.group(2): dup.append((q, found[q], m.group(2), pno + 1))
                    else: found[q] = m.group(2)
    return found, dup
if __name__ == "__main__":
    dec = load_dec(); res = {}; bad = 0; total = 0
    for p in load_pairs():
        if p["paper"] != 1: continue
        k, dup = keys_from(p["ms"], p.get("ms_pages") if p["ms"].endswith("er.pdf") or "s04_ms" in p["ms"] else None)
        miss = [q for q in range(1, 41) if q not in k]
        diff = [(q, dec["%s:%d" % (p["id"], q)]["key"], k.get(q)) for q in range(1, 41) if k.get(q) != dec["%s:%d" % (p["id"], q)]["key"]]
        total += 40 - len(diff)
        res[p["id"]] = {"keys": {str(q): v for q, v in k.items()}, "missing": miss, "dup": dup, "diff": diff}
        if miss or dup or diff:
            bad += 1; print(p["id"], p["ms"], "missing", miss, "dup", dup[:6], "diff", diff[:8])
    jsave("data/p1_keys_reextracted.json", res)
    print("papers", len(res), "papers with any difference", bad, "keys agreeing", total, "of", 40 * len(res))
