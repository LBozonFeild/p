#!/usr/bin/env python3
"""Shared helpers for the consolidated notes (dump_sec.py, mv.py, setb.py, build_notes.py, audit_notes.py).
Input: by_section.json (written by report.py from the verified findings) and tools/notes_src/<section>.txt.
notes_src/<section>.txt format:
   == ID | sub-topic title | regex | priority      sub-topic; findings lines matching the regex are filed under it
   ALSO ID | regex | priority                      extra rule for a sub-topic (lower priority number is tried first)
   - text     checklist point credited in Paper 2 mark schemes (official marking point, generalised)
   * text     checklist point needed for Paper 1 MCQs (own explanation leading to the official key)
   MOVE pid|label|ID                               manual filing of one findings line
notes_src/_overrides.txt: wording used in the notes for mixed sub-questions (out-of-scope steps removed)."""
import json, re, os, collections
WORK='/home/user/work'
REPO='/home/user/p/physics-5054-revision'
SRC=REPO+'/tools/notes_src'
DATA=REPO+'/tools/data'
SECS=[('1.1','Physical quantities and measurement techniques'),('1.2','Motion'),('1.3','Mass and weight'),('1.4','Density'),
 ('1.5.1','Balanced and unbalanced forces'),('1.5.2','Friction'),('1.5.3','Elastic deformation'),
 ('1.5.4','Circular motion'),('1.5.5','Turning effect of forces'),('1.5.6','Centre of gravity'),
 ('1.6','Momentum'),('1.7.1','Energy'),('1.7.2','Work'),('1.7.3','Energy resources'),('1.7.4','Efficiency'),('1.7.5','Power'),
 ('3.1','General properties of waves'),('3.2.1','Reflection of light'),('3.2.2','Refraction of light'),
 ('3.2.3','Thin lenses'),('3.2.4','Dispersion of light'),('3.3','Electromagnetic spectrum'),('3.4','Sound'),
 ('4.2.1','Electrical charge'),('4.2.2','Electrical current'),('4.2.3','Electromotive force and potential difference'),('4.2.4','Resistance')]
PARENTS=[('1','CHAPTER 1: MOTION, FORCES AND ENERGY'),('1.5','1.5 FORCES'),('1.7','1.7 ENERGY, WORK AND POWER'),('3','CHAPTER 3: WAVES'),
 ('3.2','3.2 LIGHT'),('4','CHAPTER 4: ELECTRICITY AND MAGNETISM'),('4.2','4.2 ELECTRICAL QUANTITIES')]
STOP=set('the a an of to in is are and or for with by on at as it its be this that from than then so not no if when which what does do into per any all each both same more less also can may will only one two three other such these those there their has have had was were been between over under about up down out off onto through during after before while where how why who whose being very much many some most least mark marks accepted example given'.split())
def is_p1(pid): return bool(re.search(r'_1\d?$',pid))
def by_section():
    for fn in (WORK+'/by_section.json',DATA+'/by_section.json'):
        if os.path.exists(fn): return json.load(open(fn,encoding='utf-8'))
    raise SystemExit('by_section.json not found: run check.py and report.py')
def load_overrides():
    ov={}
    fn=SRC+'/_overrides.txt'
    if os.path.exists(fn):
        for ln in open(fn,encoding='utf-8'):
            ln=ln.rstrip('\n')
            if not ln.strip() or ln.startswith('#'): continue
            pid,lab,text=ln.split('|',2)
            ov[f'{pid.strip()}|{lab.strip()}']=text.strip()
    return ov
def clean(t):
    t=re.sub(r'\{[FM~]\}\s*','',t)
    t=re.sub(r'\s*\[reworked[^\]]*\]','',t)
    return re.sub(r'\s+',' ',t).strip()
def load_items(sec,d=None,ov=None):
    d=d or by_section(); ov=load_overrides() if ov is None else ov
    out=[]
    for i,(pid,lab,text) in enumerate(d.get(sec,[])):
        key=f'{pid}|{lab}'
        t=clean(ov.get(key,text))
        out.append(dict(idx=i,pid=pid,lab=lab,p1=is_p1(pid),text=t,key=key,over=key in ov,sec=sec))
    return out
def read_spec(sec):
    """returns (buckets, moves). bucket = dict(id,title,rx,prio,lines,rules)."""
    fn=f'{SRC}/{sec}.txt'
    buckets=[];moves={};extra=[]
    if not os.path.exists(fn): return buckets,moves
    cur=None
    for ln in open(fn,encoding='utf-8'):
        ln=ln.rstrip('\n')
        if ln.startswith('== '):
            parts=[x.strip() for x in ln[3:].split(' | ')]
            bid,title=parts[0],parts[1]
            rx=parts[2] if len(parts)>2 else ''
            prio=float(parts[3]) if len(parts)>3 else len(buckets)
            cur=dict(id=bid,title=title,rx=rx,prio=prio,lines=[])
            buckets.append(cur)
        elif ln.startswith('ALSO '):
            parts=[x.strip() for x in ln[5:].split(' | ')]
            extra.append(dict(id=parts[0],rx=parts[1],prio=float(parts[2]) if len(parts)>2 else 99))
        elif ln.startswith('MOVE '):
            pid,lab,b=[x.strip() for x in ln[5:].split('|')]
            moves[f'{pid}|{lab}']=b
        elif ln.startswith('#') or not ln.strip():
            continue
        elif cur is not None:
            cur['lines'].append(ln)
    for b in buckets:
        b['rules']=([(b['prio'],b['rx'])] if b['rx'] else [])+[(e['prio'],e['rx']) for e in extra if e['id']==b['id']]
    return buckets,moves
