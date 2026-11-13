#!/usr/bin/env python3
"""bparts.py — the printed sub-parts that each mark-bearing unit of a Paper 2 question covers.

The verification tracker has one row per mark-bearing unit of a question. The parser of the notes
(../parse_p2.parse_qp2) names a unit by the sub-part in which its mark '[n]' is printed. Where one mark covers several
sub-parts — usual in the papers of 2004-2009, e.g. (a)(i) and (a)(ii) with a single '[2]' after (ii) — the unit is named
'aii' although it consists of (a)(i) and (a)(ii). The header of a bank page names a unit by ALL the sub-parts it covers.

leaf_groups() repeats the label tracking of parse_qp2 (same rows, same rules, copied) and records for every unit the
labels passed since the previous mark. `python bparts.py` compares the units found here with the units recorded by the
parser for all papers (WORK/p2_manifest.json): they must be identical, label by label and mark by mark."""
import sys, os, re, json, collections
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(HERE))
from lib import WORK, SRC
import fitz, parse_p2
RO=['i','ii','iii','iv','v','vi','vii','viii','ix','x']
def leaf_groups(qpfile):
    """({unit label: [sub-part labels it covers, in order]}, [[unit label, marks], …] merged as in parse_qp2)."""
    doc=fitz.open(os.path.join(SRC,qpfile))
    groups=collections.OrderedDict(); leaves=[]
    cur=None; expected=1; letter=None; roman=None; since=[]
    for pi in range(1,len(doc)):
        page=doc[pi]; rows=parse_p2.qp_rows(page)
        if not rows: continue
        labset=set()
        for f in parse_p2.page_figs(page,rows):
            for rid in f['label_rows']: labset.add(rid)
        for r in rows:
            t=r['text']
            m=re.match(r'^(\d{1,2})(?=\s|$)',t)
            if m and r['x0']<64 and int(m.group(1))==expected and expected<=14 and id(r) not in labset:
                cur=expected; expected+=1; letter=None; roman=None; since=[]
                t=t[m.end():].strip(); qstart=True
                if not t: continue
            else: qstart=False
            if cur is None: continue
            if id(r) in labset: continue
            tt=t; first=True; had_letter=False
            while True:
                ml=re.match(r'^\(([a-z]{1,4})\)(\s+|$)',tt)
                if not ml: break
                lab=ml.group(1)
                isrom=bool(parse_p2.ROM.match(lab)) and not (lab=='i' and letter=='h' and roman is None)
                if isrom and lab in ('i','v','x') and first and r['x0']<82 and letter is not None and len(lab)==1 and ord(lab)==ord(letter)+1:
                    isrom=False   # letter sequence ... (h) (i)
                if isrom:
                    okpos=(r['x0']<101.5 and first) or had_letter or qstart
                    okseq=(roman is None and lab=='i') or (roman in RO and lab in RO and RO.index(lab)>RO.index(roman)) or had_letter
                    if not (okpos and okseq): break
                    roman=lab; since.append((letter or '',roman))
                elif len(lab)==1:
                    okpos=(r['x0']<82 and first) or qstart
                    okseq=(letter is None) or (ord(lab)>ord(letter))
                    if not (okpos and okseq): break
                    letter=lab; roman=None; had_letter=True; since.append((letter,''))
                else: break
                tt=tt[ml.end():]; first=False
            if not re.search(r'\[Total:?\s*(\d+)\s*(marks?)?\]',t):
                for mm in re.finditer(r'\[(\d{1,2})\]',t):
                    label=f"{cur}{letter or ''}{roman or ''}"
                    g=groups.setdefault(label,[])
                    for x in since+[(letter or '',roman or '')]:
                        if x not in g: g.append(x)
                    since=[]; leaves.append([label,int(mm.group(1))])
    merged=[]; seen={}
    for lab,mk in leaves:
        if lab in seen: merged[seen[lab]][1]+=mk
        else: seen[lab]=len(merged); merged.append([lab,mk])
    return groups,merged
def group_label(g):
    """[('a',''),('a','i'),('a','ii')] -> '(a)(i)-(ii)'; [('b','')] -> '(b)'; [('','')] -> 'whole question'."""
    # a lettered part that is only the introduction of its first sub-part is not named separately
    g=[x for x in g if not (x[1]=='' and any(y[0]==x[0] and y[1] for y in g))]
    byl=collections.OrderedDict()
    for l,r in g: byl.setdefault(l,[]).append(r)
    out=[]
    for l,rs in byl.items():
        L=f'({l})' if l else ''
        rs=[r for r in rs if r]
        if not rs: out.append(L or 'whole question'); continue
        idx=[RO.index(r) for r in rs]
        if len(rs)>1 and idx==list(range(idx[0],idx[0]+len(rs))): out.append(f'{L}({rs[0]})-({rs[-1]})')
        else: out.append(', '.join(f'{L}({r})' for r in rs))
    return ', '.join(out)
if __name__=='__main__':
    man=json.load(open(WORK+'/p2_manifest.json')); pairs=json.load(open(WORK+'/pairs.json')) if os.path.exists(WORK+'/pairs.json') else None
    import pickle
    S=pickle.load(open(WORK+'/state.pkl','rb'))
    bad=0; multi=collections.Counter(); n=0; ex=[]
    for p in S['pairs']:
        if p['paper']!=2: continue
        groups,leaves=leaf_groups(p['qp'])
        want=[[a,b] for a,b in man[p['id']]['leaves']]
        if leaves!=want:
            bad+=1; print('DIFFERENT',p['id'],[x for x in leaves if x not in want][:5],[x for x in want if x not in leaves][:5])
        for lab,g in groups.items():
            n+=1
            q=re.match(r'^\d+',lab).group(0); plain=lab[len(q):]
            lbl=group_label(g)
            g2=[x for x in g if not (x[1]=='' and any(y[0]==x[0] and y[1] for y in g))]
            if len(g2)>1:
                multi[p['id'][:3]]+=1
                if len(ex)<12: ex.append((p['id'],lab,lbl))
    print('papers with units different from the parser:',bad)
    print('units',n,'| units that cover more than one sub-part:',sum(multi.values()),'| by session:',dict(sorted(multi.items(),key=lambda kv:(int(kv[0][1:]),kv[0][0]))))
    for x in ex: print('  ',x)
    sys.exit(1 if bad else 0)
