#!/usr/bin/env python3
"""dump_sec.py <section> [sub-topic ids|all] [full|brief] [page] — reading view of one syllabus section, grouped by the
sub-topic rules in tools/notes_src/<section>.txt.  Line: [idx] <yy><P|M>| text  +n
P = Paper 2 sub-question (official marking points), M = Paper 1 MCQ (own explanation); +n = lines saying the same thing."""
import sys
from notes_lib import *
sec=sys.argv[1]
want=sys.argv[2].split(',') if len(sys.argv)>2 and sys.argv[2]!='all' else None
brief=len(sys.argv)>3 and sys.argv[3]=='brief'
page=int(sys.argv[4]) if len(sys.argv)>4 else 0
items=load_items(sec); buckets,moves=read_spec(sec)
if not buckets: buckets=[dict(id='Z',title='(no sub-topics defined)',rx='',prio=0,lines=[],rules=[])]
res=assign(items,buckets,moves)
titles={b['id']:b['title'] for b in buckets}
OUT=[f'## {sec}: {len(items)} items, {sum(len(i["text"]) for i in items)} chars; '+', '.join(f'{k}={len(v)}' for k,v in res.items())]
for bid,its in res.items():
    if want and bid not in want: continue
    gs=chain(collapse(its))
    OUT.append(f'\n=== {bid} | {titles.get(bid,"UNASSIGNED")} ({len(its)} items, {len(gs)} shown)')
    for rep,others in gs:
        t=rep['text'][:95] if brief else rep['text']
        OUT.append(f"[{rep['idx']}] {rep['pid'][1:3]}{'M' if rep['p1'] else 'P'}| {t}"+(f'  +{len(others)}' if others else ''))
text='\n'.join(OUT)
if page:
    pages=[[]]; n=0
    for l in text.split('\n'):
        if n+len(l)+1>15000 and pages[-1]: pages.append([]); n=0
        pages[-1].append(l); n+=len(l)+1
    print(f'(page {page} of {len(pages)})'); print('\n'.join(pages[page-1]))
else: print(text)
