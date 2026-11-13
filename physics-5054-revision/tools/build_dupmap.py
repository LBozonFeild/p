#!/usr/bin/env python3
"""build_dupmap.py — Paper 1 repeated questions (exact text identity with a question in a paper verified earlier).
The working copy of p1_dupmap.json was lost with the scratch directory, so this script
 (1) recovers the map from the question-level records of the tracker ("identical text to <pid> Q<n>"),
 (2) re-validates every entry independently: the two question texts (stem + options, as extracted from the two QP PDFs) are
     identical after whitespace normalisation, the two official keys are the same letter, the source question has no findings
     line of its own and the target question has one,
 (3) writes WORK/p1_dupmap.json and tools/data/p1_dupmap.json."""
from lib import *
import collections
REPO='/home/user/p/physics-5054-revision'
trk=open(REPO+'/full_paper_verification_tracker.txt',encoding='utf-8').read().split('\n')
dup={};pid=None
for ln in trk:
    m=re.match(r'^==== PAIR (\S+) \| Paper (\d)',ln)
    if m: pid=m.group(1) if m.group(2)=='1' else None; continue
    if pid:
        m=re.match(r'^\s+Q(\d+) key ([A-D]) \| worked ([A-D?]) \| \S+ :: \(identical text to (\S+) Q(\d+)\)',ln)
        if m: dup[f'{pid}#{int(m.group(1))}']=[m.group(4),int(m.group(5))]
qs=json.load(open(WORK+'/p1_questions.json')); keys=json.load(open(WORK+'/keys_p1.json'))
def norm(t): return re.sub(r'\s+',' ',t).strip()
def loose(t): return re.sub(r'[^0-9a-zα-ωΩ]','',t.lower().replace('\u2126','Ω').replace('Ω','Ω'))
def flines(p):
    out=set()
    for ln in open(f'{REPO}/findings/p1/{p}.txt',encoding='utf-8'):
        m=re.match(r'^(\d{1,2})\s+[ABCD?]\s',ln)
        if m: out.add(int(m.group(1)))
    return out
F={p:flines(p) for p in qs}
bad=[];typo=[];fig=collections.Counter()
for k,(tp,tn) in dup.items():
    p,n=k.split('#'); n=int(n)
    a=qs[p][n-1]; b=qs[tp][tn-1]
    assert a['n']==n and b['n']==tn
    if norm(a['text'])!=norm(b['text']):
        if loose(a['text'])==loose(b['text']): typo.append((k,tp,tn))
        else: bad.append((k,tp,tn,'text differs'))
    if keys[p]['key'][n-1]!=keys[tp]['key'][tn-1]: bad.append((k,tp,tn,'key differs'))
    if n in F[p]: bad.append((k,tp,tn,'source has its own findings line'))
    if tn not in F[tp]: bad.append((k,tp,tn,'target has no findings line'))
    fig[a['fig'] or '-']+=1
# every question must be covered exactly once: own findings line or a dup entry
miss=[(p,n) for p in qs for n in range(1,41) if n not in F[p] and f'{p}#{n}' not in dup]
both=[(p,n) for p in qs for n in range(1,41) if n in F[p] and f'{p}#{n}' in dup]
print('entries',len(dup),'| character-identical',len(dup)-len(typo)-len([b for b in bad if b[3]=='text differs']),'| identical apart from punctuation/typography',len(typo),'| problems',len(bad),'| questions with neither findings line nor dup entry',len(miss),'| with both',len(both),'| figure flags of repeated questions',dict(fig))
for b in bad[:20]: print('  ',b)
print('   typography-only differences:',', '.join(f'{k}->{tp} Q{tn}' for k,tp,tn in typo))
for m in miss[:20]: print('   MISSING',m)
os.makedirs(REPO+'/tools/data',exist_ok=True)
for fn in (WORK+'/p1_dupmap.json',REPO+'/tools/data/p1_dupmap.json'):
    json.dump(dup,open(fn,'w'),indent=0,sort_keys=True)
