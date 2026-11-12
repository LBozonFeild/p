# show.py <id...> [q=N] [ms=N] [ctx=N]  -- print question text, key / full mark-scheme text and current decision
from state import *
def show(iid, items, dec, q=4000, ms=20000, ctx=700):
    it = items[iid]; d = dec[iid]
    hd = "##### %s | sec %s | %s | fig %s" % (iid, d["sec"], d["status"], d["fig"])
    if d.get("flag"): hd += " | FLAG"
    if d.get("remarks"): hd += " | rem: " + "; ".join(d["remarks"])[:160]
    print(hd)
    if it["paper"] == 1:
        print(it["text"][:q]); print("KEY:", it["key"], "  (p.%d)" % it["page"], ("also " + ",".join(d["also"][:6])) if d.get("also") else "")
    else:
        if it.get("context") and ctx: print("[CTX] " + it["context"][:ctx].replace("\n", " / "))
        print("[Q %s, %d marks, QP p.%s] " % (it["label"], it["marks"], it["pages"]) + it["qtext"][:q])
        print("[MS p.%s] " % it["ms_pages"] + it["ms_text"][:ms])
if __name__ == "__main__":
    items = load_items(); dec = load_dec()
    kw = dict(a.split("=") for a in sys.argv[1:] if re.match(r"^(q|ms|ctx)=\d+$", a))
    ids = [a for a in sys.argv[1:] if not re.match(r"^(q|ms|ctx)=\d+$", a)]
    for iid in ids:
        if iid not in items:
            print("?? unknown id", iid); continue
        show(iid, items, dec, **{k: int(v) for k, v in kw.items()})
        print()
