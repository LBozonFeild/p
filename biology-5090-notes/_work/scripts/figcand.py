"""Verified Paper 2 parts whose marking points depend on a labelled figure / a drawing on a figure (candidates for visual inspection)."""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
its = load_items(); d = load_dec()
def cls(it):
    q = it["qtext"]; ms = it["ms_text"]
    body = "\n".join(l for l in ms.split("\n") if not l.startswith("<<MS"))
    kinds = []
    if re.search(r"(?m)^\s*\(?[A-Z]\)?\s*(–|-|=|:)\s*\w", body) or re.search(r"(?m)^\s*\(([A-Z])\)\s+\w", body): kinds.append("names-for-letters")
    if re.search(r"(?m)^\s*\(?[A-Z]\)?\s*(;|‖|\{|$)", body) or re.search(r"(?m)^\s*[A-Z]( and | ?[/,+] ?)[A-Z]\b", body): kinds.append("letter-answers")
    if re.search(r"\b(label line|line (drawn|to|from|ending)|arrow|shad(ed|ing)|drawn|circle[ds]?|cross (drawn|on)|labelled correctly|correctly labelled)\b", body, re.I): kinds.append("draw-on-figure")
    return kinds
rows = []
for i in order():
    it = its[i]
    if it["paper"] != 2 or d[i]["status"] != "ver": continue
    k = cls(it)
    if not k: continue
    rows.append((i, d[i]["sec"], d[i]["fig"], k))
c = collections.Counter(); 
for r in rows: c[(r[2], "+".join(r[3]))] += 1
if len(sys.argv) > 1 and sys.argv[1] == "list":
    for r in rows:
        if r[2] != "viewed": print(r[0])
else:
    print("verified P2 parts with figure-dependent marking points:", len(rows))
    for k, v in sorted(c.items()): print("  ", k, v)
    pages = collections.Counter()
    P = {p["id"]: p for p in load_pairs()}
    pg = set()
    for r in rows:
        if r[2] == "viewed": continue
        it = its[r[0]]
        for p in (it.get("pages") or [])[:1]: pg.add((it["pair"], p))
    print("distinct first pages:", len(pg))
