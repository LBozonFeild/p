#!/usr/bin/env python3
"""bentries.py — the list of bank entries, in the order of the bank  -> WORK/bank/entries.json

Sources: the verified findings (state.pkl written by ../check.py from ../../findings) and the crop geometry (geom.json).
An entry is one original question shown once in one syllabus subsection:
  Paper 2: a numbered question is listed under every selected subsection that at least one of its sub-questions was
           assigned to in the verification tracker (first in-scope code of the tracker row); several tracker rows of the
           same question and subsection give ONE entry (the rows are consolidated, the parts are listed in the entry);
  Paper 1: a multiple-choice question is listed under the first in-scope code of its tracker row.
Order: subsection; then newest first: year (latest first), October/November before May/June of the same year; then
variant (1, 2), paper (1, 2), original question number."""
import sys, os, re, json, pickle, collections
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(HERE))
from lib import WORK, sess_key
import notes_lib
OUT=WORK+'/bank'
SECS=notes_lib.SECS; SECT=dict(SECS); ORDER={s:i for i,(s,_) in enumerate(SECS)}
CHAPTER={'1':'1 Motion, forces and energy','3':'3 Waves','4':'4 Electricity and magnetism'}
PARENT={'1.5':'1.5 Forces','1.7':'1.7 Energy, work and power','3.2':'3.2 Light','4.2':'4.2 Electrical quantities'}
def first_in(sec):
    for s in sec.split('+'):
        if s in ORDER: return s
    return None
def part_label(lab,q):
    t=lab[len(str(q)):]
    alt=''
    if t[:1] in('E','O') and (len(t)==1 or t[1:2].islower() or t[1:2]==''):
        alt='EITHER ' if t[0]=='E' else 'OR '; t=t[1:]
    m=re.match(r'^([a-h])?((?:i{1,3}|iv|v|vi{1,3}))?$',t)
    if not m: return alt+t
    return alt+(f'({m.group(1)})' if m.group(1) else '')+(f'({m.group(2)})' if m.group(2) else '') or alt.strip() or 'whole question'
ALT_E=re.compile(r'^(\d{1,2}\s+)?EITHER\b'); ALT_O=re.compile(r'^(\d{1,2}\s+)?OR\b')
TOTAL_RX=re.compile(r'\[\s*Total\s*:?\s*(\d+)\s*\]',re.I); MARK_RX=re.compile(r'\[\s*(\d{1,2})\s*\]')
def printed_marks(doc,bands):
    """What the question paper prints inside the pictures of one question, in reading order:
    dict(either=[(page, y, text)], orr=[...], marks=[n, ...] every '[n]', before_or=[...] the '[n]' above the OR row,
    totals=[n, ...] every '[Total: n]')."""
    out=dict(either=[],orr=[],marks=[],before_or=[],totals=[],whole=False)
    for pi,ya,yb in [b[:3] for b in bands]:
        for r in doc.rows(pi):
            if not ya<=(r['y0']+r['y1'])/2<=yb: continue
            t=r['text'].strip()
            m=ALT_E.match(t)
            if m:
                out['either'].append((pi+1,round(r['y0'],1),t[:60]))
                if m.group(1): out['whole']=True          # 'n EITHER': the whole question consists of the two alternatives
            elif ALT_O.match(t) and out['either']: out['orr'].append((pi+1,round(r['y0'],1),t[:60]))
            for x in TOTAL_RX.findall(t): out['totals'].append(int(x))
            for x in MARK_RX.findall(TOTAL_RX.sub(' ',t)):
                out['marks'].append(int(x))
                if not out['orr']: out['before_or'].append(int(x))
    return out
def question_marks(pm,tracker_total,has_or_rows,where):
    """(marks a candidate can score on the question, EITHER/OR question?, basis).
    Ordinary question: the sum of the marks of its tracker rows (bverify.py compares it with the marks printed on the paper).
    EITHER/OR question: the candidate answers one alternative, so the marks of the OR alternative are not added:
    the printed '[Total: n]' where the paper prints one, otherwise the sum of the printed marks above the OR row."""
    eo=bool(pm['either'] and pm['orr'])
    if has_or_rows and not eo: raise SystemExit(f'{where}: the tracker has rows of an OR alternative but the pictures show no EITHER / OR rows')
    if bool(pm['either'])!=bool(pm['orr']) or len(pm['either'])>1 or len(pm['orr'])>1:
        raise SystemExit(f'{where}: EITHER / OR rows not understood: {pm["either"]} {pm["orr"]}')
    if not eo: return tracker_total,False,'sum of the tracker rows'
    if pm['totals']:
        if len(set(pm['totals']))!=1: raise SystemExit(f'{where}: EITHER/OR question with different printed totals {pm["totals"]}')
        total=pm['totals'][0]; basis='printed total'
    else:
        total=sum(pm['before_or']); basis='printed marks above the OR alternative'
    if has_or_rows and total!=tracker_total: raise SystemExit(f'{where}: marks {total} ({basis}) differ from the tracker rows without the OR alternative ({tracker_total})')
    return total,True,basis
def sort_key(e):
    """order of the bank: subsection; newest first (year descending, October/November before May/June of the same year);
    variant 1 before 2; Paper 1 before Paper 2; original question number"""
    return (ORDER[e['sec']],-e['year'],0 if e['sess'][0]=='w' else 1,e['variant'],e['paper'],e['q'])
