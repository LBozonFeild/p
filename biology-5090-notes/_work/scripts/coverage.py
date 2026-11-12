"""Lexical coverage check: every marking point of every verified Paper 2 item against the notes of the item's OWN subsection(s).
usage: coverage.py [thr=0.6] [budget=14000] [only=fully|mixed] [skip=N] [list=1]"""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
STOP = set("""a an the of to in on at by for with from and or but not no nor is are was were be been being as it its this that these those which who whom whose what when where why how
than then so if into out up down over under about between through during before after above below more most less least much many few some any all each every either neither both other another such
only also very can could may might must shall should will would do does did done has have had having there their they them he she his her you your we our i
ref reference references aw ora accept allow ignore reject max marks mark mp point points answer answers named name correct correctly idea credit award awarded once anywhere eg e.g ie i.e etc
one two three four five six seven eight nine ten first second third must need needed required require requires given give gives use used using uses e g
question guidance total page scheme syllabus paper cambridge level description described describe stated state unless qualified qualification context response
r a i ig""".split())
def stem(w):
    for suf in ("ations", "ation", "ising", "ised", "izing", "ized", "ings", "ing", "ies", "ied", "ed", "es", "ly", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[:-len(suf)]; break
    return w
def words(t):
    return [stem(w) for w in re.findall(r"[a-z][a-z0-9]+", t.lower()) if w not in STOP and len(w) > 2]
def points(ms):
    out = []
    for blk in ms.split("\n"):
        if blk.startswith("<<MS"): continue
        blk = blk.split("‖")[0]
        blk = re.sub(r"\{[^}]*\}", " ", blk)
        out.append(blk)
    txt = " ".join(out)
    return [p.strip() for p in txt.split(";") if len(words(p)) >= 1]
if __name__ == "__main__":
    kw = dict(a.split("=") for a in sys.argv[1:] if "=" in a)
    thr = float(kw.get("thr", 0.6)); lo = float(kw.get("lo", -1)); budget = int(kw.get("budget", 14000)); skip = int(kw.get("skip", 0))
    items = load_items(); dec = load_dec()
    nw = {s: set(words(notes(s))) for s in SECS}
    res = []; tot = unc = 0
    for i in order():
        d = dec[i]; it = items[i]
        if it["paper"] != 2 or d["status"] != "ver": continue
        mixed = any(c.startswith("o") for c in d["sec"].split("+"))
        if kw.get("only") == "fully" and mixed: continue
        if kw.get("only") == "mixed" and not mixed: continue
        voc = set().union(*[nw[s] for s in insecs(d)])
        bad = []
        pts = points(it["ms_text"])
        for p in pts:
            w = words(p); hit = sum(1 for x in w if x in voc)
            tot += 1
            if re.search(r"Mark Scheme|Trace ID|Syllabus|^Section|AVP|O LEVEL|papacambridge", p): continue
            if lo <= hit / len(w) < thr: bad.append((round(hit / len(w), 2), p)); unc += 1
        if bad: res.append((len(bad), len(pts), i, d["sec"], bad))
    res.sort(key=lambda r: (-r[0], r[2]))
    print("verified P2 items checked: marking points %d, below threshold %.2f: %d (%.1f%%), items with any: %d" % (tot, thr, unc, 100.0 * unc / max(tot, 1), len(res)))
    if kw.get("list"):
        used = 0
        for n, np_, i, sec, bad in res[skip:]:
            s = "## %s [%s] %d/%d\n" % (i, sec, n, np_) + "\n".join("   %.2f %s" % (c, p[:170]) for c, p in bad)
            if used + len(s) > budget: break
            print(s); used += len(s)
