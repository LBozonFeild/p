# compact view: showc.py <id...>  -> question tail (160 chars) + full MS text on few lines
from state import *
items = load_items(); dec = load_dec()
for iid in sys.argv[1:]:
    it = items[iid]; d = dec[iid]
    q = re.sub(r"\s+", " ", it["qtext"])[-170:]
    ms = it["ms_text"]
    ms = re.sub(r"<<MS [^>]*>>\n", "", ms)
    ms = re.sub(r"\s*‖\s*;", ";", ms)
    ms = re.sub(r"\n(?=\S)", " | ", ms)
    print("## %s [%s, %dm] %s\n   %s" % (iid, d["sec"], it["marks"], q, ms))