def assign(items,buckets,moves):
    res=collections.OrderedDict((b['id'],[]) for b in buckets)
    order=sorted([(pr,rx,b['id']) for b in buckets for pr,rx in b.get('rules',[])],key=lambda x:x[0])
    catch=[b['id'] for b in buckets if not b.get('rules')]
    ids=set(res)
    for it in items:
        b=moves.get(it['key'])
        if b is not None and b not in ids: raise SystemExit(f'MOVE to unknown bucket {b} for {it["key"]}')
        if b is None:
            for pr,rx,bid in order:
                if re.search(rx,it['text'],re.I): b=bid; break
        if b is None:
            b=catch[0] if catch else '?'
            if b=='?': res.setdefault('?',[])
        it['bucket']=b
        res[b].append(it)
    return res
SYN={'velocity':'speed','deceleration':'acceleration','decelerat':'acceleration','accelerat':'acceleration','decelerate':'acceleration','accelerate':'acceleration',
 'retardation':'acceleration','drag':'resistance','gradient':'slope','mass':'mass','weigh':'weight','gravitational':'gravity','straight-line':'straight',
 'larger':'greater','bigger':'greater','higher':'greater','increase':'increas','decrease':'decreas','smaller':'less','lower':'less','reduce':'decreas','reduc':'decreas','rise':'increas','fall':'decreas'}
def toks(t):
    t=t.lower()
    t=re.sub(r'\[[a-z]?\d\]|\([a-z]\d\)','',t)
    w=re.findall(r'[a-zλρθμωδ]+',t)
    out=set()
    for x in w:
        if len(x)<3 or x in STOP: continue
        for suf in ('ing','ed','es','s'):
            if len(x)>4 and x.endswith(suf): x=x[:-len(suf)]; break
        out.add(SYN.get(x,x))
    return out
def is_calc(t):
    return bool(re.search(r'\d\s*[×÷]\s*[\d(]|=\s*\(?\d[\d ,.]*\s*[×÷+−/]',t))
def normkey(t):
    return re.sub(r'[\d.,×÷=+\-−–⁻⁰¹²³⁴⁵⁶⁷⁸⁹ ]+','#',t.lower())
def collapse(items,contain=True):
    """group items that say the same thing: (1) identical once numbers are ignored; (2) every content word of the item is
    already in a longer item of the same kind (Paper 2: all words; Paper 1: at least 85 %). Returns [(rep,[hidden…])]."""
    groups=collections.OrderedDict()
    for it in items:
        groups.setdefault((it['p1'],normkey(it['text'])),[]).append(it)
    gs=[[g[0],g[1:]] for g in groups.values()]
    if not contain: return [(a,b) for a,b in gs]
    order=sorted(range(len(gs)),key=lambda i:-len(toks(gs[i][0]['text'])))
    keep=[]
    for i in order:
        rep,hid=gs[i]; T=toks(rep['text']); done=False
        if T:
            for k in keep:
                if k[0]['p1']!=rep['p1']: continue
                c=len(T&k[2])/len(T)
                if c>=(0.85 if rep['p1'] else 1.0):
                    k[1].extend([rep]+hid); done=True; break
        if not done: keep.append([rep,hid,T,i])
    keep.sort(key=lambda k:k[3])
    return [(k[0],k[1]) for k in keep]
def chain(groups):
    """greedy nearest-neighbour ordering so that related points sit together; worded points first, calculations after."""
    def run(gs):
        if not gs: return []
        T=[toks(g[0]['text']) for g in gs]
        n=len(gs); used=[False]*n; seq=[0]; used[0]=True; cur=0
        for _ in range(n-1):
            best=-1;bs=-1.0
            for j in range(n):
                if used[j]: continue
                s=len(T[cur]&T[j])/(len(T[cur]|T[j]) or 1)
                if s>bs: bs=s;best=j
            used[best]=True; seq.append(best); cur=best
        return [gs[i] for i in seq]
    words=[g for g in groups if not is_calc(g[0]['text'])]
    calcs=[g for g in groups if is_calc(g[0]['text'])]
    return run(words)+run(calcs)
def src_tag(pid,lab):
    sess,comp=pid.split('_')
    if lab.startswith('MCQ'): q='Q'+lab[3:]
    else:
        m=re.match(r'^(\d+)(E)?([a-h])?([ivx]+)?$',lab)
        if m: q='Q'+m.group(1)+(' EITHER' if m.group(2) else '')+(f'({m.group(3)})' if m.group(3) else '')+(f'({m.group(4)})' if m.group(4) else '')
        else: q='Q'+lab
    return f'{sess}/{comp} {q}'
