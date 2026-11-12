#!/usr/bin/env python3
"""audit_notes.py — checks of physics_papers_1_2_notes.txt against the verified findings (word matching; no reading).
 A  structure: every findings line (after the wording of notes_src/_overrides.txt) is filed in a sub-topic that has a checklist;
    the catch-all Z is empty; the notes file holds exactly the checklist lines of notes_src (no line missing, none extra).
 B  coverage (findings -> notes): for every Paper 2 marking point and every Paper 1 line, the share of its content words found
    (a) in the best single checklist line of its sub-topic and (b) in all checklist lines of its sub-topic.
    A point is flagged when (b) < 0.75 or (a) < 0.5.  A flagged point passes without being read if one checklist line of the
    section family (the section and its sister sections, e.g. 1.5.1-1.5.6) covers at least 0.6 of its words ("matched
    elsewhere"), or if at least 0.75 of its words other than exam-technique words occur across the family ("spread").
    The rest must be read: the notes are corrected, or the point is listed in notes_src/_audit_ok.txt with the reason.
 C  support (notes -> findings): for every checklist line, the share of its content words (exam-technique words ignored) found
    in the findings of the section family: Paper 2 findings for '- ' lines, Paper 1 and Paper 2 findings for '* ' lines.
    A line is flagged when the share is below 0.8 or when three or more words are unsupported; flagged lines are read and either
    corrected or listed in _audit_ok.txt.  Numbers in a checklist line must occur in the findings of the same section
    (small common numbers are ignored).
 D  references and scope: the notes text from CONTENTS onwards is scanned for paper identifiers, sessions, years and question
    or figure numbers; the checklist lines are scanned for words that belong to syllabus sections outside the selected ones
    (SCOPE, which includes the rules for series and parallel circuits).  Each hit must lie in a context that was read and
    accepted (SCOPE_OK: word -> sections).
Writes work/notes_audit.txt (full lists) and prints a summary.  _audit_ok.txt keys: B|section|pair|label|point index,
C|section|sub-topic|first 60 characters of the line, N|... (numbers); changing the start of a line makes its key stale."""
import sys, re, os, collections
from notes_lib import *
import build_notes
NOTES=REPO+'/physics_papers_1_2_notes.txt'
OKF=SRC+'/_audit_ok.txt'
detail=len(sys.argv)>1
def points(it):
    if it['p1']: return [it['text']]
    return [p.strip() for p in it['text'].split(' ;; ') if p.strip()]
def nums(t):
    t=re.sub(r'\([BCMA]?\d\)|\[[BCMA]?\d\]','',t)
    t=re.sub(r'(?<=\d) (?=\d{3}\b)','',t)
    return set(x.rstrip('.') for x in re.findall(r'\d+(?:\.\d+)?',t))
ok=set()
if os.path.exists(OKF):
    for ln in open(OKF,encoding='utf-8'):
        ln=ln.rstrip('\n')
        if ln and not ln.startswith('#'): ok.add(ln.split('\t')[0])
rep=[];summ=collections.OrderedDict()
d=by_section(); ov=load_overrides()
tot_items=0; tot_points=0; filed=0
lowB=[]; lowC=[]; numC=[]; allp2=[];allp1=[]
histB=collections.Counter()
SMALL=set('0 1 2 3 4 5 6 7 8 9 10 12 20 100 1000 60 90 180 360 50 30 45 0.5 1.0 2.0 3.0 4.0 5.0 10.0 25 75 15 40 80'.split())
ALL=[]
META=set('answer use change find first substitut substitution formula equation version scheme schem question separate credit accept ignor ignore recent older own alone ask asks need step calculation calculate work value valu correct correctly earn typical typically usually often sometim single necessary state stat give giv must they either rearrang rearrangement convert method route alternative allow requir result read reading us total new point version full fuller part form final quote quot written writ show shown wrong unit'.split())
SECW={}
for sec,title,rows in build_notes.sections():
    w={True:set(),False:set()}
    for b,p2,p1,items in rows:
        for it in items: w[it['p1']]|=toks(it['text'])
    SECW[sec]=w
def fam(sec):
    p='.'.join(sec.split('.')[:2])
    return [s for s in SECW if s==sec or (len(sec.split('.'))==3 and s.startswith(p+'.'))]
for sec,title,rows in build_notes.sections():
    for b,p2,p1,items in rows:
        for l in p2+p1: ALL.append((sec,b['id'],toks(l)))
