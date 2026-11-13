#!/usr/bin/env python3
"""build_notes.py — assemble physics_papers_1_2_notes.txt from tools/notes_src/<section>.txt.
Each sub-topic prints its Paper 2 marking points ('- ' lines) and then its Paper 1 multiple-choice points ('* ' lines)
as lines that start with a dash.  Order of sub-topics: the 'ORDER' line of the section file (default: file order).
The script refuses to build if a sub-topic that holds findings has no checklist, or if the catch-all 'Z' holds findings."""
import sys, re, textwrap
from notes_lib import *
OUT=REPO+'/physics_papers_1_2_notes.txt'
W=100
KEEP=['ΔEp = mgΔh','Ek = ½mv²','n = sin i ÷ sin r','P = E ÷ t','W = mg','F = ma','E = Pt','v = fλ','f = 1/T','Q = It','W = QV',
      'R = V/I','V = IR','e.m.f.','p.d.']
def caps(t):
    for i,k in enumerate(KEEP): t=t.replace(k,f'\x00{i}\x00')
    t=t.upper()
    for i,k in enumerate(KEEP): t=t.replace(f'\x00{i}\x00',k)
    return t
def order_of(sec,buckets):
    ids=[b['id'] for b in buckets]
    first=open(f'{SRC}/{sec}.txt',encoding='utf-8').readline().strip()
    if first.startswith('ORDER '):
        o=first.split()[1:]
        assert sorted(o)==sorted(ids),(sec,o,ids)
        return o
    return ids
# a number is kept on the same line as the unit that follows it
UNIT_RX=re.compile(r'(?<=\d) (?=(?:m/s²|m/s|km/h|N/kg|N/m|N/cm|kg/m³|g/cm³|J/C|J/s|kW h|N m|kHz|MHz|Hz|kΩ|Ω|°C|mA|kW|MW|kJ|MJ|kN|kV|mV|kg|km|cm|mm|ms|min|Pa|m|s|g|h|N|J|W|V|A|C|K|%)(?![A-Za-z0-9]))')
# a short formula such as R = V/I or Q = It is not split at the equals sign
EQ_RX=re.compile(r'(?<![A-Za-z.])([A-Za-zλρΔ]{1,3}) = (?=\S)')
def wrap(prefix,text):
    text=UNIT_RX.sub('\u00a0',text)
    text=EQ_RX.sub(lambda m:m.group(1)+'\u00a0=\u00a0',text)
    # checklist lines start with a dash, so a wrapped line must not begin with a dash or a minus sign: both stay with the word before
    text=text.replace(' – ','\u00a0– ').replace(' − ','\u00a0− ')
    out=textwrap.fill(text,width=W,initial_indent=prefix,subsequent_indent=' '*len(prefix),break_long_words=False,break_on_hyphens=False)
    return out.replace('\u00a0',' ')
def sections():
    """yields (sec,title,[(bucket,p2lines,p1lines,n_items)])"""
    d=by_section(); ov=load_overrides()
    for sec,title in SECS:
        buckets,moves=read_spec(sec)
        res=assign(load_items(sec,d,ov),buckets,moves)
        bid={b['id']:b for b in buckets}
        rows=[]
        for i in order_of(sec,buckets):
            b=bid[i]
            p2=[l[2:].strip() for l in b['lines'] if l.startswith('- ')]
            p1=[l[2:].strip() for l in b['lines'] if l.startswith('* ')]
            bad=[l for l in b['lines'] if not (l.startswith('- ') or l.startswith('* '))]
            assert not bad,(sec,i,bad[:2])
            rows.append((b,p2,p1,res.get(i,[])))
        yield sec,title,rows
