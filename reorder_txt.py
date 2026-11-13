#!/usr/bin/env python3
"""Re-order the plain-text question bank into newest-to-oldest order.

Question blocks are preserved verbatim (including subquestion-split
blocks); they are sorted newest to oldest, then paper/variant, then
question number, then subquestion. MCQ answers are already present as
text inside each block. The syllabus subsection moves into a per-block
tag line.
"""
import re, sys

SRC = 'biology-5090/biology_5090_past_paper_questions_with_ms.txt'
ORDER = {'October/November': 2, 'May/June': 1, 'February/March': 0}

lines = open(SRC, encoding='utf-8').read().split('\n')

i = 0
while i < len(lines) and not lines[i].startswith('# '):
    i += 1
preamble = lines[:i]

blocks = []
chapter = sub = sess_key = sess = None
cur = None

def flush():
    global cur
    if cur is not None:
        blocks.append(cur)
        cur = None

for ln in lines[i:]:
    if ln.startswith('# '):
        flush(); chapter = ln[2:].strip(); sub = sess_key = sess = None
    elif ln.startswith('## '):
        flush(); sub = ln[3:].strip(); sess_key = sess = None
    elif ln.startswith('### '):
        flush()
        m = re.match(r'^### (May/June|October/November|February/March) (\d{4}) — Paper (\d) — Variant (\d)$', ln)
        if not m:
            sys.exit('bad session header: ' + ln)
        sess = ln[4:].strip()
        sess_key = (int(m.group(2)), ORDER[m.group(1)], int(m.group(3)), int(m.group(4)))
    elif ln.startswith('**Question '):
        flush()
        m = re.match(r'^\*\*Question (\d+)(\([a-z](?:\([ivx]+\))?\))?\*\*$', ln)
        if not m:
            sys.exit('bad question header: ' + ln)
        cur = dict(header=ln, q=int(m.group(1)), part=m.group(2) or '',
                   lines=[ln], sess_key=sess_key, sub=sub, chapter=chapter)
    else:
        if cur is not None:
            cur['lines'].append(ln)
flush()

def sort_key(b):
    return (-b['sess_key'][0], -b['sess_key'][1], b['sess_key'][2], b['sess_key'][3], b['q'], b['part'])

blocks.sort(key=sort_key)

preamble = [('Ordering: newest to oldest; then paper and variant; then question order. '
             'Syllabus subsections are tagged on each question.'
             if l.startswith('Ordering:') else l) for l in preamble]

out = list(preamble)
prev = None
for b in blocks:
    if b['sess_key'] != prev:
        if prev is not None:
            while out and out[-1] == '':
                out.pop()
            out.extend(['', ''])
        y, srank, paper, var = b['sess_key']
        sname = {2: 'October/November', 1: 'May/June', 0: 'February/March'}[srank]
        out.append(f'### {sname} {y} — Paper {paper} — Variant {var}')
        out.append('')
        prev = b['sess_key']
    body = [l for l in b['lines']]
    while body and body[-1].strip() in ('', '---'):
        body.pop()
    out.extend(body)
    out.append('')
    if b['sub']:
        out.append('SYLLABUS SUBSECTION: ' + b['sub'])
        out.append('')
    out.append('---')
    out.append('')

text = '\n'.join(out)
text = re.sub(r'\n{4,}', '\n\n\n', text)
open(SRC, 'w', encoding='utf-8').write(text)
print('blocks', len(blocks), 'lines', text.count(chr(10)))
