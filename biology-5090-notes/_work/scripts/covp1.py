"""Lexical check of verified Paper 1 questions against the notes of their own subsection(s): lists the questions whose vocabulary is least represented."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
STOP = set("which what when where diagram shows show shown following these those their there from with that this have been does would could will after before during into than then they them each other about below above table graph figure correct statement statements describes describe labelled label part parts cell cells some most more less many both only also between through same different used using person plant plants human body called name named number increase decrease higher lower high greater least first second third explain explains because result results process happens happen substance substances structure structures function functions organ organs level levels concentration blood water".split())
def toks(t):
    return {w[:6] for w in re.findall(r"[a-z]{4,}", t.lower()) if w not in STOP}
its = load_items(); d = load_dec()
N = {s: toks(notes(s)) for s in SECS}
out = []
for i in order():
    it = its[i]
    if it["paper"] != 1 or d[i]["status"] != "ver": continue
    secs = [s for s in d[i]["sec"].split("+") if s in N]
    T = toks(re.sub(r"(PapaCambridge|papacambridge|Downloaded from|Trace ID|at www\.cambridge|www\.cie).*$", "", it["text"]))
    if len(T) < 3: continue
    have = set().union(*[N[s] for s in secs])
    miss = sorted(T - have)
    out.append((len(T & have) / len(T), i, d[i]["sec"], it["key"], miss))
out.sort()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 60; skip = int(sys.argv[2]) if len(sys.argv) > 2 else 0
print("verified P1 items checked:", len(out), "| below 0.5:", sum(1 for o in out if o[0] < 0.5), "| below 0.6:", sum(1 for o in out if o[0] < 0.6), "| below 0.7:", sum(1 for o in out if o[0] < 0.7))
for sc, i, sec, key, miss in out[skip:skip + n]:
    t = re.sub(r"\s+", " ", its[i]["text"])
    t = re.sub(r"(PapaCambridge|papacambridge|Downloaded from|Trace ID|at www\.cambridge|www\.cie).*$", "", t)
    print("#%s [%s key %s] %.2f %s" % (i, sec, key, sc, t[:300]))
