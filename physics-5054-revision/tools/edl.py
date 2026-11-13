#!/usr/bin/env python3
"""edl.py <section> <match> <new line> [<match> <new line> …]  — edit single checklist lines of tools/notes_src/<section>.txt.
<match> is a substring that identifies exactly one checklist line; <new line> starts with '- ' or '* ', or is DELETE.
'+ID' as <match> appends <new line> to sub-topic ID ('- ' lines go after the last '- ' line, '* ' lines at the end)."""
import sys
from notes_lib import *
sec=sys.argv[1]; args=sys.argv[2:]; assert len(args)%2==0
fn=f'{SRC}/{sec}.txt'; L=open(fn,encoding='utf-8').read().rstrip('\n').split('\n')
for m,new in zip(args[0::2],args[1::2]):
    assert new=='DELETE' or new[:2] in ('- ','* '),new[:30]
    if m.startswith('+') and len(m)<=3:
        bid=m[1:]; s=[i for i,l in enumerate(L) if l.startswith(f'== {bid} | ')]; assert len(s)==1,(bid,s)
        e=s[0]+1
        while e<len(L) and not L[e].startswith('== '): e+=1
        blk=list(range(s[0]+1,e)); pos=s[0]+1
        if new.startswith('- '):
            c=[i for i in blk if L[i].startswith('- ')]; pos=(c[-1]+1) if c else s[0]+1
        else:
            c=[i for i in blk if L[i][:2] in ('- ','* ')]; pos=(c[-1]+1) if c else s[0]+1
        L.insert(pos,new); print('added to',bid); continue
    hit=[i for i,l in enumerate(L) if l[:2] in ('- ','* ') and m in l]
    assert len(hit)==1,f'{len(hit)} lines match {m!r}'
    if new=='DELETE': del L[hit[0]]; print('deleted')
    else: L[hit[0]]=new; print('replaced')
open(fn,'w',encoding='utf-8').write('\n'.join(L)+'\n')