fallback=[]          # tracker rows on a selected subsection whose label is not a unit of the parser (named by part_label)
def build():
    import bgeom, bparts
    man2=json.load(open(WORK+'/p2_manifest.json'))
    S=pickle.load(open(WORK+'/state.pkl','rb'))
    res1,res2,pairs=S['res1'],S['res2'],S['pairs']
    G=json.load(open(OUT+'/geom.json'))
    E=[]
    for p in pairs:
        pid=p['id']; g=G[pid]
        year=2000+int(p['sess'][1:]); sname='May/June' if p['sess'][0]=='s' else 'October/November'
        variant=int(p['comp'][1]) if len(p['comp'])==2 else 1
        base=dict(pid=pid,sess=p['sess'],year=year,session=sname,paper=p['paper'],variant=variant,comp=p['comp'],qp=p['qp'],ms=p['ms'],combined=p['combined'])
        if p['paper']==2:
            r=res2[pid]; byq=collections.OrderedDict(); qdoc=bgeom.Doc(p['qp'])
            # sub-parts covered by every mark-bearing unit (tracker row); the units must be those of the parser of the notes
            ugroups,uleaves=bparts.leaf_groups(p['qp'])
            if uleaves!=[list(x) for x in man2[pid]['leaves']]: raise SystemExit(f'{pid}: bparts.leaf_groups() does not reproduce the units of the parser')
            for x in r['rows']:
                q=int(re.match(r'^(\d+)',x['label']).group(1)); byq.setdefault(q,[]).append(x)
            for q,xs in byq.items():
                groups=collections.OrderedDict(); total=0; seen=set(); has_or=False
                for x in xs:
                    mk=r['leaves'].get(x['label'],0) or 0
                    isor=bool(re.match(r'^\d+O',x['label']))          # part of the OR alternative
                    has_or=has_or or isor
                    # marks of the question as a candidate can score them: the OR alternative replaces EITHER
                    if x['label'] not in seen and not isor: total+=mk
                    seen.add(x['label'])
                    f=first_in(x['sec'])
                    if f: groups.setdefault(f,[]).append((x['label'],mk))
                if not groups: continue                               # no part on a selected subsection: not in the bank
                # the tracker marks an OR alternative only where its parts have rows of their own; the question paper itself
                # is read as well, so that every question with alternatives is recognised and its marks are counted once
                pm=printed_marks(qdoc,g['q'][str(q)])
                total,eo,basis=question_marks(pm,total,has_or,f'{pid} Q{q}')
                for sec,parts in groups.items():
                    labs=[];mk=0;sl=set()
                    for lab,m_ in parts:
                        if lab in sl: continue
                        # name of the unit: all the sub-parts that its mark covers ('(a)(i)-(ii)' where one '[2]' is printed
                        # for (a)(i) and (a)(ii)); rows of an OR alternative carry a label of the tracker only
                        if lab in ugroups: l_=bparts.group_label(ugroups[lab])
                        else: l_=part_label(lab,q); fallback.append((pid,lab,l_))
                        # 'n EITHER ... OR ...': every part belongs to one alternative; name it
                        if eo and pm['whole'] and not l_.startswith(('EITHER','OR')): l_='EITHER '+l_
                        sl.add(lab); labs.append(l_); mk+=m_
                    if mk>total: raise SystemExit(f'{pid} Q{q} {sec}: {mk} marks on the subsection, {total} on the question')
                    e=dict(base); e.update(sec=sec,q=q,parts=labs,marks_sec=mk,marks_q=total,either_or=eo,marks_basis=basis,tracker_rows=len(parts),
                        other_secs=[s for s in groups if s!=sec],
                        qbands=g['q'][str(q)],mbands=g['m'][str(q)],ms_new=g['ms_new'])
                    E.append(e)
        else:
            r=res1[pid]
            for n in range(1,41):
                x=r['rows'].get(n)
                if not x: continue
                f=first_in(x['sec'])
                if not f: continue
                dup=None
                m=re.match(r'^\(identical text to (\S+) Q(\d+)\)',x['text'])
                if m: dup=[m.group(1),int(m.group(2))]
                e=dict(base); e.update(sec=f,q=n,parts=['whole question'],marks_sec=1,marks_q=1,either_or=False,tracker_rows=1,other_secs=[],
                    qbands=g['q'][str(n)],key=g['k'][str(n)],letter=r['key'][n-1],dup=dup)
                E.append(e)
    E.sort(key=sort_key)
    for i,e in enumerate(E):
        e['rid']=f"{e['sec']}|{e['sess']}|P{e['paper']}|V{e['variant']}|Q{e['q']}"
        e['seq']=i+1
    return E
if __name__=='__main__':
    E=build()
    json.dump(E,open(OUT+'/entries.json','w'))
    c=collections.Counter((e['sec'],e['paper']) for e in E)
    print('entries',len(E),'| Paper 1',sum(1 for e in E if e['paper']==1),'| Paper 2',sum(1 for e in E if e['paper']==2),'| distinct record ids',len({e['rid'] for e in E}))
    print('Paper 2 original questions',len({(e['pid'],e['q']) for e in E if e['paper']==2}))
    for s,t in SECS: print(f'  {s:6s} {t[:44]:44s} P1 {c[(s,1)]:4d}  P2 {c[(s,2)]:4d}')
    print('first:',E[0]['rid'],'| last:',E[-1]['rid'])
    print('EITHER/OR records:',[(e['rid'],e['parts'],e['marks_sec'],e['marks_q'],e['marks_basis']) for e in E if e['either_or']])
    print('units named by the tracker label only:',fallback)
