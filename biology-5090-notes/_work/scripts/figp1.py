"""Render the question-paper region of Paper 1 items: figp1.py <id...> [zoom=1.3] -> /home/user/img/<id>.png"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
from lib import *
kw = dict(a.split("=") for a in sys.argv[1:] if "=" in a and ":" not in a.split("=")[0])
ids = [a for a in sys.argv[1:] if ":" in a]
its = load_items(); P = {p["id"]: p for p in load_pairs()}
for i in ids:
    it = its[i]; p = P[it["pair"]]
    doc = opendoc(p["qp"], clean=True); pg = doc[it["page"] - 1]
    r = pg.rect
    y0 = max(0, (it["y0"] or 0) - 6); y1 = min(r.height, (it["y1"] or r.height) + 4)
    out = os.path.join(IMG, i.replace(":", "_") + ".png")
    render(p["qp"], it["page"] - 1, (0, y0, r.width, y1), float(kw.get("zoom", 1.3)), out)
    print(out, "page", it["page"], "key", it["key"], "pages", it.get("pages"))
