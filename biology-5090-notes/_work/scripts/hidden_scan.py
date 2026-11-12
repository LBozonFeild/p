"""Find page regions that were invisible with the first version of the clean renderer (wrapper base stream kept).
Writes state/hidden_regions.json: {file: {page_no(1-based): [x0,y0,x1,y1] in page points}}"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from state import *
from PIL import Image, ImageChops
import io
Z = 0.4
files = set()
for p in load_pairs():
    files.add(p["qp"]); files.add(p["ms"])
res = jload("state/hidden_regions.json", {}) or {}
for fn in sorted(files):
    if fn in res: continue
    a = opendoc(fn, clean="old"); b = opendoc(fn, clean=True)
    out = {}
    for i in range(len(a)):
        pa = a[i].get_pixmap(matrix=fitz.Matrix(Z, Z), alpha=False); pb = b[i].get_pixmap(matrix=fitz.Matrix(Z, Z), alpha=False)
        ia = Image.frombytes("RGB", (pa.width, pa.height), pa.samples).convert("L"); ib = Image.frombytes("RGB", (pb.width, pb.height), pb.samples).convert("L")
        diff = ImageChops.difference(ia, ib).point(lambda v: 255 if v > 60 else 0)
        bb = diff.getbbox()
        if bb:
            out[str(i + 1)] = [round(v / Z, 1) for v in bb]
    res[fn] = out
    jsave("state/hidden_regions.json", res)
n = sum(len(v) for v in res.values())
print("files", len(res), "files with hidden content", sum(1 for v in res.values() if v), "pages with hidden content", n)
