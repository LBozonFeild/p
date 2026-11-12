"""Sequential FULL read of the mark scheme of every out-of-scope Paper 2 part (complements the vocabulary scan).
usage: readoos.py [code=o6] [budget=16500] [commit=1]   (commit=1 records the ids printed by the PREVIOUS call as read)"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state import *
from lib import jload, jsave
NOISE = re.compile(r"(Question\s+Answer\s+Marks?\s+Guidance|Question\s+Answer|Trace ID:.*|Re-uploading.*|Licensed for hosting.*|Page \d+ Mark Scheme.*?(20\d\d)|Cambridge O Level – .*?20\d\d|GCE O LEVEL – .*?20\d\d|Syllabus Paper|© UCLES 20\d\d|5090\s+2\d)")
def clean(ms):
    out = []
    for l in ms.split("\n"):
        if l.startswith("<<MS"): continue
        l = NOISE.sub("", l).strip()
        l = re.sub(r"\s{2,}", " ", l)
        if l: out.append(l)
    return " | ".join(out)
def main():
    kw = dict(a.split("=") for a in sys.argv[1:] if "=" in a)
    budget = int(kw.get("budget", 16500))
    its = load_items(); dec = load_dec(); st = jload("state/oos_fullread.json", {"read": [], "last": []})
    if kw.get("commit"):
        st["read"] = sorted(set(st["read"]) | set(st["last"])); st["last"] = []; jsave("state/oos_fullread.json", st)
    done = set(st["read"])
    todo = [i for i in order() if its[i]["paper"] == 2 and dec[i]["status"] == "oos" and i not in done and (not kw.get("code") or dec[i]["sec"] == kw["code"])]
    used = 0; shown = []
    for i in todo:
        it = its[i]; q = re.sub(r"\s+", " ", it["qtext"]).strip()
        q = re.sub(r"\b(DO NOT WRITE IN THIS MARGIN|MARGIN|THIS IN WRITE NOT DO|WRITE NOT DO|NOT DO|THIS IN|IN WRITE|DO NOT|WRITE|THIS|NOT)\b", "", q) if it["pair"] >= "s25" else q
        q = re.sub(r"[ .]{3,}", " ", q); q = re.sub(r"\s+", " ", q)[-int(kw.get("q", 120)):]
        s = "#%s [%s %sm] %s => %s" % (i, dec[i]["sec"], it["marks"], q, clean(it["ms_text"]))
        if used + len(s) > budget and shown: break
        print(s); used += len(s) + 1; shown.append(i)
    st["last"] = shown; jsave("state/oos_fullread.json", st)
    print("== shown %d, remaining after these %d (read so far %d)" % (len(shown), len(todo) - len(shown), len(done)))
main()
