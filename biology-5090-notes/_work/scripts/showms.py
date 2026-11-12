from state import *
def ms_text(M, dec, iid):
    pid = iid.split(":")[0]
    return "\n".join("<<%s>>\n%s" % (l, "\n".join(M[pid]["sections"][l])) for l in dict.fromkeys(dec[iid]["ms_labels"]))
if __name__ == "__main__":
    M = jload("data/ms2_sections.json"); dec = load_dec()
    for iid in sys.argv[1:]:
        print("=====", iid, "[%d]" % dec[iid]["marks"], dec[iid]["sec"], "old pts", dec[iid]["old_pts"])
        print(ms_text(M, dec, iid))