elsewhere=[];spread=[];okB=[];okC=0;okN=0
for sec,title,rows in build_notes.sections():
    items_all=[it for b,p2,p1,items in rows for it in items]
    secnums={True:set(),False:set()}
    for it in items_all: secnums[it['p1']]|=nums(it['text'])
    for b,p2,p1,items in rows:
        tot_items+=len(items)
        if b['id']=='Z':
            if items: rep.append(f'A FAIL {sec}: Z holds {len(items)} line(s)')
            continue
        if items and not (p2 or p1): rep.append(f'A FAIL {sec} {b["id"]}: no checklist'); continue
        filed+=len(items)
        L2=[toks(l) for l in p2]; L1=[toks(l) for l in p1]
        U=set().union(*L2,*L1) if (L2 or L1) else set()
        I2=set();I1=set()
        for it in items:
            if it['p1']: I1|=toks(it['text'])
            else: I2|=toks(it['text'])
        # B: findings -> notes
        for it in items:
            lines=(L1+L2) if it['p1'] else (L2+L1)
            for k,p in enumerate(points(it)):
                T=toks(p); tot_points+=1
                if not T: histB['no words']+=1; continue
                best=max((len(T&l)/len(T) for l in lines),default=0)
                un=len(T&U)/len(T)
                histB['best>=0.8' if best>=0.8 else 'best>=0.6' if best>=0.6 else 'best<0.6']+=1
                if un<0.75 or best<0.5:
                    key=f'B|{sec}|{it["key"]}|{k}'
                    if key in ok: okB.append(key); continue
                    F=[x for x in ALL if x[0] in fam(sec)]
                    g=max(F,key=lambda x:len(T&x[2])/len(T))
                    gb=len(T&g[2])/len(T)
                    FU=set().union(*[x[2] for x in F])
                    fu=len((T-META)&FU)/max(1,len(T-META))
                    if gb>=0.6: elsewhere.append((key,b['id'],p,g[0],g[1])); continue
                    if fu>=0.75: spread.append((key,b['id'],p)); continue
                    lowB.append((fu,gb,key,b['id'],p,sorted(T-META-FU)))
        # C: notes -> findings
        for kind,lines_,I in (('-',p2,I2),('*',p1,I1|I2)):
            for l in lines_:
                (allp2 if kind=='-' else allp1).append((sec,b['id'],l))
                T=toks(l)-META
                if not T: continue
                I=set()
                for s_ in fam(sec):
                    I|=SECW[s_][False]
                    if kind=='*': I|=SECW[s_][True]
                c=len(T&I)/len(T)
                key=f'C|{sec}|{b["id"]}|{l[:60]}'
                if (c<0.8 or len(T-I)>=3):
                    if key in ok: okC+=1
                    else: lowC.append((c,key,kind,l,sorted(T-I)))
                nn=nums(l)-SMALL
                miss=sorted(n for n in nn if n not in secnums[False] and n not in secnums[True]) if kind=='*' else sorted(n for n in nn if n not in secnums[False])
                keyn=f'N|{sec}|{b["id"]}|{l[:60]}'
                if miss:
                    if keyn in ok: okN+=1
                    else: numC.append((keyn,kind,l,miss))
# A: notes file holds exactly the checklist lines
txt=open(NOTES,encoding='utf-8').read()
flat=[];cur=None
for ln in txt.split('\n'):
    if ln.startswith('  - '): cur=ln[4:]; flat.append(cur)
    elif ln.startswith('    ') and flat and cur is not None: flat[-1]+=' '+ln.strip()
    else: cur=None
want=[l for _,_,l in allp2]+[l for _,_,l in allp1]
cw=collections.Counter(re.sub(r'\s+',' ',x) for x in want); cf=collections.Counter(re.sub(r'\s+',' ',x) for x in flat)
if cw!=cf: rep.append(f'A FAIL notes file differs from notes_src: {sum((cw-cf).values())} missing, {sum((cf-cw).values())} extra checklist lines')
# D: references and scope
body=txt.split('END OF NOTES')[0]
start=body.index('CONTENTS')
chk=body[start:]
REF=[(r'\b[sw]\d\d_\d','paper id'),(r'5054_','file name'),(r'\b(May|June|October|November|Oct/Nov|May/June)\b','session'),
     (r'\b(200[4-9]|201\d|202[0-6])\b(?! ?(Ω|Hz|m/s|N|J|W|kg|m\b|s\b|C\b|V\b|A\b|Pa|°))','year-like number'),(r'\bQ\d+\b|\bQuestion \d|\bFig\.',' question/figure reference'),
     (r'\bvariant\b|\bPaper \d\d\b|\bMS\b|\bQP\b','paper reference')]
SCOPE=r'P = VI|P = IV|(?-i:VIt)|V²/R|I²R|P/V|kW ?h|kilowatt|\bcost\b|\bfuse|live wire|neutral wire|transformer|half-life|radioactiv|alpha|beta|gamma|nucle|specific heat|latent|\bpressure|oscilloscope|c\.r\.o|time-base|magnetic|magnet\b|relay|transistor|potential divider|thermistor|\bLDR|diode|\bLED\b|capacitor|logic gate|planet|galax|\bstars?\b|thermal|conduction|convection|evaporat|molecul|kinetic theory|\bgas(es)?\b|Boyle|hρg|manometer|barometer|induced e\.m\.f|generator|motor\b|solenoid|electromagnet|1/R\b|branch|junction|short.circuit|combined resistance|sum of the p\.d|share of the p\.d|shares? the (?:supply )?p\.d|ratio of the resistances|proportion to their resistances|resistors? (?:are |connected )?in (?:series|parallel)|(?:lamps|components) (?:are |connected )?in (?:series|parallel)|parallel (?:pair|combination|branch|circuit|resistor)|series (?:circuit|resistor|resistance|combination|current)|fusion|fission'
refhits=[]
for ln in chk.split('\n'):
    for rx,name in REF:
        for m in re.finditer(rx,ln):
            refhits.append((name,m.group(0),ln.strip()[:150]))
