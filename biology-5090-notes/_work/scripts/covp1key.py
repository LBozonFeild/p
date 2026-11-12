"""Verified Paper 1 questions with textual options: is the KEYED option's wording represented in the notes of the question's subsection(s)?"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
STOP = set("which what when where diagram shows show shown following these those their there from with that this have been does would could will after before during into than then they them each other about below above table graph figure correct statement only also between through same different used using called name named number more less most both".split())
def toks(t): return {w[:6] for w in re.findall(r"[a-z]{4,}", t.lower()) if w not in STOP}
its = load_items(); d = load_dec()
N = {s: toks(notes(s)) for s in SECS}
out = []; nopt = 0
for i in order():
    it = its[i]
    if it["paper"] != 1 or d[i]["status"] != "ver": continue
    t = re.sub(r"(PapaCambridge|papacambridge|Downloaded from|Trace ID|at www\.cambridge|www\.cie|© UCLES|© Cambridge).*$", "", re.sub(r"\s+", " ", it["text"]))
    m = re.search(r"\sA\s+(.+?)\s+B\s+(.+?)\s+C\s+(.+?)\s+D\s+(.+)$", t)
    if not m: continue
    opt = m.group("ABCD".index(it["key"]) + 1)
    T = toks(opt)
    if len(T) < 2: continue
    nopt += 1
    secs = [s for s in d[i]["sec"].split("+") if s in N]
    have = set().union(*[N[s] for s in secs])
    out.append((len(T & have) / len(T), i, d[i]["sec"], it["key"], opt, t[:m.start()][-150:]))
out.sort()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
print("verified P1 questions with a textual keyed option:", nopt, "| keyed option below 0.5:", sum(1 for o in out if o[0] < 0.5), "| below 0.7:", sum(1 for o in out if o[0] < 0.7))
for sc, i, sec, key, opt, stem in out[:n]:
    print("#%s [%s %s] %.2f ..%s => %s" % (i, sec, key, sc, stem, opt[:150]))
