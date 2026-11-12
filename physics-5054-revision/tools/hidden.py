#!/usr/bin/env python3
"""hidden.py <sec> -- list findings lines hidden behind a '+n' in dump_sec.py whose text differs
from the line shown (so that nothing is skipped when the checklist is written)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notes_lib import *
sec = sys.argv[1]
only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
items = load_items(sec); b, m = read_spec(sec); res = assign(items, b, m)
for bid in res:
    if only and bid not in only: continue
    for rep, hid in collapse(res[bid]):
        for h in hid:
            if normkey(h['text']) != normkey(rep['text']):
                print(bid, f"[{h['idx']}]", h['pid'][1:3] + ('M' if h['p1'] else 'P') + '|', h['text'][:300])
