#!/usr/bin/env python3
"""mv.py <section> <ID>:<idx,idx,…> … — record manual sub-topic filing (stored as stable pid|label keys)."""
import sys
from notes_lib import *
sec=sys.argv[1]; items={it['idx']:it for it in load_items(sec)}
buckets,moves=read_spec(sec); ids={b['id'] for b in buckets}
add=[]
for arg in sys.argv[2:]:
    b,lst=arg.split(':')
    assert b in ids,f'unknown sub-topic {b}'
    for i in lst.split(','):
        it=items[int(i)]; add.append(f"MOVE {it['pid']}|{it['lab']}|{b}")
with open(f'{SRC}/{sec}.txt','a',encoding='utf-8') as f:
    f.write('\n'.join(add)+'\n')
print(len(add),'moves recorded')
