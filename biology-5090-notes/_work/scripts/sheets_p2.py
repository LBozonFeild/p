"""Contact sheets of question-paper pages for Paper 2 figure-dependent parts (corrected renderer).
   sheets_p2.py [zoom=0.9] [per=3]  -> /home/user/img/p2s_NN.png + state/p2_sheets_index.txt"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from state import *
from PIL import Image, ImageDraw
kw = dict(a.split("=") for a in sys.argv[1:] if "=" in a)
Z = float(kw.get("zoom", 0.9)); PER = int(kw.get("per", 3))
its = load_items(); d = load_dec(); P = {p["id"]: p for p in load_pairs()}
rows = [r for r in jload("state/p2_fig_candidates.json") if d[r[0]]["fig"] != "viewed" and d[r[0]]["status"] == "ver"]
extra = json.loads(kw["extra"]) if "extra" in kw else []
pages = {}
ordr = {i: n for n, i in enumerate(order())}
for r in rows:
    it = its[r[0]]; pg = (it.get("pages") or [None])[0]
    if pg is None: continue
    pages.setdefault((it["pair"], pg), []).append(r[0])
keys = sorted(pages, key=lambda k: min(ordr[i] for i in pages[k]))
docs = {}
def clean(ms):
    out = []
    for l in ms.split("\n"):
        if l.startswith("<<MS"): continue
        l = re.sub(r"(Question\s+Answer\s+Marks?\s+Guidance|Page \d+ Mark Scheme.*|Trace ID:.*|Licensed for hosting.*|Re-uploading.*)", "", l).strip()
        if l: out.append(re.sub(r"\s{2,}", " ", l))
    return " | ".join(out)
idx = []; n = 0
for k in range(0, len(keys), PER):
    grp = keys[k:k + PER]; ims = []
    n += 1
    idx.append("=== sheet %02d" % n)
    for (pair, pg) in grp:
        p = P[pair]
        if p["qp"] not in docs: docs[p["qp"]] = opendoc(p["qp"], clean=True)
        page = docs[p["qp"]][pg - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(Z, Z), alpha=False)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        if page.rect.width > page.rect.height: im = im.resize((int(im.width * 0.75), int(im.height * 0.75)))
        lab = Image.new("RGB", (im.width, 16), (225, 235, 255)); ImageDraw.Draw(lab).text((4, 2), "%s  page %d" % (pair, pg), fill=(0, 0, 120))
        c = Image.new("RGB", (im.width, im.height + 16), "white"); c.paste(lab, (0, 0)); c.paste(im, (0, 16)); ims.append(c)
        for i in pages[(pair, pg)]:
            q = re.sub(r"\s+", " ", its[i]["qtext"])[-90:]
            idx.append("  %s p%d [%s] ..%s => %s" % (i, pg, d[i]["sec"], q, clean(its[i]["ms_text"])[:330]))
    Wd = sum(c.width for c in ims) + 6 * (len(ims) - 1); Hd = max(c.height for c in ims)
    sh = Image.new("RGB", (Wd, Hd), (150, 150, 150)); x = 0
    for c in ims: sh.paste(c, (x, 0)); x += c.width + 6
    sh.save(os.path.join(IMG, "p2s_%02d.png" % n))
open(os.path.join(W, "state", "p2_sheets_index.txt"), "w").write("\n".join(idx) + "\n")
print("pages", len(keys), "sheets", n)