# words that belong to other syllabus sections but are legitimate context inside the sections listed (each context was read)
SCOPE_OK={'gamma':'3.1 3.3 3.4','electromagnet':'1.7.1 1.7.3 3.1 3.3 3.4 4.2.4','gas':'1.4 1.5.1 1.6 1.7.1 1.7.3 3.3 3.4','gases':'1.7.3 3.3 3.4',
 'generator':'1.7.1 1.7.3 1.7.4 3.4','kilowatt':'1.7.5','kw h':'1.7.5','kwh':'1.7.5','ldr':'4.2.2 4.2.4','thermistor':'4.2.4','magnet':'1.5.1',
 'magnetic':'1.5.1 3.3 4.2.1','molecul':'3.1 3.4','motor':'1.7.1 1.7.2 1.7.4 4.2.2 4.2.4','diode':'4.2.4','parallel pair':'4.2.3','nucle':'1.5.4 1.7.1 1.7.3','oscilloscope':'3.4',
 'planet':'1.3 1.5.3 1.5.4','potential divider':'4.2.4','pressure':'1.5.1 1.7.3 3.1 3.4','radioactiv':'1.7.3 3.3',
 'thermal':'1.5.2 1.7.1 1.7.2 1.7.3 1.7.4 3.3','transformer':'1.7.3','conduction':'3.3','convection':'3.3','cost':'1.7.3','fuse':'1.7.3'}
scopehits=collections.Counter(); scopelines=[]
for sec_,b_,l in allp2+allp1:
    for m in re.finditer(SCOPE,l,re.I):
        w=m.group(0).lower(); scopehits[(sec_,w)]+=1
        if sec_ not in SCOPE_OK.get(w,'').split(): scopelines.append((f'S|{sec_}|{b_}|{w}|{l[:50]}',l))
out=[]
out.append(f'findings lines: {tot_items} | filed in a sub-topic with a checklist: {filed} | marking points / MCQ lines checked: {tot_points}')
out.append(f'checklist lines: Paper 2 {len(allp2)}, Paper 1 {len(allp1)} | lines that start with a dash in the notes file: {len(flat)}')
out.append('coverage of findings points by the best single checklist line: '+', '.join(f'{k} {v}' for k,v in sorted(histB.items())))
out.append(f'A structure problems: {len(rep)}')
out+=rep
out.append(f'B findings points below the threshold in their own sub-topic: matched by one checklist line elsewhere in the section (or its sister sections): {len(elsewhere)} | content words found across several lines of the section: {len(spread)} | accepted after reading (listed in _audit_ok.txt): {len(okB)}')
out.append(f'B findings points still to be read by hand: {len(lowB)}')
out.append(f'C checklist lines whose content words are not all found in the findings of the section: accepted after reading {okC}, still to be read {len(lowC)} | lines with numbers not found in the section findings: accepted after reading {okN}, still to be read {len(numC)}')
out.append(f'D reference-like strings (paper ids, sessions, years, question or figure numbers): {len(refhits)} | words from other syllabus sections: {sum(scopehits.values())} occurrences, of which outside the reviewed contexts: {len(scopelines)}')
print('\n'.join(out))
full=out[:]
full.append('\n== B low coverage (union, best, key, sub-topic, point, words missing)')
for un,best,key,bid,p,miss in sorted(lowB): full.append(f'{un:.2f} {best:.2f}\t{key}\t{bid}\t{p}\t{" ".join(miss)}')
full.append('\n== B matched elsewhere (key, own sub-topic, point, section and sub-topic of the matching line)')
for key,bid,p,gs,gbk in elsewhere: full.append(f'{key}\t{bid}\t{p}\t{gs} {gbk}')
full.append('\n== C weak support (share, key, kind, line, unsupported words)')
for c,key,kind,l,miss in sorted(lowC): full.append(f'{c:.2f}\t{key}\t{kind}\t{l}\t{" ".join(miss)}')
full.append('\n== C numbers not found')
for key,kind,l,miss in numC: full.append(f'{key}\t{kind}\t{l}\t{" ".join(miss)}')
full.append('\n== D references')
for x in refhits: full.append('\t'.join(x))
full.append('\n== D scope keywords')
for key,l in scopelines: full.append(f'{key}\t{l}')
os.makedirs(WORK,exist_ok=True)
open(WORK+'/notes_audit.txt','w',encoding='utf-8').write('\n'.join(full)+'\n')
