#!/usr/bin/env python3
"""breports.py — tracker, exclusions and audit of the question bank, as text and as PDF  -> ../../question_bank/

  physics_5054_question_bank_tracker.txt / .pdf      one line per record in the bank and per question left out
  physics_5054_question_bank_exclusions.txt / .pdf   what is not in the bank, and why
  physics_5054_question_bank_audit.txt / .pdf        counts, reconciliation, results of the automated checks, record of
                                                     the visual review, limits

Everything is computed here from
  WORK/bank/entries.json, manifest.json     written by bbuild.py together with the PDF
  WORK/bank/geom.json, geom_check.json      crop geometry and its tests (bgeom.py, bcheck_geom.py)
  WORK/bank/verify.json                     checks of the finished PDF (bverify.py)
  WORK/state.pkl                            the verified findings of the paper-by-paper verification (../check.py)
  ../data/bank_unpaired_questions.json      questions of the papers without a mark scheme (bunpaired.py)
  visual_review.txt                         record of the inspection by eye (written by hand; copied into the audit)
The audit states FAIL, and this script exits with 1, if a reconciliation fails, if a check failed, or if the results
of the checks do not belong to the PDF that is on disk (the hash of the PDF and of the geometry are compared)."""
import sys, os, re, json, pickle, collections, datetime, hashlib
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(HERE))
from lib import *
import notes_lib, bentries
OUT=WORK+'/bank'; REPO='/home/user/p/physics-5054-revision'; QB=REPO+'/question_bank'; DATA=REPO+'/tools/data'
BANK='physics_5054_past_paper_questions_with_ms.pdf'
STEM='physics_5054_question_bank_'
SECS=notes_lib.SECS; SECT=dict(SECS); ORDER={s:i for i,(s,_) in enumerate(SECS)}
CHAPTER=bentries.CHAPTER
XNAME={'X1.8':'1.8 Pressure','X2.1':'2.1 Kinetic particle model of matter','X2.2':'2.2 Thermal properties and temperature',
       'X2.3':'2.3 Transfer of thermal energy','X4.1':'4.1 Simple magnetism and magnetic fields','X4.3':'4.3 Electric circuits',
       'X4.4':'4.4 Practical electricity','X4.5':'4.5 Electromagnetic effects','X4.6':'4.6 Uses of an oscilloscope',
       'X5':'5 Nuclear physics','X6':'6 Space physics','XOLD':'earlier-syllabus content (not in the 2026-2028 syllabus)'}
XORDER=['X1.8','X2.1','X2.2','X2.3','X4.1','X4.3','X4.4','X4.5','X4.6','X5','X6','XOLD']
def first_in(sec):
    for s in sec.split('+'):
        if s in ORDER: return s
    return None
def rng(ps):
    """[3,4,5,8] -> '3-5, 8'"""
    ps=sorted(set(ps)); out=[]; i=0
    while i<len(ps):
        j=i
        while j+1<len(ps) and ps[j+1]==ps[j]+1: j+=1
        out.append(str(ps[i]) if i==j else f'{ps[i]}-{ps[j]}'); i=j+1
    return ', '.join(out)
def sname(sess): return 'May/June' if sess[0]=='s' else 'October/November'
def sshort(sess): return 'May/Jun' if sess[0]=='s' else 'Oct/Nov'
def xcodes(codes):
    """codes of a question that is not on a selected subsection -> readable list"""
    seen=[]
    for c in codes:
        for s in c.split('+'):
            if s not in seen: seen.append(s)
    seen.sort(key=lambda s:XORDER.index(s) if s in XORDER else -1)
    return '; '.join(XNAME.get(s,s) for s in seen)
def th(n): return f'{n:,}'

# ------------------------------------------------------------------------------------------------ data
def load():
    D=type('D',(),{})()
    D.E=json.load(open(OUT+'/entries.json')); D.M=json.load(open(OUT+'/manifest.json')); D.G=json.load(open(OUT+'/geom.json'))
    D.V=json.load(open(OUT+'/verify.json')); D.GC=json.load(open(OUT+'/geom_check.json'))
    S=pickle.load(open(WORK+'/state.pkl','rb')); D.res1,D.res2,D.pairs,D.excl=S['res1'],S['res2'],S['pairs'],S['excl']; D.man2=S['man2']
    D.U=json.load(open(DATA+'/bank_unpaired_questions.json'))
    D.P1Q=json.load(open(WORK+'/p1_questions.json'))
    D.pdf=os.path.join(QB,BANK)
    D.pdf_size=os.path.getsize(D.pdf); D.pdf_sha=hashlib.sha256(open(D.pdf,'rb').read()).hexdigest()
    D.geom_sha=hashlib.sha1(open(OUT+'/geom.json','rb').read()).hexdigest()
    D.review=open(os.path.join(HERE,'visual_review.txt'),encoding='utf-8').read().rstrip('\n').split('\n') if os.path.exists(os.path.join(HERE,'visual_review.txt')) else None
    return D

