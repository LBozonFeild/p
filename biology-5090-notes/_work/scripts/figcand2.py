"""Verified Paper 2 parts whose marking points identify or mark structures on a figure -> state/p2_fig_candidates.json"""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
from lib import jsave
its = load_items(); d = load_dec()
NAME = re.compile(r"\b(identify|name|state the name|give the name|state the identity|what is|which (letter|structure|part|vessel|cell)|state the letter|use the letter)\b", re.I)
LAB = re.compile(r"\b(labelled|structures?|parts?|cells?|vessels?|tissues?|regions?|organs?|components?|chambers?|glands?|molecules?|bones?|neurones?)\b[^.?]{0,25}\b[A-Z]\b|\b[A-Z]\b(,| and| or| to) \b[A-Z]\b|\b(identify|name) [A-Z]\b", re.I)
ONFIG = re.compile(r"\bOn Fig\.|\bon Figure|label line|shade|draw (in|arrows?|an arrow|and label|a line|lines)|complete Fig|place (a|the) letter|use (a )?lines?|use (a|an) (label|arrow)|mark with|indicate on|label (on|with|and name|a|the|one|two)|write the letter|by writing", re.I)
FIG = re.compile(r"\bFig\.|\bFigure\b|diagram|photograph|micrograph|drawing", re.I)
def msletters(it):
    body = "\n".join(l for l in it["ms_text"].split("\n") if not l.startswith("<<MS"))
    return bool(re.search(r"(?m)^\s*\(?[A-Z]\)?\s*(–|-|=|:|\))\s*\w", body) or re.search(r"(?m)^\s*\(?[A-Z]\)?\s*(;|‖|\{)", body))
rows = []
for i in order():
    it = its[i]
    if it["paper"] != 2 or d[i]["status"] != "ver": continue
    q = re.sub(r"\s+", " ", it["qtext"]); ctx = re.sub(r"\s+", " ", it.get("context") or ""); last = q[-240:]
    hasfig = bool(FIG.search(q) or FIG.search(ctx))
    k = None
    if hasfig and NAME.search(last) and (LAB.search(last) or msletters(it)): k = "name"
    elif ONFIG.search(last) and hasfig: k = "mark"
    elif msletters(it) and hasfig and re.search(r"\b[A-Z]\b", last): k = "letters"
    if k: rows.append((i, k, d[i]["sec"], d[i]["fig"], it.get("pages")))
jsave("state/p2_fig_candidates.json", rows)
c = collections.Counter((r[1], r[3]) for r in rows)
print(len(rows), dict(c))
pg = {(r[0].split(":")[0], (r[4] or [None])[0]) for r in rows if r[3] != "viewed"}
print("distinct (paper, first part page):", len(pg))
