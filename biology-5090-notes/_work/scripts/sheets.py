"""Contact sheets of Paper 1 items (corrected renderer): sheets.py <json list of ids | 'hidden'> [zoom=1.2] [maxh=1480] -> /home/user/img/sheet_NN.png"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from state import *
from PIL import Image, ImageDraw
kw = dict(a.split("=") for a in sys.argv[2:] if "=" in a)
Z = float(kw.get("zoom", 1.2)); MAXH = int(kw.get("maxh", 1480)); prefix = kw.get("prefix", "sheet")
if sys.argv[1] == "hidden":
    ids = [o[0] for o in jload("state/hidden_items_viewed.json") if o[7] >= 3]
else:
    ids = json.loads(sys.argv[1])
its = load_items(); d = load_dec(); P = {p["id"]: p for p in load_pairs()}
docs = {}
crops = []
for i in ids:
    it = its[i]; p = P[it["pair"]]
    if p["qp"] not in docs: docs[p["qp"]] = opendoc(p["qp"], clean=True)
    pg = docs[p["qp"]][it["page"] - 1]; r = pg.rect
    y0 = max(0, (it["y0"] or 0) - 5); y1 = min(r.height, (it["y1"] or r.height) + 3)
    if y1 > 800: y1 = 800
    pix = pg.get_pixmap(matrix=fitz.Matrix(Z, Z), clip=fitz.Rect(40, y0, 562, y1), alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # trim trailing white rows
    bb = Image.eval(im.convert("L"), lambda v: 255 if v < 200 else 0).getbbox()
    if bb: im = im.crop((0, 0, im.width, min(im.height, bb[3] + 6)))
    lab = Image.new("RGB", (im.width, 20), (225, 235, 255)); ImageDraw.Draw(lab).text((4, 4), "%s   KEY %s   [%s]" % (i, it["key"], d[i]["sec"]), fill=(0, 0, 120))
    c = Image.new("RGB", (im.width, im.height + 22), "white"); c.paste(lab, (0, 0)); c.paste(im, (0, 22))
    crops.append((i, c))
sheets = []; cols = [[]]; h = 0
for i, c in crops:
    if h + c.height > MAXH and cols[-1]:
        cols.append([]); h = 0
    cols[-1].append(c); h += c.height
n = 0
for k in range(0, len(cols), 2):
    pair = cols[k:k + 2]
    Wd = sum(max(c.width for c in col) for col in pair) + 10 * (len(pair) - 1)
    Hd = max(sum(c.height for c in col) for col in pair)
    sh = Image.new("RGB", (Wd, Hd), (160, 160, 160)); x = 0
    for col in pair:
        y = 0
        for c in col:
            sh.paste(c, (x, y)); y += c.height
        x += max(c.width for c in col) + 10
    n += 1; fn = os.path.join(IMG, "%s_%02d.png" % (prefix, n)); sh.save(fn); sheets.append((fn, sh.size))
for s in sheets: print(s)