def build_rows(D):
    """included and excluded records + everything needed for the reconciliation."""
    E,M,G=D.E,D.M,D.G
    npages=collections.Counter(p['rid'] for p in M['pages'] if p['kind']=='entry')
    inc=[]; byq=collections.defaultdict(list)
    for e in E:
        g=G[e['pid']]; first=M['first'][e['rid']]; last=first+npages[e['rid']]-1
        qpp=[b[0]+1 for b in e['qbands']]
        if e['paper']==1:
            msp=[e['key'][0]+1]; mssec=f"p. {rng(msp)}; row of the answer key for Question {e['q']}"
            scope='whole question (1 mark)'
            fig={'F':'figure','T':'table','':'no figure'}[D.P1Q[e['pid']][e['q']-1]['fig']]
            diag=f"preserved; picture + key row ({fig})"
            assoc=f"verified: same paper, key row {e['q']}"
            nq,nm=len(e['qbands']),1
        else:
            msp=[b[0]+1 for b in e['mbands']]; mssec=f"p. {rng(msp)}; complete scheme of Question {e['q']}"
            scope=f"whole question ({e['marks_q']} marks); on {e['sec']}: {', '.join(e['parts'])} ({e['marks_sec']} marks)"
            if e['other_secs']: scope+=f"; question also printed under {', '.join(e['other_secs'])}"
            if e['either_or']: scope+='; EITHER/OR question: both alternatives and both schemes included'
            figs=[k for k in D.man2[e['pid']]['figs'] if k.split('.')[0]==str(e['q'])]
            nq,nm=len(e['qbands']),len(e['mbands'])
            diag=f"preserved; {nq} question + {nm} scheme picture{'s' if nm!=1 else ''} ({len(figs)} captioned figure{'s' if len(figs)!=1 else ''})"
            assoc=f"verified: same paper, scheme of Question {e['q']}"
        r=dict(rid=e['rid'],bank=f'{first}-{last}' if last>first else str(first),first=first,last=last,year=e['year'],session=e['session'],sess=e['sess'],
               paper=e['paper'],variant=e['variant'],q=e['q'],chapter=CHAPTER[e['sec'].split('.')[0]],sub=f"{e['sec']} {SECT[e['sec']]}",sec=e['sec'],
               scope=scope,qp=e['qp'],qpp='p. '+rng(qpp),ms=e['ms'],mss=mssec,diag=diag,assoc=assoc,status='INCLUDED',pid=e['pid'],nq=nq,nm=nm,pages=npages[e['rid']])
        inc.append(r); byq[(e['pid'],e['q'])].append(e['rid'])
    # ---- every source question of the 156 papers, from the findings (independent of entries.json)
    exc=[]; src=collections.OrderedDict(); expect=[]
    for p in D.pairs:
        pid=p['id']; g=G[pid]; variant=int(p['comp'][1]) if len(p['comp'])==2 else 1; year=2000+int(p['sess'][1:])
        qs=collections.OrderedDict()
        if p['paper']==1:
            for n in range(1,41): qs[n]=[D.res1[pid]['rows'][n]['sec']]
        else:
            for x in D.res2[pid]['rows']:
                qs.setdefault(int(re.match(r'^(\d+)',x['label']).group(1)),[]).append(x['sec'])
            if sorted(qs)!=sorted(int(k) for k in g['q']): raise SystemExit(f'{pid}: questions of the findings differ from the geometry')
        src[pid]=dict(p=p,n=len(qs),inc=0,rec=0,exc=0)
        for n,codes in qs.items():
            if p['paper']==1: secs=[first_in(codes[0])] if first_in(codes[0]) else []
            else:
                secs=[]
                for c in codes:
                    f=first_in(c)
                    if f and f not in secs: secs.append(f)
            if secs:
                src[pid]['inc']+=1; src[pid]['rec']+=len(secs)
                for s_ in secs: expect.append(f"{s_}|{p['sess']}|P{p['paper']}|V{variant}|Q{n}")
                continue
            src[pid]['exc']+=1
            qpp=[b[0]+1 for b in g['q'][str(n)]]
            if p['paper']==1: mss=f"p. {g['k'][str(n)][0]+1}; key row {n} (not reproduced)"
            else: mss=f"p. {rng([b[0]+1 for b in g['m'][str(n)]])}; scheme of Question {n} (not reproduced)"
            exc.append(dict(rid=f"EXCL|{p['sess']}|P{p['paper']}|V{variant}|Q{n}",bank='-',year=year,session=sname(p['sess']),sess=p['sess'],paper=p['paper'],variant=variant,q=n,
                chapter='-',sub='not selected: '+xcodes(codes),scope='whole question',qp=p['qp'],qpp='p. '+rng(qpp),ms=p['ms'],mss=mss,diag='not reproduced',
                assoc='scheme present; not needed',status='EXCLUDED: not on a selected subsection',pid=pid,kind='topic',codes=codes))
    # ---- papers without a mark scheme
    unp=[]
    for fn,v in D.U['files'].items():
        year=2000+int(v['sess'][1:])
        for q in v['questions']:
            inbank=[]
            if q['identical_to']:
                inbank=byq.get((q['identical_to'][0],q['identical_to'][1]),[])
            if q['secs']: sub='; '.join(f'{s} {SECT[s]}' for s in q['secs']); why='the paper has no mark scheme in the repository (question is on a selected subsection)'
            else:
                sub='not selected'+(': '+xcodes([q['code']]) if v['paper']==1 else ''); why='the paper has no mark scheme in the repository (question is not on a selected subsection either)'
            if inbank: why+='; the identical question of '+G[q['identical_to'][0]]['qp']+' is in the bank: '+', '.join(inbank)
            elif q['identical_to'] and q['secs']: why+='; identical to a question of '+G[q['identical_to'][0]]['qp']
            unp.append(dict(rid=f"EXCL|{v['sess']}|P{v['paper']}|V{v['variant']}|Q{q['q']}",bank='-',year=year,session=sname(v['sess']),sess=v['sess'],paper=v['paper'],variant=v['variant'],q=q['q'],
                chapter=CHAPTER[q['secs'][0].split('.')[0]] if q['secs'] else '-',sub=sub,scope='whole question',qp=fn,qpp='p. '+rng(q['pages']),ms='none in the repository',mss='-',
                diag='not reproduced',assoc='no official scheme to associate',status='EXCLUDED: '+why,kind='noscheme',secs=q['secs'],identical=q['identical_to'],inbank=inbank,basis=q['basis'],file=fn))
    dup=[]
    for x in D.excl:
        if 'no corresponding mark scheme' in x['reason']: continue
        base=re.sub(r'(-1)?-solved','',x['file'])
        dup.append(dict(rid='FILE|'+x['file'],bank='-',year='-',session='-',sess='',paper='-',variant='-',q='-',chapter='-',sub='-',scope='whole file',qp=x['file'],qpp='all',ms='-',mss='-',
            diag='not reproduced',assoc='-',status=f"EXCLUDED: scanned 'solved' copy of {base} with handwritten answers; not an official paper. The official {base} is used.",kind='dup',base=base))
    return inc,exc,unp,dup,src,expect

FIELDS=[('record_id','rid'),('bank_pages','bank'),('year','year'),('session','session'),('paper','paper'),('variant','variant'),('question','q'),('chapter','chapter'),
        ('subsection','sub'),('scope','scope'),('question_paper_file','qp'),('question_paper_source_pages','qpp'),('mark_scheme_file','ms'),('mark_scheme_source_pages_and_section','mss'),
        ('diagram_preservation','diag'),('association_verification','assoc'),('final_status','status')]

# ------------------------------------------------------------------------------------------------ PDF helpers
SAN={'\u2019':"'",'\u2018':"'",'\u201c':'"','\u201d':'"','\u2013':'-','\u2014':'-','\u2212':'-','\u2265':'>=','\u2264':'<=','\u00d7':'x','\u2192':'->','\u2026':'...','\u03bb':'lambda',
     '\u2022':'*','\u00b1':'+/-','\u0394':'delta ','\u03b8':'theta','\u03a9':'ohm','\u03c1':'rho','\u00b0':' deg','\u00bd':'1/2','\u221d':' prop. to ','\u03bc':'micro','\u03c0':'pi','\u2248':'~'}
NSAN=collections.Counter()
def inside_pictures(M):
    """Rows of the question papers that lie inside a question picture of the bank although they are not part of the question:
    page numbers, section headings with their instruction, notices that the next question begins over the page.
    {kind: dict(pictures=set of distinct pictures, pages=[bank pages], records=set, files=set, texts=Counter)}"""
    import bgeom
    NOTICE=re.compile(r'^(Question \d+|Section [AB]) (begins|starts) (over the page|on the next page|on page \d+)\.?$')
    docs={}; cls={}
    out={k:dict(pictures=set(),pages=[],records=set(),files=set(),texts=collections.Counter()) for k in ('page number','section heading','notice','scheme heading','scheme heading not first')}
    msrow={}
    for i,p in enumerate(M['pages']):
        if p['kind']!='entry': continue
        for it in p['items']:
            fn,pi,x0,y0,x1,y1=it['spec']
            if it['part']!='Q':
                # mark schemes of Paper 2: a heading row 'Section A' / 'Section B' above the scheme of the first question of the section
                if re.search(r'_ms_1',fn): continue                     # answer key of Paper 1
                key=tuple(it['spec'])
                if key not in msrow:
                    if fn not in docs: docs[fn]=bgeom.Doc(fn)
                    rows=sorted((r for r in docs[fn].rows(pi) if r['text'].strip() and y0<=(r['y0']+r['y1'])/2<=y1),key=lambda r:r['y0'])
                    hs=[k for k,r in enumerate(rows) if re.fullmatch(r'section [ab]',r['text'].strip(),re.I)]
                    msrow[key]=None if not hs else 'scheme heading' if hs==[0] and len(rows)>1 else 'scheme heading not first'
                if msrow[key]:
                    o=out[msrow[key]]; o['pictures'].add(key); o['pages'].append(i+1); o['records'].add(p['rid']); o['files'].add(fn)
                continue
            if (fn,pi) not in cls:
                if fn not in docs: docs[fn]=bgeom.Doc(fn)
                cls[(fn,pi)]=bgeom.classify_qp(docs[fn],pi,1 if re.search(r'_qp_1',fn) else 2)
            kinds={}
            for r,c in cls[(fn,pi)]:
                if not y0<=(r['y0']+r['y1'])/2<=y1: continue
                t=' '.join(sp['text'].strip() for sp in r['spans'] if not (sp['x0']>515 and sp['text'].strip() in bgeom.EXAM_USE)).strip()
                if c=='top': kinds['page number']=t
                elif NOTICE.match(t): kinds['notice']=t
                elif c=='content' and bgeom.HEAD_QP.match(t) and re.match(r'^Section [AB]\b',t): kinds['section heading']=t
            for k,t in kinds.items():
                o=out[k]
                if tuple(it['spec']) not in o['pictures'] and k!='page number': o['texts'][re.sub(r'\d+','N',t)]+=1
                o['pictures'].add(tuple(it['spec'])); o['pages'].append(i+1); o['records'].add(p['rid']); o['files'].add(fn)
    return out