def main():
    out=[];problems=[];np2=np1=nsub=0
    bar='='*W; thin='-'*W
    out+=[bar,'CAMBRIDGE O LEVEL PHYSICS 5054 — PAPERS 1 AND 2','REVISION CHECKLIST BUILT FROM THE MARK SCHEMES',bar,'',
    'WHAT THIS FILE COVERS','']
    out.append(wrap('  ','Chapter 1 Motion, forces and energy: sections 1.1 to 1.7 (pressure, section 1.8, is not included). '
      'Chapter 3 Waves: sections 3.1 to 3.4. Chapter 4 Electricity and magnetism: section 4.2 Electrical quantities only '
      '(charge, current, e.m.f. and potential difference, resistance).'))
    out.append('')
    out.append(wrap('  ','Only the content of these sections is included. Where a question on one of them also needed a rule from another '
      'section, that step is left out: the rules for series and parallel circuits and for sharing the p.d. in a potential divider (section 4.3), '
      'electrical power P = IV and the cost of electricity (section 4.4), and nuclear fusion in the Sun (chapters 5 and 6). '
      'In the resistance checklists the total resistance of a circuit, or the p.d. across a component and the current in it, '
      'are therefore treated as known quantities. The kilowatt-hour belongs to section 4.4; it appears under 1.7.5 only as a '
      'unit of energy used with E = Pt.'))
    out.append('')
    out.append(wrap('  ','Some points come from older papers, set on earlier versions of the syllabus, and are not named in the syllabus '
      'for 2026 to 2028. The main ones are: vernier calipers and vector diagrams for two vectors that are not at right angles (1.1); ticker-tape '
      'timers (1.2); the camera, the projector and the photographic enlarger (3.2.3); and the three sub-topics of 4.2.1 marked '
      '"earlier syllabuses" (induced charges; earthing and charging by induction; static electricity in practice).'))
    out+=['','HOW TO READ THE CHECKLISTS','']
    for t in [
     'Every line that starts with a dash (-) is one point to learn.',
     'PAPER 2 MARKING POINTS are the answers that the mark schemes for the structured paper give credit for. The same point asked in several papers is written once, in general wording. Alternatives that the schemes accept, and answers they ignore or reject, are kept with the point.',
     'PAPER 1 MULTIPLE-CHOICE POINTS are short explanations of the ideas that lead to the correct option in the multiple-choice paper. A multiple-choice mark scheme gives only the letter of the answer, so these lines are explanations written for these notes and are not official marking points.',
     'Numbers inside a point are examples of the method; in an examination use the data of the question.']:
        out.append(wrap('  • ',t))
    out+=['','MARK CODES USED IN THE PAPER 2 POINTS','']
    for t in [
     '(B1) an independent mark: given for that statement or value on its own.',
     '(C1) a compensation mark for a correct step of the method (formula, substitution or intermediate value). It is also given automatically when the final answer is correct, so working protects marks when the answer is wrong.',
     '(M1) a method mark: the step must be seen. The (A1) that follows it cannot be given unless the M1 is earned.',
     '(A1) an answer mark: the correct final answer or the final part of an explanation, usually with its unit.',
     '(1) one mark, in schemes that print no letter code.',
     'Codes joined by "or", such as (B1 or M1), show that different schemes used different codes for the same point.',
     '"any two", "two of", "three points": only that number of the listed points is needed for full marks.',
     'ecf: error carried forward – a wrong earlier answer used correctly in a later step can still earn the later marks.',
     '"accepted", "ignored", "not accepted / rejected": ignored answers neither gain nor lose the mark; rejected answers lose it.']:
        out.append(wrap('  • ',t))
    toc=[];body=[]
    chapter=None;parent=None
    PAR=dict(PARENTS)
    for sec,title,rows in sections():
        ch=sec.split('.')[0]
        if ch!=chapter:
            chapter=ch;parent=None
            body+=['','',bar,PAR[ch],bar]; toc+=['',PAR[ch]]
        par='.'.join(sec.split('.')[:2])
        if len(sec.split('.'))==3 and par!=parent:
            parent=par
            body+=['','',PAR[par],'~'*len(PAR[par])]; toc.append('  '+PAR[par])
        elif len(sec.split('.'))==2: parent=None
        head=f'{sec} {caps(title)}'
        body+=['','',thin,head,thin]
        toc.append(('    ' if len(sec.split('.'))==3 else '  ')+head)
        for b,p2,p1,items in rows:
            if b['id']=='Z':
                if items or p2 or p1: problems.append(f'{sec}: catch-all Z holds {len(items)} findings line(s) / {len(p2)+len(p1)} checklist line(s)')
                continue
            if not items and not (p2 or p1): continue
            if items and not (p2 or p1): problems.append(f'{sec} {b["id"]}: {len(items)} findings line(s) but no checklist'); continue
            if (p2 or p1) and not items: problems.append(f'{sec} {b["id"]}: checklist without findings lines')
            n2=sum(1 for it in items if not it['p1']); n1=len(items)-n2
            if p2 and not n2: problems.append(f'{sec} {b["id"]}: Paper 2 points but no Paper 2 findings filed here')
            if p1 and not n1: problems.append(f'{sec} {b["id"]}: Paper 1 points but no Paper 1 findings filed here')
            nsub+=1
            body+=['',caps(b['title']),'']
            if p2:
                body.append('  Paper 2 marking points'); np2+=len(p2)
                body+=[wrap('  - ',t) for t in p2]
            if p1:
                if p2: body.append('')
                body.append('  Paper 1 multiple-choice points (explanations, not official marking points)'); np1+=len(p1)
                body+=[wrap('  - ',t) for t in p1]
    out+=['','CONTENTS']+toc+body+['','',bar,'END OF NOTES',bar]
    if problems:
        print('NOT BUILT —',len(problems),'problem(s):'); print('\n'.join(problems)); sys.exit(1)
    open(OUT,'w',encoding='utf-8').write('\n'.join(out)+'\n')
    print(f'wrote {OUT}: {len(out)} lines; {nsub} sub-topics; {np2} Paper 2 marking points; {np1} Paper 1 points; {np2+np1} checklist lines')
if __name__=='__main__': main()
