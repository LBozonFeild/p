from extract_ms2 import *
def run(pid, show_pages=None, grep=None):
    pairs = load_pairs(); dec = load_dec(); order_ = order()
    p=[x for x in pairs if x["id"]==pid][0]
    ids=[i for i in order_ if i.startswith(pid+":")]
    expected=[]
    for i in ids:
        for l in dec[i]["ms_labels"]:
            if l not in expected: expected.append(l)
    G,info,marks=parse_ms(p["ms"],expected,p.get("ms_pages"),p["year"])
    print(pid, p["ms"], info)
    print(" expected:", " ".join(expected))
    print(" pages:", G.pages)
    print(" rejected:", G.rejected)
    print(" empty:", [l for l in expected if not G.sections[l]])
    d=opendoc(p["ms"])
    if show_pages:
        for pn in show_pages:
            pg=d[pn-1]
            V,H=rulings(pg)
            print("  page",pn,"V",[(x,round(t)) for x,t in V if t>60],"H",[(y,round(t)) for y,t in H if t>100])
            for L in page_lines(pg):
                s=" ".join("%d:%s"%(x0,t) for x0,x1,t in L["words"])
                if grep is None or re.search(grep, L["text"]):
                    print("   y%4d"%L["y0"], s[:150])
    return G
if __name__=="__main__":
    pid=sys.argv[1]
    pgs=[int(x) for x in sys.argv[2].split(",")] if len(sys.argv)>2 and sys.argv[2] else None
    run(pid, pgs, sys.argv[3] if len(sys.argv)>3 else None)