def san(t):
    """the PDF copies use the built-in fonts: characters outside ASCII are written out."""
    out=[]
    for ch in str(t):
        if ord(ch)<127: out.append(ch)
        elif ch in SAN: out.append(SAN[ch])
        else: out.append('?'); NSAN[ch]+=1
    return ''.join(out)
def text_pdf(path,lines,title,fs=7.6,landscape=False):
    """monospaced copy of a text file; long lines are wrapped with a hanging indent."""
    pw,ph=(841.89,595.28) if landscape else (595.28,841.89)
    mx=30; top=36; bot=30; lh=fs*1.22; cw=fs*0.6; maxc=int((pw-2*mx)/cw)
    out=[]
    for ln in lines:
        ln=san(ln.replace('\t','    '))
        if len(ln)<=maxc: out.append(ln); continue
        ind=len(ln)-len(ln.lstrip(' ')); m=re.match(r'^\s*(\[[A-Z]+\]|[-*]|\d+\.|[A-Z]\d*\.?)\s+',ln)
        hang=' '*min(maxc//2,(len(m.group(0)) if m else ind+2)); cur=ln
        first=True
        while len(cur)>maxc:
            k=cur.rfind(' ',0,maxc+1)
            if k<=len(hang)+8: k=maxc
            out.append(cur[:k].rstrip()); cur=hang+cur[k:].lstrip(); first=False
        out.append(cur)
    per=int((ph-top-bot)/lh); n=max(1,(len(out)+per-1)//per)
    doc=fitz.open(); doc.set_metadata(dict(title=title,creator='physics-5054-revision/tools/bank/breports.py',producer='PyMuPDF'))
    for i in range(n):
        pg=doc.new_page(width=pw,height=ph); sh=pg.new_shape(); y=top
        for ln in out[i*per:(i+1)*per]:
            if ln.strip(): sh.insert_text((mx,y),ln,fontname='cour',fontsize=fs,color=(0,0,0))
            y+=lh
        sh.insert_text((mx,ph-14),title,fontname='helv',fontsize=6.5,color=(0.35,0.35,0.35))
        t=f'Page {i+1} of {n}'; sh.insert_text((pw-mx-fitz.get_text_length(t,'helv',6.5),ph-14),t,fontname='helv',fontsize=6.5,color=(0.35,0.35,0.35))
        sh.commit()
    doc.save(path,garbage=3,deflate=True); return n

_tl={}
def tlen(t,font,fs):
    k=(t,font,fs)
    if k not in _tl: _tl[k]=fitz.get_text_length(t,fontname=font,fontsize=fs)
    return _tl[k]
def wrap(t,font,fs,w):
    """wrap at spaces (and after '|', ';', '_' when a word is too long)."""
    t=str(t); out=[]; cur=''
    for word in t.split(' '):
        trial=(cur+' '+word) if cur else word
        if tlen(trial,font,fs)<=w: cur=trial; continue
        if cur: out.append(cur); cur=''
        while tlen(word,font,fs)>w:
            k=len(word)-1
            while k>1 and tlen(word[:k],font,fs)>w: k-=1
            j=max(word.rfind('|',0,k),word.rfind('_',0,k),word.rfind(';',0,k),word.rfind('/',0,k))
            if j>2: k=j+1
            out.append(word[:k]); word=word[k:]
        cur=word
    if cur or not out: out.append(cur)
    return out
def table_pdf(path,title,intro,cols,groups):
    """cols=[(heading,width,key)], groups=[(group title, [row dict])] ; landscape A4, 6 pt."""
    pw,ph=841.89,595.28; mx=22; top=30; bot=24; fs=6.0; lh=6.9; font='helv'
    doc=fitz.open(); doc.set_metadata(dict(title=title,creator='physics-5054-revision/tools/bank/breports.py',producer='PyMuPDF'))
    state=dict(pg=None,sh=None,y=0,n=0)
    xs=[mx]
    for _,w,_ in cols: xs.append(xs[-1]+w)
    def newpage(head=True):
        if state['sh'] is not None: state['sh'].commit()
        state['pg']=doc.new_page(width=pw,height=ph); state['sh']=state['pg'].new_shape(); state['n']+=1; state['y']=top
        if head:
            heads=[wrap(h,'hebo',fs,w-4) for h,w,_ in cols]; nl=max(len(h) for h in heads)
            sh=state['sh']; sh.draw_rect(fitz.Rect(mx,state['y']-7,pw-mx,state['y']+(nl-1)*lh+3)); sh.finish(color=None,fill=(0.88,0.88,0.88))
            for hl,x in zip(heads,xs):
                for i,l in enumerate(hl): sh.insert_text((x+2,state['y']+i*lh),l,fontname='hebo',fontsize=fs)
            state['y']+=nl*lh+5
    newpage(head=False); sh=state['sh']
    sh.insert_text((mx,state['y']+4),title,fontname='hebo',fontsize=12); state['y']+=22
    for ln in intro:
        for l in wrap(ln,font,7.2,pw-2*mx):
            if state['y']>ph-bot-10: newpage(head=False); sh=state['sh']
            state['sh'].insert_text((mx,state['y']),l,fontname='hebo' if ln.isupper() else font,fontsize=7.2); state['y']+=9
    for gt,rows in groups:
        newpage(); sh=state['sh']
        sh.insert_text((mx,state['y']+2),gt,fontname='hebo',fontsize=8.5); state['y']+=14
        for r in rows:
            cells=[wrap(san(r[k]),font,fs,w-4) for _,w,k in cols]; h=max(len(c) for c in cells)*lh+2.2
            if state['y']+h>ph-bot:
                newpage(); state['sh'].insert_text((mx,state['y']+2),gt+' (continued)',fontname='hebo',fontsize=8.5); state['y']+=14
            sh=state['sh']
            for c,x in zip(cells,xs):
                for i,l in enumerate(c):
                    if l: sh.insert_text((x+2,state['y']+i*lh),l,fontname=font,fontsize=fs)
            state['y']+=h
            sh.draw_line((mx,state['y']-lh+1.2),(pw-mx,state['y']-lh+1.2)); sh.finish(color=(0.78,0.78,0.78),width=0.25)
    state['sh'].commit()
    n=len(doc)
    for i,pg in enumerate(doc):
        sh=pg.new_shape(); sh.insert_text((mx,ph-10),title,fontname='helv',fontsize=6.5,color=(0.35,0.35,0.35))
        t=f'Page {i+1} of {n}'; sh.insert_text((pw-mx-fitz.get_text_length(t,'helv',6.5),ph-10),t,fontname='helv',fontsize=6.5,color=(0.35,0.35,0.35)); sh.commit()
    doc.save(path,garbage=3,deflate=True); return n

# ------------------------------------------------------------------------------------------------ the three reports
def main():
    D=load(); inc,exc,unp,dup,src,expect=build_rows(D)
    E,M,G,V,GC=D.E,D.M,D.G,D.V,D.GC
    now=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    os.makedirs(QB,exist_ok=True)
    N=M['n_pages']; nrec=len(inc); n1=sum(1 for r in inc if r['paper']==1); n2=nrec-n1
    q1=len({(r['pid'],r['q']) for r in inc if r['paper']==1}); q2=len({(r['pid'],r['q']) for r in inc if r['paper']==2})
    src1=sum(v['n'] for v in src.values() if v['p']['paper']==1); src2=sum(v['n'] for v in src.values() if v['p']['paper']==2)
    ex1=sum(1 for r in exc if r['paper']==1); ex2=len(exc)-ex1
    u1=sum(1 for r in unp if r['paper']==1); u2=len(unp)-u1
    u1s=sum(1 for r in unp if r['paper']==1 and r['secs']); u2s=sum(1 for r in unp if r['paper']==2 and r['secs']); u2rec=sum(len(r['secs']) for r in unp if r['paper']==2)
    allfiles=sorted(f for f in os.listdir(SRC) if f.lower().endswith('.pdf'))
    used=set()
    for p in D.pairs: used.add(p['qp']); used.add(p['ms'])
    exfiles={x['file'] for x in D.excl}
    other=[f for f in allfiles if f not in used and f not in exfiles]
    kinds=collections.Counter()
    KN={('qp','3'):'Paper 3 question papers (practical test)',('qp','4'):'Paper 4 question papers (alternative to practical)',('ms','3'):'Paper 3 mark schemes',('ms','4'):'Paper 4 mark schemes',
        ('er','-'):'examiner reports',('gt','-'):'grade thresholds',('ir','3'):'instructions for the practical test (Paper 3)',('ci','3'):'confidential instructions (Paper 3)',('ab','3'):'answer booklets of the practical test (Paper 3)'}
    for f in other:
        m=re.match(r'5054_[sw]\d\d_([a-z]+)(?:_(\d))?',f); k=(m.group(1),m.group(2) or '-') if m else ('?','?')
        kinds[KN.get(k,'other files: '+'_'.join(k))+(' - scanned "solved" copy' if 'solved' in f else '')]+=1
    p1agree=sum(r['agree'] for r in D.res1.values()); p1dis=sum(r['dis']+r['unsolved'] for r in D.res1.values())
    # ---------------- reconciliation
    R=[]
    def chk(name,ok,detail): R.append((bool(ok),name,detail))
    rid_inc=[r['rid'] for r in inc]
    chk('R1 the records of the bank are exactly the question/subsection pairs that the verified findings give',sorted(rid_inc)==sorted(expect) and len(set(rid_inc))==len(rid_inc),
        f'{th(len(expect))} pairs expected from the findings, {th(len(rid_inc))} records in the bank, {th(len(set(rid_inc)&set(expect)))} in both')
    fresh=[e['rid'] for e in bentries.build()]
    chk('R2 the entry list used for the build equals a fresh list made from the findings, in the same order',fresh==rid_inc,f'{th(len(fresh))} entries, order identical' if fresh==rid_inc else 'lists differ')
    chk('R3 questions of the 156 papers: in the bank + left out = all questions',q1+ex1==src1 and q2+ex2==src2 and all(v['inc']+v['exc']==v['n'] for v in src.values()),
        f'Paper 1: {th(q1)} + {th(ex1)} = {th(src1)}; Paper 2: {th(q2)} + {th(ex2)} = {th(src2)}; checked for each of the {len(src)} papers')
    chk('R4 no question is both in the bank and in the list of exclusions',not ({(r['pid'],r['q']) for r in inc}&{(r['pid'],r['q']) for r in exc}),'0 questions in both lists')
    chk('R5 papers without a mark scheme: every question is listed and left out',u1==200 and u2==55 and len(D.U['files'])==10 and not D.U.get('problems'),f'{len(D.U["files"])} papers, {u1} + {u2} = {u1+u2} questions')
    total=src1+src2+u1+u2
    chk('R6 all questions of all Paper 1 and Paper 2 question papers in the folder',q1+q2+len(exc)+len(unp)==total,f'{th(q1+q2)} in the bank + {th(len(exc))} not on a selected subsection + {th(len(unp))} without a mark scheme = {th(total)}')
    npent=sum(r['pages'] for r in inc); kinds_p=collections.Counter(p['kind'] for p in M['pages'])
    chk('R7 pages of the bank: front pages + divider pages + pages of the records = all pages',npent+kinds_p['front']+kinds_p['divider']==N and all(inc[i]['last']+1==inc[i+1]['first'] or inc[i+1]['sec']!=inc[i]['sec'] for i in range(len(inc)-1)),
        f"{kinds_p['front']} + {kinds_p['divider']} + {th(npent)} = {th(N)}; the pages of consecutive records follow each other without a gap")
    chk('R8 files of the folder physics-5054: used + excluded + other kinds = all',len(used)+len(exfiles)+len(other)==len(allfiles) and all(f in allfiles for f in used),f'{len(used)} + {len(exfiles)} + {len(other)} = {len(allfiles)}')
    rows2=sum(e['tracker_rows'] for e in E if e['paper']==2)
    chk('R9 consolidation: several tracker rows of one question in one subsection give one record',len({(e['pid'],e['q'],e['sec']) for e in E})==len(E),
        f'{th(rows2)} in-scope tracker rows of Paper 2 give {th(n2)} records of {th(q2)} questions; {th(n1)} Paper 1 questions give one record each')
    chk('R11 all papers used are complete in the paper-by-paper verification; Paper 1: the recorded answer equals the published key letter',
        all(r['status']=='COMPLETE' for r in D.res1.values()) and all(r['status']=='COMPLETE' for r in D.res2.values()) and p1agree==40*len(D.res1) and p1dis==0,
        f"{len(D.res1)} Paper 1 papers: {th(p1agree)} of {th(40*len(D.res1))} answers equal the key, {p1dis} differ or are open; {len(D.res2)} Paper 2 papers: {th(sum(r['nleaf'] for r in D.res2.values()))} sub-questions matched to their scheme entries")
    ok_pdf=V.get('info',{}).get('pdf_sha256')==D.pdf_sha
    ok_geom=V.get('info',{}).get('geom_sha1')==D.geom_sha and GC.get('geom_sha1')==D.geom_sha
    chk('R10 the results of the checks belong to the files on disk',ok_pdf and ok_geom,
        ('PDF hash equals the hash recorded by bverify.py' if ok_pdf else 'PDF CHANGED after bverify.py ran')+'; '+('geometry hash equals the hash recorded by bverify.py and bcheck_geom.py' if ok_geom else 'geometry CHANGED after the checks ran'))
    # ---------------- geometry checks
    st=GC['stat']; pr=GC['problems']
    # rows of the scheme pages that are in no crop: allowed only before the scheme of Question 1 or after the scheme of the
    # last question (covers, general notes, legend of the mark codes); a row between two questions would be lost content
    def v4pos(pid,pg,y):
        m_={int(k):v for k,v in G[pid]['m'].items()}
        first=min((b[0],b[1]) for b in m_[min(m_)]); last=max((b[0],b[2]) for b in m_[max(m_)])
        if (pg-1,y)<first: return 'before the scheme of Question 1'
        if (pg-1,y)>last: return 'after the scheme of the last question'
        return 'BETWEEN TWO QUESTIONS'
    v4=[list(x)+[v4pos(x[0],x[1],x[2])] for x in pr['V4']]; v4c=collections.Counter(x[5] for x in v4)
    v4ok=not v4c['BETWEEN TWO QUESTIONS']
    lined=GC.get('lined',[])
    GCH=[
     ('V1 Paper 2: the mark allocations printed inside the crops of a question add up to the marks of that question',not pr['V1'],f"{st.get('p2 questions',0)} questions, {len(pr['V1'])} differ"),
     ('V2 question papers: every text row and every answer line lies in exactly one crop',not pr['V2'],f"{th(st.get('qp rows',0))} rows, {len(pr['V2'])} outside or in two crops ({st.get('dotted rows on shared lined pages',0)} ruled lines on the shared lined pages are not reproduced, see the exclusions file)"),
     ('V3 every question and every scheme starts inside the first crop of its own question',not pr['V3'] and not pr['V3ms'],f"{th(st.get('starts',0))} question starts, {len(pr['V3'])+len(pr['V3ms'])} misplaced"),
     ('V4 Paper 2 schemes: every row of the used scheme pages lies in exactly one crop, or is general material listed in the exclusions file',v4ok,f"{th(st.get('ms rows',0))} rows; {len(v4)} rows are in no crop: "+', '.join(f'{n} {k}' for k,n in v4c.most_common())+' (covers, general notes, legends of the mark codes; listed in the exclusions file, part D)'),
     ('V5 Paper 1: one crop per question; its text equals the question text of the verification',not pr['V5'],f"{th(st.get('p1 questions',0))} questions, {len(pr['V5'])} differ"),
     ('V6 Paper 1: the crop of a key row holds the question number and the key letter of that question, nothing else',not pr['V6'],f"{th(st.get('key rows',0))} key rows, {len(pr['V6'])} differ"),
     ('V7 the pixel row of every cut line is free of ink (more than 8 dark pixels at 2 pixels per point), or the place was inspected',all((x[0],x[1],x[2],x[4]) in CROSS_OK for x in pr['V7']),f"{th(st.get('edges',0))} cut lines, {len(pr['V7'])} with ink"+(': '+'; '.join(f"{x[0]} {x[1]} p. {x[2]} at y={x[4]}" for x in pr['V7'])+' (the two places described under V11)' if pr['V7'] else '')),
     ('V8 Paper 2 schemes: no two neighbouring questions whose mark codes are off by opposite amounts (a row filed under the wrong question)',not pr['V8'],f"{len(pr['V8'])} such pairs"),
     ('V9 every question crop holds text (no crop of ruled lines only)',not pr['V9'],f"{len(pr['V9'])} crops without text"),
     ('V10 no ink is left outside the crops between page header and page footer',not pr['V10'],f"{th(st.get('qp pages tested for ink outside the bands',0))} question-paper pages and {st.get('ms pages tested for ink outside the bands',0)} scheme pages; {len(pr['V10'])} pages with unexplained ink; {len(lined)} shared lined pages not reproduced; {st.get('ms pages with listed rows outside the bands',0)} scheme pages with the general material of V4"),
     ('V11 no stroke crosses a cut line (8 pixels per point; excepted: cuts placed on a table rule, the rule of the examiner column), or the place was inspected',all((x[0],x[1],x[2],x[4]) in CROSS_OK for x in pr['V11']),f"{th(st.get('cut lines tested for crossing strokes',0))} cut lines, {len(pr['V11'])} crossed"+(': '+'; '.join(f"{x[0]} {x[1]} p. {x[2]} at y={x[4]}: {CROSS_OK.get((x[0],x[1],x[2],x[4]),'NOT REVIEWED')}" for x in pr['V11']) if pr['V11'] else '')),
    ]
    VCH=[(k,v['ok'],v['detail']) for k,v in V['checks'].items()]
    # the record of the visual review must name the file it describes (first 16 hex digits of its sha256)
    rv_m=re.search(r'sha256 ([0-9a-f]{16})\b','\n'.join(D.review)) if D.review is not None else None
    review_ok=bool(rv_m) and D.pdf_sha.startswith(rv_m.group(1)) and not any(l.startswith('[FAIL]') for l in D.review)
    all_ok=all(o for o,_,_ in R) and all(o for _,o,_ in GCH) and all(o for _,o,_ in VCH) and bool(V.get('ok')) and review_ok
    # =============================================================== TRACKER
    intro=[
     'PHYSICS 5054 QUESTION BANK - TRACKER',
     f'Belongs to {BANK} ({th(N)} pages, {th(D.pdf_size)} bytes). Written {now} by tools/bank/breports.py.',
     f'Part 1: the {th(nrec)} records of the bank, in the order of the bank (subsection; year; May/June before October/November; variant; paper; question number).',
     f'Part 2: the {th(len(exc))} questions of the 156 papers used that are not on a selected subsection. Part 3: the {len(unp)} questions of the 10 question papers without a mark scheme. Part 4: {len(dup)} duplicate files.',
     'A record is one original question printed once under one syllabus subsection. Record ID = subsection | session and year (s = May/June, w = October/November) | paper | variant | question number. A Paper 2 question that tests several selected subsections has one record in each; several tracker rows of the same question in one subsection are one record.',
     'Scope: the bank always shows the WHOLE question and the WHOLE official mark scheme of that question. The scope field names the parts (and marks) that put the question into the subsection.',
     'Source pages are page numbers of the source PDF (first page = 1). Bank pages are page numbers of the bank PDF.',
     'Diagram preservation: "preserved" = the question is reproduced as pictures of the full width of the source page, from the first line of the question to its last line; every picture was compared pixel by pixel with a fresh rendering of the source region (check B3b of the audit), no stroke crosses a cut line (V11) and no ink of the page is left outside the crops (V10).',
     'Association verification: "verified" = the scheme shown is the scheme of the question with the same number in the mark scheme of the same paper (same year, session, paper, variant). Paper 2: the crop runs from the label of the question in the scheme to the label of the next question; in the paper-by-paper verification every sub-question of the paper was matched to its scheme entry. Paper 1: the crop is the row of the published answer key with that question number; the answer recorded in the verification (worked out from the question; for a question repeated word for word in another paper, taken from that question) agrees with the key letter for all '+th(p1agree)+' questions of the '+str(len(D.res1))+' papers.',
     'Excluded rows: "not on a selected subsection" = no part of the question belongs to a selected subsection (the subsection field names the sections it belongs to).',
     'Final status: INCLUDED, or EXCLUDED with the reason.']
    fpath=os.path.join(QB,STEM+'tracker.txt')
    with open(fpath,'w',encoding='utf-8') as f:
        for l in intro: f.write('# '+l+'\n')
        f.write('#\n# Fields (separated by TAB): '+', '.join(n for n,_ in FIELDS)+'\n')
        for title,rows in ((f'PART 1 - INCLUDED RECORDS ({th(nrec)})',inc),(f'PART 2 - EXCLUDED: QUESTIONS OF THE PAPERS USED THAT ARE NOT ON A SELECTED SUBSECTION ({th(len(exc))})',exc),
                           (f'PART 3 - EXCLUDED: QUESTIONS OF QUESTION PAPERS WITHOUT A MARK SCHEME ({len(unp)})',unp),(f'PART 4 - EXCLUDED: DUPLICATE FILES ({len(dup)})',dup)):
            f.write('#\n# '+title+'\n'); f.write('\t'.join(n for n,_ in FIELDS)+'\n')
            for r in rows: f.write('\t'.join(str(r[k]) for _,k in FIELDS)+'\n')
    def prow(r):
        d=dict(r); d['ys']=f"{r['year']} {sshort(r['sess'])}" if r['sess'] else '-'
        d['pvq']=f"P{r['paper']} V{r['variant']} Q{r['q']}" if r['sess'] else '-'
        d['qpf']=f"{r['qp']} {r['qpp']}"; d['msf']=f"{r['ms']} {r['mss']}" if r['mss']!='-' else r['ms']
        return d
    cols=[('Record ID',78,'rid'),('Bank pages',34,'bank'),('Year, session',48,'ys'),('Paper, variant, question',44,'pvq'),('Syllabus subsection',98,'sub'),('Scope',112,'scope'),
          ('Question paper: file, source pages',88,'qpf'),('Mark scheme: file, source pages, section',98,'msf'),('Diagram preservation',62,'diag'),('Association verification',52,'assoc'),('Final status',84,'status')]
    assert sum(w for _,w,_ in cols)==798
    ntp=table_pdf(os.path.join(QB,STEM+'tracker.pdf'),'Physics 5054 question bank - tracker',intro[1:],cols,
        [(f'Part 1 - included records ({th(nrec)})',[prow(r) for r in inc]),(f'Part 2 - excluded: questions of the papers used that are not on a selected subsection ({th(len(exc))})',[prow(r) for r in exc]),
         (f'Part 3 - excluded: questions of question papers without a mark scheme ({len(unp)})',[prow(r) for r in unp]),(f'Part 4 - excluded: duplicate files ({len(dup)})',[prow(r) for r in dup])])
    # =============================================================== EXCLUSIONS
    X=[]; A=X.append
    A('PHYSICS 5054 QUESTION BANK - EXCLUSIONS AND UNRESOLVED ITEMS'); A('='*60)
    A(f'Belongs to {BANK}. Written {now} by tools/bank/breports.py.'); A('')
    A('The bank holds a question only if (1) it is in a Paper 1 or Paper 2 question paper, (2) the official mark scheme of that')
    A('paper is in the repository and (3) at least one part of the question is on a selected syllabus subsection (1.1-1.7,')
    A('3.1-3.4, 4.2). Everything else is listed here. No answer was written, inferred or taken from another paper.'); A('')
    A('SUMMARY'); A('-'*7)
    A(f'  A  {len(unp):5d} questions in {len(D.U["files"])} question papers without a mark scheme in the repository ({u1s+u2s} of them on a selected subsection)')
    A(f'  B  {len(dup):5d} files that are scanned "solved" copies of question papers')
    A(f'  C  {th(len(exc)):>5s} questions of the 156 papers used with no part on a selected subsection (Paper 1: {th(ex1)}, Paper 2: {ex2})')
    A(f'  D        parts of the pages of the included questions that are not reproduced (page furniture, shared lined pages, general notes),')
    A(f'           and page furniture that is inside the pictures')
    A(f'  E        syllabus sections that were not selected')
    A(f'  F  {len(other):5d} files of other kinds in the folder (Papers 3 and 4, examiner reports, grade thresholds, instructions)')
    A(f'  G        unresolved items: none'); A('')
    A('A. QUESTION PAPERS WITHOUT A MARK SCHEME IN THE REPOSITORY'); A('-'*58)
    A('The folder physics-5054 has no mark scheme for these ten question papers, so none of their questions is in the bank: a question')
    A('is never shown without its own official scheme and the scheme of another paper is never attached to it.')
    A('For the reconciliation every question was still given its syllabus code. Questions whose text is identical to a question of a')
    A('verified paper take the code of that question; the others were coded by reading the question (no scheme to check against).'); A('')
    for fn,v in D.U['files'].items():
        rows=[r for r in unp if r['file']==fn]; on=[r for r in rows if r['secs']]
        A(f"{fn}   {v['sess'][0]=='s' and 'May/June' or 'October/November'} {2000+int(v['sess'][1:])}, Paper {v['paper']}, variant {v['variant']}: {len(rows)} questions, {len(on)} on a selected subsection ({sum(len(r['secs']) for r in on)} question/subsection pairs)")
        idall=all(r['identical'] for r in rows)
        if idall and v['paper']==2: A(f"    The paper repeats {G[rows[0]['identical'][0]]['qp']} question for question (texts compared). Its questions are in the bank through that paper.")
        if idall and v['paper']==1:
            c=collections.Counter(G[r['identical'][0]]['qp'] for r in rows)
            A('    Every question is identical in text to a question of a verified paper: '+', '.join(f'{n} in {k}' for k,n in c.most_common())+'.')
        for r in on:
            t=f"    Q{r['q']:<3d} source {r['qpp']:9s} {'; '.join(r['secs'])}"
            if r['inbank']: t+=f"   identical question in the bank: {', '.join(r['inbank'])}"
            elif r['identical']: t+=f"   identical to {r['identical'][0]} Q{r['identical'][1]}"
            A(t)
        off=[r for r in rows if not r['secs']]
        A(f"    not on a selected subsection ({len(off)}): "+', '.join(f"Q{r['q']}" for r in off)); A('')
    A('B. DUPLICATE FILES'); A('-'*18)
    for r in dup: A(f"  {r['qp']}: scanned copy of {r['base']} with handwritten answers; not an official paper. The official {r['base']} is used.")
    A('')
    A('C. QUESTIONS OF THE 156 PAPERS USED THAT ARE NOT ON A SELECTED SUBSECTION'); A('-'*73)
    A('Their mark schemes are in the repository and were verified, but no part of these questions belongs to 1.1-1.7, 3.1-3.4 or 4.2.')
    A('Codes: '+'; '.join(XNAME[k].replace(' (not in the 2026-2028 syllabus)','') if k!='XOLD' else 'old = earlier-syllabus content that is not in the 2026-2028 syllabus' for k in XORDER)+'.'); A('')
    cc=collections.Counter()
    for r in exc:
        for c in r['codes']:
            for s_ in c.split('+'): cc[s_]+=1
    for pid,v in src.items():
        rows=[r for r in exc if r['pid']==pid]
        def short(r):
            seen=[]
            for c in r['codes']:
                for s_ in c.split('+'):
                    t='old' if s_=='XOLD' else s_[1:]
                    if t not in seen: seen.append(t)
            return f"Q{r['q']} {'+'.join(seen)}"
        A(f"{pid:7s} {v['p']['qp']:20s} {len(rows):2d} of {v['n']:2d} questions left out: "+', '.join(short(r) for r in rows))
    A(''); A(f'Total: {th(len(exc))} questions ({th(ex1)} of Paper 1, {ex2} of Paper 2).'); A('')
    A('D. MATERIAL ON THE PAGES OF THE INCLUDED QUESTIONS THAT IS NOT REPRODUCED'); A('-'*72)
    A('The pictures of the bank run from the first line of a question (or scheme) to its last line, over the full width of the')
    A('page. D1 lists what is left out, D2 what is inside a picture although it is not part of the question.'); A('')
    A('D1. Not part of a picture:')
    A('  * the page number at the head of the page (exception in D2), the footer line (copyright, paper code, "Turn over") and')
    A('    bar codes;')
    A('  * blank pages, cover pages, the instructions on the front page, formula or data pages, copyright notices at the end;')
    A(f'  * the shared lined answer pages at the end of seven Paper 2 question papers of 2004-2009 ({len(lined)} pages). They are ruled lines')
    A('    for the answers to all Section B questions and belong to no single question:')
    bl=collections.OrderedDict()
    for pid,fn,pg in lined: bl.setdefault(fn,[]).append(pg)
    for fn,pgs in bl.items(): A(f'      {fn}: source pages {rng(pgs)}')
    A(f'  * rows of the Paper 2 mark schemes that belong to no question ({len(v4)} text rows): covers bound into the scheme file, general')
    A('    marking notes, the legend of the mark codes and "Total for paper" lines. Each row, with file and source page:')
    last=None
    for pid,pg,y,hit,text,pos in v4:
        fn=G[pid]['ms']
        if (fn,pg,pos)!=last: A(f'      {fn} p. {pg} ({pos}):'); last=(fn,pg,pos)
        A(f'          {text}')
    A('  * Paper 1 mark schemes: only the row of the answer key of the question is shown (question number, key letter and, where')
    A('    printed, the mark). The rest of the key table belongs to other questions.'); A('')
    IP=inside_pictures(M)
    def ipn(k): return f"{len(IP[k]['pictures'])} pictures, shown on {len(IP[k]['pages'])} pages of the bank ({len(IP[k]['records'])} records)"
    A('D2. Inside a picture although not part of the question. A picture is the full width of the page and has no holes, so what')
    A('stands beside or directly above the lines of a question is in its picture:')
    A('  * the heading of a section with its instruction ("Section A", "Answer all the questions in this section.", "Section B",')
    A('    "Answer two questions from this section."). It is printed directly above the first question of the section and is kept')
    A(f"    with that question: {ipn('section heading')}.")
    A('  * in the Paper 2 mark schemes, the heading "Section A" or "Section B" above the scheme of the first question of the section:')
    A(f"    {ipn('scheme heading')}.")
    if IP['scheme heading not first']['pictures']:
        A(f"    A heading that is not the first line of its picture: {ipn('scheme heading not first')}; bank pages {', '.join(map(str,IP['scheme heading not first']['pages']))}.")
    else:
        A('    In every one of them the heading is the first line of the picture; no scheme picture holds a heading anywhere else.')
    A('  * the column "For Examiner\'s Use" of the older papers with its label and its rule, the corner marks of the page, and the')
    A('    vertical notice "DO NOT WRITE IN THIS MARGIN" of the papers of 2025 and 2026 (the notice is cut where a picture ends);')
    pn=IP['page number']
    yrs=[2000+int(re.search(r'_[sw](\d\d)_',f).group(1)) for f in pn['files']]
    A(f"  * the page number, in {len(pn['files'])} Paper 2 question papers of {min(yrs)}-{max(yrs)} only. In these papers the label 'For Examiner's Use' begins on the")
    A('    line of the page number and reaches down to the first line of the page. A picture of the top of such a page cannot leave')
    A(f"    the number out without cutting through the label or the first line: {ipn('page number')}.")
    A('    Files: '+', '.join(sorted(pn['files'],key=lambda f:(int(re.search(r'_[sw](\d\d)_',f).group(1)),f)))+'.')
    nt=IP['notice']
    A('  * a notice that the next question or section begins over the page, printed alone on the page after the last line of a')
    A(f"    question: {ipn('notice')}; each is a strip less than 30 pt high. Bank pages: {', '.join(map(str,nt['pages']))}.")
    A('    Wording: '+'; '.join(f'"{t}" ({n})' for t,n in sorted(nt['texts'].items()))+'.'); A('')
    A('E. SYLLABUS SECTIONS THAT WERE NOT SELECTED'); A('-'*43)
    A('Selected: 1.1-1.7 (all subsections), 3.1-3.4 (all subsections) and 4.2 (4.2.1-4.2.4): 27 subsections.')
    A('Not selected. A question with no part on a selected subsection is not in the bank (part C). A Paper 2 question that has a')
    A('part on a selected subsection and other parts on these sections is in the bank and is shown whole.')
    A('Rows of the verification tracker (one per Paper 1 question, one per Paper 2 sub-question) that carry the code:')
    A(f"  {'section':62s} {'rows':>5s}   of these in questions left out")
    call=collections.Counter()
    for r_ in D.res1.values():
        for x in r_['rows'].values():
            for s_ in set(x['sec'].split('+')): call[s_]+=1
    for r_ in D.res2.values():
        for x in r_['rows']:
            for s_ in set(x['sec'].split('+')): call[s_]+=1
    cx=collections.Counter()
    for r in exc:
        for c in r['codes']:
            for s_ in set(c.split('+')): cx[s_]+=1
    for k in XORDER: A(f'  {XNAME[k]:62s} {call[k]:5d}   {cx[k]:5d}')
    A('  Section 4.3 (electric circuits) is not a selected section: series and parallel circuit rules are filed there, not under 4.2.4.'); A('')
    A('F. FILES OF OTHER KINDS IN THE FOLDER'); A('-'*37)
    A(f'{len(allfiles)} PDF files in physics-5054: {len(used)} used (78 Paper 1 and 78 Paper 2 question papers, 155 mark scheme files: the May/June 2004')
    A(f'mark scheme is one file for all papers), {len(exfiles)} listed in A and B, {len(other)} of other kinds:')
    for k,n in sorted(kinds.items(),key=lambda kv:-kv[1]): A(f'  {n:4d}  {k}')
    A('The request covers past-paper questions with mark schemes for the theory papers; Papers 3 and 4 test practical skills and')
    A('were not part of the verified material.'); A('')
    A('G. UNRESOLVED ITEMS'); A('-'*19)
    A('None. Every question of every Paper 1 and Paper 2 question paper in the folder is either in the bank or listed in A or C, and')
    A('every included question has the scheme of its own paper (see the reconciliation in the audit file).')
    open(os.path.join(QB,STEM+'exclusions.txt'),'w',encoding='utf-8').write('\n'.join(X)+'\n')
    nxp=text_pdf(os.path.join(QB,STEM+'exclusions.pdf'),X,'Physics 5054 question bank - exclusions')
    # =============================================================== AUDIT
    U_=[]; A=U_.append
    def line(ok,name,detail): A(f"[{'PASS' if ok else 'FAIL'}] {name}"); A(f"       {detail}")
    A('PHYSICS 5054 QUESTION BANK - AUDIT'); A('='*34)
    A(f'Written {now} by tools/bank/breports.py.'); A('')
    A(f"RESULT: {'ALL AUTOMATED CHECKS PASSED; VISUAL REVIEW RECORDED' if all_ok else 'NOT PASSED - see the lines marked FAIL'}"); A('')
    A('1. FILES'); A('-'*8)
    for fn in [BANK]+[STEM+k+e for k in ('tracker','exclusions','audit') for e in ('.txt','.pdf')]:
        pth=os.path.join(QB,fn)
        if fn==STEM+'audit.txt' or fn==STEM+'audit.pdf': A(f'  {fn:52s} this file' if fn.endswith('.txt') else f'  {fn:52s} PDF copy of this file'); continue
        A(f'  {fn:52s} {th(os.path.getsize(pth)):>12s} bytes'+(f'   {th(N)} pages' if fn==BANK else ''))
    A(f'  sha256 of the bank PDF: {D.pdf_sha}')
    A(f"  built {M.get('built','?')} by tools/bank/bbuild.py; checked {V.get('when','?')} by tools/bank/bverify.py"); A('')
    A('2. WHAT IS IN THE BANK'); A('-'*22)
    A(f'  records (one question in one subsection)        {th(nrec):>7s}   Paper 1: {th(n1)}   Paper 2: {th(n2)}')
    A(f'  original questions                              {th(q1+q2):>7s}   Paper 1: {th(q1)}   Paper 2: {th(q2)}')
    c=collections.Counter(collections.Counter((r['pid'],r['q']) for r in inc if r['paper']==2).values())
    A('  Paper 2 questions by number of subsections      '+', '.join(f'{k} subsection{"s" if k>1 else ""}: {c[k]}' for k in sorted(c)))
    A(f"  pages                                           {th(N):>7s}   front {kinds_p['front']}, subsection title pages {kinds_p['divider']}, pages of records {th(npent)}")
    A(f"  pictures placed                                 {th(V['info']['pictures']):>7s}   distinct pictures: {th(V['info']['distinct_pictures'])} (a question printed under several subsections uses the same pictures)")
    A(f"  bookmarks                                       {th(V['info']['bookmarks']):>7s}   chapter and front matter 5, subsections 27, records {th(nrec)}")
    A(f"  page orientation                                portrait {th(V['info']['orientation'].get('P',0))}, landscape {th(V['info']['orientation'].get('L',0))} (landscape mark schemes from 2017 on)")
    A(f"  papers                                          {len(src)} question papers with their mark schemes: 78 of Paper 1, 78 of Paper 2, May/June 2004 to May/June 2026")
    eo=[e for e in E if e.get('either_or')]
    A(f"  EITHER/OR questions                             {len({(e['pid'],e['q']) for e in eo})} questions, {len(eo)} records, both alternatives and both schemes shown; the marks in the header are those of one alternative:")
    for e in eo: A(f"      {e['rid']:24s} {e['marks_sec']} of {e['marks_q']} marks ({e['marks_basis']})")
    A(f"  pictures                                        16 grey levels, {V['info'].get('min_dpi',180)} dpi or more, shown at original size; text is black on white")
    A('')
    A('3. RECONCILIATION'); A('-'*17)
    for ok,name,detail in R: line(ok,name,detail)
    A('')
    A('  Questions by source                       questions   in the bank    left out   reason for leaving out')
    A(f'  Paper 1, papers with a mark scheme           {th(src1):>6s}        {th(q1):>6s}      {th(ex1):>6s}   not on a selected subsection')
    A(f'  Paper 2, papers with a mark scheme           {th(src2):>6s}        {th(q2):>6s}      {th(ex2):>6s}   not on a selected subsection')
    A(f'  Paper 1, papers without a mark scheme        {u1:>6d}        {0:>6d}      {u1:>6d}   no mark scheme ({u1s} on a selected subsection)')
    A(f'  Paper 2, papers without a mark scheme        {u2:>6d}        {0:>6d}      {u2:>6d}   no mark scheme ({u2s} on a selected subsection, {u2rec} question/subsection pairs)')
    A(f'  all                                          {th(total):>6s}        {th(q1+q2):>6s}      {th(len(exc)+len(unp)):>6s}')
    A('')
    A('4. AUTOMATED CHECKS OF THE CROP GEOMETRY (tools/bank/bcheck_geom.py, against the source PDFs)'); A('-'*93)
    A(f"  run {GC.get('when','?')}; {GC.get('pairs','?')} papers")
    for name,ok,detail in GCH: line(ok,name,detail)
    if GC.get('info'):
        A('  Notes of the geometry program:')
        for pid,notes in GC['info'].items():
            for nt in notes: A(f'    {pid}: {nt}')
    A('')
    A('5. AUTOMATED CHECKS OF THE FINISHED PDF (tools/bank/bverify.py: the PDF reopened from disk, every page rendered)'); A('-'*113)
    for name,ok,detail in VCH: line(ok,name,detail)
    if V['info'].get('edges_reviewed'):
        A('  Cut lines with ink that were inspected by eye and accepted (B6):')
        for x in V['info']['edges_reviewed']: A(f"    bank page {x['page']}, {x['edge']} edge, {x['source']} source page {x['source_page']}: {x['reason']}")
    A('')
    A('6. RECORDS PER SUBSECTION'); A('-'*25)
    A('  subsection                                                 Paper 1  Paper 2  records  bank pages')
    cs=collections.Counter((r['sec'],r['paper']) for r in inc); order=[s for s,_ in SECS if s in M['secpage']]
    for i,s_ in enumerate(order):
        a=M['secpage'][s_]; b=(M['secpage'][order[i+1]]-1) if i+1<len(order) else N
        A(f"  {s_:6s} {SECT[s_][:50]:50s} {cs[(s_,1)]:7d}  {cs[(s_,2)]:7d}  {cs[(s_,1)]+cs[(s_,2)]:7d}  {a}-{b}")
    A(f"  {'all':57s} {n1:7d}  {n2:7d}  {nrec:7d}")
    A('')
    A('7. RECORDS PER PAPER'); A('-'*20)
    A('  paper    question paper        mark scheme           questions  in the bank  records  left out')
    ci=collections.Counter(r['pid'] for r in inc)
    for pid,v in src.items():
        A(f"  {pid:8s} {v['p']['qp']:21s} {v['p']['ms']:21s} {v['n']:9d}  {v['inc']:11d}  {ci[pid]:7d}  {v['exc']:8d}")
    A(f"  {'all':52s} {src1+src2:9d}  {q1+q2:11d}  {nrec:7d}  {len(exc):8d}")
    A('')
    A('8. VISUAL REVIEW'); A('-'*16)
    if D.review is None: A('[FAIL] no record of the visual review (tools/bank/visual_review.txt is missing)')
    else:
        if not review_ok: A('[FAIL] the record of the visual review does not name the bank PDF on disk (sha256); it describes another build')
        for l in D.review: A(l)
    A('')
    A('9. HOW THE BANK WAS MADE, AND LIMITS'); A('-'*36)
    for l in [
     '* Source: the PDF files in the folder physics-5054 of the repository. Every picture of the bank is rendered directly from them',
     '  by tools/bank/bbuild.py. No page of an earlier bank is used.',
     '* The files of the repository are stored with inverted colours: each page content is wrapped in a block that paints the page',
     '  white and inverts it with a blend mode. The wrapper also leaves white as the fill colour, so text that the original draws in',
     '  the default colour is invisible in the stored copy (282 pages of 31 of the files used, mostly papers of 2004-2009).',
     '  The bank removes the wrapper from the page content before rendering; it does not invert pixels. All pages of the bank are',
     '  black on white (check B1) and the text that is invisible in the stored copies is present.',
     '* Landscape mark schemes (2017 on) carry a page rotation or are landscape pages. The rotation is removed with the display',
     '  transformation of the page before any coordinate is measured; these schemes are shown on landscape pages, upright.',
     '* A question is cut out over the full page width from the blank band above its first line to the blank band below its last',
     '  line; a question that runs over several source pages gives one picture per page. The cut between two questions is placed',
     '  from the ink of the rendered page, not from text recognition. Nothing inside a picture is moved, removed or compressed.',
     '* Which subsection a question belongs to comes from the paper-by-paper verification of this project (every question read with',
     '  its mark scheme by the AI agent that built the bank, plus mechanical checks). It is a judgement, not an official',
     '  Cambridge classification. Questions written for earlier syllabuses are filed under the 2026-2028 subsection they fit.',
     '* The automated checks compare pixels, positions, page text and counts. They cannot judge whether a question is filed under',
     '  the best subsection. The visual review (part 8) covered contact sheets of all pages and full-size samples, not every page',
     '  at full size.',
     '* Third-party marks in the source files (a watermark and footer of the download site in the 2026 files) are part of the source',
     '  pages; the footer is outside the pictures, the pale watermark is visible inside them.']: A(l)
    open(os.path.join(QB,STEM+'audit.txt'),'w',encoding='utf-8').write('\n'.join(U_)+'\n')
    nap=text_pdf(os.path.join(QB,STEM+'audit.pdf'),U_,'Physics 5054 question bank - audit')
    print(f'tracker: {th(nrec)} included + {th(len(exc))} + {len(unp)} + {len(dup)} excluded rows; PDF {ntp} pages')
    print(f'exclusions: {len(X)} lines, PDF {nxp} pages | audit: {len(U_)} lines, PDF {nap} pages')
    if NSAN: print('characters replaced by ? in the PDF copies:',dict(NSAN))
    for ok,name,detail in R:
        if not ok: print('FAIL',name,'|',detail)
    for name,ok,detail in GCH+VCH:
        if not ok: print('FAIL',name,'|',detail)
    if D.review is None: print('FAIL visual_review.txt missing')
    elif not review_ok: print('FAIL visual_review.txt does not name the sha256 of the bank PDF on disk, or carries a [FAIL] line')
    print('RESULT:','all passed' if all_ok else 'NOT PASSED')
    return all_ok
# cut lines that a stroke crosses or touches (V7, V11); each inspected by eye, enlarged: (paper, 'qp'|'ms', source page, y) -> what was seen
CROSS_OK={
 ('s04_2','qp',11,795.6):"the mark '[9]', last line of Question 10, touches the page footer '[Turn over' (gap 0.12 pt, found at 8 pixels per point); the cut is at the lower end of the brackets and '[9]' is complete in the picture",
 ('s25_22','qp',6,796.5):"the corner marks of the page (page furniture, at x = 35-38 pt and 557-560 pt) stand beside the last answer line of Question 4; the cut is in the blank row below that line and passes through the corner marks only",
}
if __name__=='__main__':
    sys.exit(0 if main() else 1)
