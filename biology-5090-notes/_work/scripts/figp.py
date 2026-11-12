"""render the question-paper page(s) relevant to a Paper 2 item: figp.py <id> [page=N] [zoom=1.1] [clip=x0,y0,x1,y1]"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
from lib import *
def main():
    ids = [a for a in sys.argv[1:] if "=" not in a]; kw = dict(a.split("=") for a in sys.argv[1:] if "=" in a)
    its = load_items(); P = {p["id"]: p for p in load_pairs()}
    for i in ids:
        it = its[i]; pid, lab = i.split(":"); p = P[pid]
        qn = re.match(r"\d+", lab).group(0)
        pgs = sorted({pg for j, x in its.items() if j.startswith(pid + ":") and re.match(r"\d+", j.split(":")[1]).group(0) == qn for pg in (x.get("pages") or [])})
        print(i, "part pages", it.get("pages"), "question pages", pgs)
        want = [int(kw["page"])] if "page" in kw else (it.get("pages") or pgs)[:1]
        for pg in want:
            clip = tuple(float(v) for v in kw["clip"].split(",")) if "clip" in kw else None
            out = os.path.join(IMG, "%s_p%d.png" % (re.sub(r"[^A-Za-z0-9]+", "_", i).strip("_"), pg))
            print(render(p["qp"], pg - 1, clip, float(kw.get("zoom", 1.1)), out))
main()
