# One-off recovery: rebuild pairs.json and decisions.json from the previously generated tracker
# (the original working directory outside the repository was lost when the sandbox was recycled).
import re, sys
if "--force" not in sys.argv:
    sys.exit("restore_from_tracker.py is a one-off recovery script (used once, on 2026-11-12). Running it again would overwrite "
             "state/pairs.json and state/decisions.json with a reconstruction from the tracker. Pass --force only if that is intended.")
sys.argv.remove("--force")
from lib import *
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "full_paper_verification_tracker.txt")
L = open(src, encoding="utf-8").read().split("\n")
iB = next(i for i, l in enumerate(L) if l.startswith("PART B"))
pairs = []
i = 0
while i < iB:
    m = re.match(r"^(\w+) \| year (\d+) \| session ([^|]+) \| paper (\d) variant (\S+)$", L[i])
    if m:
        pid = m.group(1)
        m2 = re.match(r"^\s+QP: (\S+) \| MS: (\S+) \((.*), pages (.*)\)$", L[i + 1])
        m3 = re.match(r"^\s+questions: (\d+) \| sub-questions \(mark-bearing parts\): (\d+) \| marks available: (\d+)", L[i + 2])
        pg = m2.group(4)
        pages = None if pg == "None" else [int(x) for x in re.findall(r"\d+", pg)]
        pairs.append(dict(id=pid, year=int(m.group(2)), session=m.group(3).strip(), paper=int(m.group(4)), variant=m.group(5),
                          qp=m2.group(1), ms=m2.group(2), ms_kind=m2.group(3), ms_pages=pages,
                          nq=int(m3.group(1)), nsub=int(m3.group(2)), marks=int(m3.group(3))))
        i += 3
    else:
        i += 1
dec = {}
order = []
cur = None
for l in L[iB:]:
    m = re.match(r"^--- (\w+)\s+\((\S+) / (\S+)\)", l)
    if m:
        cur = m.group(1); continue
    if not l.startswith("  ") or cur is None:
        continue
    f = [x.strip() for x in l.strip().split(" | ")]
    d = {}
    if f[0].startswith("Q") and " key " in f[0]:
        m = re.match(r"^Q(\d+) key (\S+)$", f[0])
        iid = "%s:%s" % (cur, m.group(1))
        d["key"] = m.group(2)
        sec, status, fig, rest = f[1], f[2], f[3], f[4:]
    else:
        m = re.match(r"^(\S+) \[(\d+)\]$", f[0])
        iid = "%s:%s" % (cur, m.group(1))
        d["marks"] = int(m.group(2))
        sec = f[1]
        m = re.match(r"^MS (.*) \(p\.(\d+)\)$", f[2])
        d["ms_labels"] = [x.strip() for x in m.group(1).split(",")]
        d["ms_page"] = int(m.group(2))
        m = re.match(r"^(\d+) pts / (\d+) alt$", f[3])
        d["old_pts"] = int(m.group(1)); d["old_alt"] = int(m.group(2))
        status, fig, rest = f[4], f[5], f[6:]
    d["sec"] = sec
    d["status"] = {"VERIFIED": "ver", "OUT-OF-SCOPE": "oos", "IN-SCOPE-PENDING": "pend", "PENDING-REVIEW": "pend"}[status]
    d["fig"] = {"no figure": "none", "figure viewed": "viewed", "text sufficient / figure not rendered": "text",
                "n/a (out of scope)": "na", "FIGURE NOT YET VIEWED": "noimg"}[fig]
    rem = []
    for r in rest:
        if r.startswith("also: "):
            d["also"] = [x.strip() for x in r[6:].split(",")]
        elif r.startswith("FLAG: "):
            d["flag"] = r[6:]
        else:
            rem.append(r)
    if rem:
        d["remarks"] = rem
    dec[iid] = d
    order.append(iid)
jsave("state/pairs.json", pairs)
jsave("state/decisions.json", dec)
jsave("state/order.json", order)
print("pairs", len(pairs), "P1", sum(p["paper"] == 1 for p in pairs), "P2", sum(p["paper"] == 2 for p in pairs))
print("items", len(dec), "P1", sum("key" in d for d in dec.values()), "P2", sum("marks" in d for d in dec.values()))
import collections
print(collections.Counter(d["status"] for d in dec.values()))
print("flags", [k for k, d in dec.items() if "flag" in d])
print("pending", [k + "=" + d["sec"] for k, d in dec.items() if d["status"] == "pend"])
