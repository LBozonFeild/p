# mark.py ver <id...>            mark in-scope items as verified (question + full MS read, notes checked/patched)
# mark.py sec <id>=<a+b> ...     set subsection codes (in-scope -> pending until 'ver'; all out-of-scope -> oos)
# mark.py add <sec[+sec]> <id..> add in-scope subsection(s) to items (kept: existing codes) and mark them verified with a remark
# mark.py drop <sec[+sec]> <id..> remove subsection code(s) (item returns to out-of-scope when none is left)
# mark.py flag <id> <text> | note <id> <text> | fig <viewed|text|none> <id...>
from state import *
dec = load_dec(); a = sys.argv[1:]
cmd = a[0]
def chk(i):
    if i not in dec: sys.exit("unknown id " + i)
if cmd == "ver":
    for i in a[1:]:
        chk(i)
        if not insecs(dec[i]): sys.exit("no in-scope section: " + i)
        dec[i]["status"] = "ver"
        if dec[i]["fig"] == "na": dec[i]["fig"] = "text"
    log("ver " + " ".join(a[1:]))
elif cmd == "sec":
    for x in a[1:]:
        i, s = x.rsplit("=", 1); chk(i)
        for c in s.split("+"):
            if c not in SECS and c not in OOS: sys.exit("bad code " + c)
        dec[i]["sec"] = s
        if insecs(dec[i]): dec[i]["status"] = "pend"
        else: dec[i]["status"] = "oos"; dec[i]["fig"] = "na"
    log("sec " + " ".join(a[1:]))
elif cmd == "add":
    new = a[1].split("+")
    for c in new:
        if c not in SECS: sys.exit("bad code " + c)
    for i in a[2:]:
        chk(i)
        cur = dec[i]["sec"].split("+")
        was_oos = dec[i]["status"] == "oos"
        for c in new:
            if c not in cur: cur.append(c)
        dec[i]["sec"] = "+".join(cur); dec[i]["status"] = "ver"
        if dec[i]["fig"] == "na": dec[i]["fig"] = "text"
        if was_oos:
            r = dec[i].setdefault("remarks", [])
            if "moved in by full-MS audit of out-of-scope items" not in r: r.append("moved in by full-MS audit of out-of-scope items")
    log("add %s %s" % (a[1], " ".join(a[2:])))
elif cmd == "drop":
    # mark.py drop <sec[+sec]> <id...>: remove in-scope subsection code(s); an item left with no in-scope code returns to out-of-scope
    rem = a[1].split("+")
    for i in a[2:]:
        chk(i)
        cur = [c for c in dec[i]["sec"].split("+") if c not in rem]
        if not cur: sys.exit("no code left for " + i)
        dec[i]["sec"] = "+".join(cur)
        if not insecs(dec[i]):
            dec[i]["status"] = "oos"; dec[i]["fig"] = "na"
            dec[i]["remarks"] = [r for r in (dec[i].get("remarks") or []) if "moved in by full-MS audit" not in r]
    log("drop %s %s" % (a[1], " ".join(a[2:])))
elif cmd == "flag":
    chk(a[1]); dec[a[1]]["flag"] = " ".join(a[2:]); log("flag " + a[1])
elif cmd == "note":
    chk(a[1]); dec[a[1]].setdefault("remarks", []).append(" ".join(a[2:])); log("note " + a[1])
elif cmd == "fig":
    for i in a[2:]:
        chk(i); dec[i]["fig"] = a[1]
    log("fig %s %s" % (a[1], " ".join(a[2:])))
else:
    sys.exit("unknown command")
save_dec(dec)
import collections
print("ok;", dict(collections.Counter(d["status"] for d in dec.values())))
