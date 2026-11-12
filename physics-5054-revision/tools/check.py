# Validate findings, build tracker / checkpoint / draft-notes / exclusions.  Usage: check.py [quiet]
from lib import *
import collections, datetime
REPO='/home/user/p/physics-5054-revision'
FD=REPO+'/findings'
pairs,excl=list_pairs()
man2=json.load(open(WORK+'/p2_manifest.json'))
man1=json.load(open(WORK+'/p1_manifest.json')) if os.path.exists(WORK+'/p1_manifest.json') else {}
keys=json.load(open(WORK+'/keys_p1.json'))
q1=json.load(open(WORK+'/p1_questions.json'))
dup=json.load(open(WORK+'/p1_dupmap.json'))
hdr=json.load(open(WORK+'/header_check.json'))
INSEC=['1.1','1.2','1.3','1.4','1.5.1','1.5.2','1.5.3','1.5.4','1.5.5','1.5.6','1.6','1.7.1','1.7.2','1.7.3','1.7.4','1.7.5','3.1','3.2.1','3.2.2','3.2.3','3.2.4','3.3','3.4','4.2.1','4.2.2','4.2.3','4.2.4']
TAG=re.compile(r'\[(?:[BCMAx]?)(\d)\]')
def parse_p2(pid):
    fn=f'{FD}/p2/{pid}.txt'
    if not os.path.exists(fn): return None
    rows=[];notes=[];over={}
    for ln in open(fn):
        ln=ln.rstrip('\n')
        if not ln.strip(): continue
        if ln.startswith('#'): notes.append(ln[1:].strip()); continue
        if ln.startswith('!marks'):   # override leaf marks:  !marks 7Ea=2 7Eb=3
            for tok in ln.split()[1:]:
                a,b=tok.split('='); over[a]=int(b)
            continue
        parts=[x.strip() for x in ln.split('|',2)]
        if len(parts)<3: rows.append(dict(label=parts[0],sec='?',text=ln,bad=True)); continue
        rows.append(dict(label=parts[0],sec=parts[1],text=parts[2]))
    return rows,notes,over
def parse_p1(pid):
    fn=f'{FD}/p1/{pid}.txt'
    if not os.path.exists(fn): return None
    rows={};notes=[]
    for ln in open(fn):
        ln=ln.rstrip('\n')
        if not ln.strip(): continue
        if ln.startswith('#'): notes.append(ln[1:].strip()); continue
        m=re.match(r'^(\d{1,2})\s+([ABCD?])\s+(\S+)\s*(.*)$',ln)
        if not m: notes.append('UNPARSED: '+ln); continue
        rows[int(m.group(1))]=dict(ans=m.group(2),sec=m.group(3),text=m.group(4))
    return rows,notes
def insec(sec):
    return any(s in INSEC for s in sec.split('+'))
res2={};res1={}
for p in pairs:
    pid=p['id']
    if p['paper']==2:
        m=man2[pid]; f=parse_p2(pid)
        r=dict(pid=pid,status='NOT STARTED',issues=[])
        leaves=collections.OrderedDict((l,k) for l,k in m['leaves'])
        r.update(nq=m['nq'],nleaf=len(leaves),qp_marks=sum(leaves.values()))
        if f:
            rows,notes,over=f
            for a,b in over.items(): leaves[a]=b
            if over: r['qp_marks']=sum(leaves.values()); r['nleaf']=len(leaves)
            got=collections.OrderedDict()
            for x in rows:
                got.setdefault(x['label'],[]).append(x)
            missing=[l for l in leaves if l not in got]
            extra=[l for l in got if l not in leaves]
            if missing: r['issues'].append('leaf parts without findings: '+','.join(missing))
            if extra: r['issues'].append('findings labels not in QP parse: '+','.join(extra))
            n_in=n_out=mk_in=mk_out=pts=figs=0;mm=[]
            for l,xs in got.items():
                lm=leaves.get(l)
                tagsum=0;anyin=False
                for x in xs:
                    if insec(x['sec']):
                        anyin=True
                        tg=[int(d) for d in TAG.findall(x['text'])]
                        tagsum+=sum(tg); pts+=len(tg)
                    if '{F}' in x['text'] or '{M}' in x['text']: figs+=1
                if anyin:
                    n_in+=1; mk_in+=(lm or 0)
                    if lm is not None and tagsum!=lm and not any('{~}' in x['text'] for x in xs): mm.append(f'{l}:tags={tagsum},qp={lm}')
                else:
                    n_out+=1; mk_out+=(lm or 0)
            if mm: r['issues'].append('mark-tag sum mismatch: '+'; '.join(mm))
            r.update(n_in=n_in,n_out=n_out,mk_in=mk_in,mk_out=mk_out,pts=pts,figs=figs,notes=notes,rows=rows,leaves=leaves)
            r['status']='COMPLETE' if not r['issues'] else 'ISSUES'
        res2[pid]=r
    else:
        f=parse_p1(pid)
        r=dict(pid=pid,status='NOT STARTED',issues=[])
        if f:
            rows,notes=f
            key=keys[pid]['key']
            agree=dis=unsolved=dupn=n_in=figs=0;disl=[];missing=[]
            full={}
            for n in range(1,41):
                d=dup.get(f'{pid}#{n}')
                x=rows.get(n)
                if x is None and d:
                    # resolve by identity to earlier verified question
                    f2=parse_p1(d[0])
                    if f2 and d[1] in f2[0]:
                        y=f2[0][d[1]]
                        x=dict(ans=y['ans'],sec=y['sec'],text=f'(identical text to {d[0]} Q{d[1]}) '+y['text'],dup=True); dupn+=1
                if x is None: missing.append(n); continue
                full[n]=x
                if insec(x['sec']): n_in+=1
                if '{F}' in x['text']: figs+=1
                if x['ans']=='?': unsolved+=1
                elif x['ans']==key[n-1]: agree+=1
                else:
                    if '!resolved' in x['text']: agree+=0; dis+=0; r.setdefault('resolved',[]).append(n)
                    else: dis+=1; disl.append(f'Q{n}: mine {x["ans"]} vs key {key[n-1]}')
            if missing: r['issues'].append('questions without findings: '+','.join(map(str,missing)))
            if disl: r['issues'].append('unresolved answer disagreements: '+'; '.join(disl))
            r.update(agree=agree,dis=dis,unsolved=unsolved,dupn=dupn,n_in=n_in,figs=figs,notes=notes,rows=full,key=key)
            r['status']='COMPLETE' if not r['issues'] else 'ISSUES'
        res1[pid]=r
json.dump(dict(p1={k:{a:b for a,b in v.items() if a not in('rows',)} for k,v in res1.items()},p2={k:{a:b for a,b in v.items() if a not in('rows','leaves')} for k,v in res2.items()}),open(WORK+'/status.json','w'))
c2=collections.Counter(r['status'] for r in res2.values()); c1=collections.Counter(r['status'] for r in res1.values())
print('P2:',dict(c2),'| P1:',dict(c1))
for r in list(res2.values())+list(res1.values()):
    if r['issues']: print('  ',r['pid'],r['issues'])
import pickle
pickle.dump(dict(res1=res1,res2=res2,pairs=pairs,excl=excl,man2=man2,hdr=hdr,keys=keys),open(WORK+'/state.pkl','wb'))
