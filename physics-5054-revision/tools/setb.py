#!/usr/bin/env python3
"""setb.py <section> < text   — replace the checklist lines of the named sub-topics in tools/notes_src/<section>.txt.
Input: '@ID' starts a sub-topic; then its lines: '- text' (Paper 2 marking point) or '* text' (Paper 1 explanation).
Header ('== …'), ALSO and MOVE lines of the file are kept unchanged."""
import sys,re
from notes_lib import *
sec=sys.argv[1]; fn=f'{SRC}/{sec}.txt'
new={};cur=None
for ln in sys.stdin.read().split('\n'):
    if ln.startswith('@'): cur=ln[1:].strip(); new[cur]=[]; continue
    if not ln.strip(): continue
    assert cur is not None, 'text before first @ID'
    assert ln.startswith('- ') or ln.startswith('* '), 'bad line: '+ln[:60]
    new[cur].append(ln.rstrip())
out=[];cur=None;seen=set()
for ln in open(fn,encoding='utf-8').read().split('\n'):
    if ln.startswith('== '):
        cur=ln[3:].split(' | ')[0].strip(); out.append(ln)
        if cur in new: out.extend(new[cur]); seen.add(cur)
        continue
    if ln.startswith('ALSO ') or ln.startswith('MOVE ') or ln.startswith('#'): out.append(ln); continue
    if cur in new: continue
    if ln.strip(): out.append(ln)
missing=set(new)-seen
assert not missing, f'unknown sub-topic ids: {missing}'
open(fn,'w',encoding='utf-8').write('\n'.join(out)+'\n')
b,m=read_spec(sec)
print(sec,'updated:',', '.join(f"{x['id']}={sum(1 for l in x['lines'] if l.startswith('- '))}+{sum(1 for l in x['lines'] if l.startswith('* '))}" for x in b))
