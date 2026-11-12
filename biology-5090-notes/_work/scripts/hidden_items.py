"""For Paper 1 items with fig status 'viewed' on pages with hidden content: how much of the item's ink was invisible with the old renderer."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from state import *
from PIL import Image, ImageChops
res = jload("state/hidden_regions.json")
its = load_items(); d = load_dec(); P = {p["id"]: p for p in load_pairs()}
Z = 1.0; cache = {}
def pages(fn, pn):
    k = (fn, pn)
    if k not in cache:
        if fn not in cache:
            cache[fn] = (opendoc(fn, clean="old"), opendoc(fn, clean=True))
        a, b = cache[fn]
        pa = a[pn].get_pixmap(matrix=fitz.Matrix(Z, Z), alpha=False); pb = b[pn].get_pixmap(matrix=fitz.Matrix(Z, Z), alpha=False)
        cache[k] = (Image.frombytes("RGB", (pa.width, pa.height), pa.samples).convert("L"), Image.frombytes("RGB", (pb.width, pb.height), pb.samples).convert("L"))
    return cache[k]
out = []
which = sys.argv[1] if len(sys.argv) > 1 else "viewed"
for i in order():
    it = its[i]
    if it["paper"] != 1: continue
    if which == "viewed" and d[i].get("fig") != "viewed": continue
    if which == "ver" and d[i]["status"] != "ver": continue
    p = P[it["pair"]]; h = res.get(p["qp"], {})
    if str(it["page"]) not in h: continue
    ia, ib = pages(p["qp"], it["page"] - 1)
    y0 = int(max(0, (it["y0"] or 0) - 4)); y1 = int(min(ib.height, (it["y1"] or ib.height) + 2))
    ca = ia.crop((0, y0, ia.width, y1)); cb = ib.crop((0, y0, ib.width, y1))
    ink_new = sum(1 for v in cb.getdata() if v < 128)
    ink_old = sum(1 for v in ca.getdata() if v < 128)
    hid = ink_new - ink_old
    out.append((i, d[i]["status"], d[i].get("fig"), d[i]["sec"], it["page"], ink_new, hid, round(100.0 * hid / max(1, ink_new))))
jsave("state/hidden_items_%s.json" % which, out)
part = [o for o in out if o[7] >= 3]
print("items on affected pages:", len(out), "| with >=3% of their ink hidden:", len(part))
for o in part: print(o)
