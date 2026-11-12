# Combine the extracted question papers and mark schemes into one item table (data/items.json).
from state import *
pairs = load_pairs(); dec = load_dec(); order_ = order()
Q1 = jload("data/qp1_items.json"); Q2 = jload("data/qp2_items.json"); M = jload("data/ms2_sections.json")
P = {p["id"]: p for p in pairs}
items = {}
for iid in order_:
    pid, lab = iid.split(":")
    d = dec[iid]; p = P[pid]
    if p["paper"] == 1:
        q = Q1[pid][int(lab) - 1]
        assert q["n"] == int(lab)
        items[iid] = dict(paper=1, pair=pid, n=int(lab), text=q["text"], key=d["key"], page=q["page"], y0=q["y0"], y1=q["y1"], pages=q["pages"])
    else:
        q = Q2[pid][iid]
        labs = list(dict.fromkeys(d["ms_labels"]))
        secs = M[pid]["sections"]
        ms = "\n".join(("<<MS %s>>\n" % l) + "\n".join(secs[l]) for l in labs)
        items[iid] = dict(paper=2, pair=pid, label=lab, marks=d["marks"], qtext=q["text"], pages=q["pages"], how=q["how"],
                          ms_labels=labs, ms_text=ms, ms_page=d["ms_page"], ms_pages=sorted(set(M[pid]["pages"].get(l, d["ms_page"]) for l in labs)),
                          pts=ms.count(";"))
# context for Paper 2 parts: stem of the main question and of the lettered part
byq = {}
for iid, it in items.items():
    if it["paper"] == 2:
        m = re.match(r"^(\d+[EO]?)(\([a-h]\))?", it["label"])
        it["_q"] = m.group(1); it["_l"] = m.group(2) or ""
        byq.setdefault((it["pair"], it["_q"]), []).append(iid)
for (pid, q), ids in byq.items():
    first = items[ids[0]]
    for iid in ids:
        it = items[iid]
        ctx = []
        if iid != ids[0]:
            t = first["qtext"]
            mm = re.search(r"(?m)^\(a\)", t)
            ctx.append(t[:mm.start()] if mm and mm.start() > 40 else t[:900])
            same = [j for j in ids if items[j]["_l"] == it["_l"]]
            if same and same[0] != iid and same[0] != ids[0]:
                ctx.append(items[same[0]]["qtext"][:600])
        it["context"] = "\n...\n".join(c.strip() for c in ctx if c.strip())
for it in items.values():
    it.pop("_q", None); it.pop("_l", None)
jsave("data/items.json", items)
print("items", len(items), "P1", sum(i["paper"] == 1 for i in items.values()), "P2", sum(i["paper"] == 2 for i in items.values()))
import os
print("size MB", round(os.path.getsize(os.path.join(W, "data/items.json")) / 1e6, 2))
