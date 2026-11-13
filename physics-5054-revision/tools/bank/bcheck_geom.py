#!/usr/bin/env python3
"""bcheck_geom.py — tests of the crop geometry (WORK/bank/geom.json) against the source PDFs.
 V1 Paper 2: the '[n]' mark allocations printed inside the bands of a question add up to the marks of that question
 V2 QP: every text row of the question pages (content and dotted answer lines) lies in exactly one band
 V3 every question start lies in the first band of its own question
 V4 Paper 2 MS: every content row of the scheme pages lies in exactly one band (rows outside: listed)
 V5 Paper 1: one band per question; its text equals the question text of the verified parser
 V6 Paper 1 key: the words inside the key row are the question number, the key letter (and the mark)
 V7 the top and bottom edge of every band is free of ink (long vertical rules excepted)
 V9 every question band holds letters or digits (no band of ruled lines only)
 V8 Paper 2 MS: two neighbouring questions whose mark codes are off by opposite amounts (rows filed under the wrong question)
 V10 no ink is left outside the crops: on every question-paper page from Question 1 on, the ink between the page header
     and the page footer lies inside a band (pages without any band that hold only ruled answer lines are listed:
     shared lined pages); on every used mark-scheme page, ink outside the bands occurs only where V4 lists text rows
 V11 no stroke crosses a cut line: at 8 pixels per point, no column has ink directly above AND directly below the top
     or bottom edge of a band (excepted: cuts placed on a table rule, the rule of the examiner column, the outer 30 pt
     (25 pt) of the page)"""
import sys,collections
from bgeom import *
G=json.load(open(OUT+'/geom.json'))
man2=json.load(open(WORK+'/p2_manifest.json')); q1=json.load(open(WORK+'/p1_questions.json')); keys=json.load(open(WORK+'/keys_p1.json'))
only=sys.argv[1:]
bad=collections.defaultdict(list); stat=collections.Counter(); lined=[]
def inband(bands,pi,y):
    return [n for n,bs in bands.items() for b in bs if b[0]==pi and b[1]<=y<=b[2]]
FZ=8.0
def crossing(doc,pi,y,rules,margin):
    """columns (in points) where ink lies directly above and directly below the horizontal line y.
    rules = x positions (points) of the examiner-column rule of the page (bgeom.margin_rule_cols); nothing else is excepted."""
    W,H=doc.size(pi)
    y0=max(0.0,y-0.5); f=doc.gray(pi,FZ,clip=(0,y0,W,min(H,y+0.5)))<DARK
    k=int(round((y-y0)*FZ))                      # first fine row below the line
    if k<2 or f.shape[0]<k+2: return []
    both=f[k-2:k].any(axis=0)&f[k:k+2].any(axis=0)
    both[:int(margin*FZ)]=False; both[int((W-margin)*FZ):]=False
    out=[]
    for c in np.flatnonzero(both):
        x=c/FZ
        if any(abs(x-rx)<=1.25 for rx in rules): continue
        if out and x-out[-1][1]<1.0: out[-1][1]=x
        else: out.append([x,x])
    return [(round(float(u),1),round(float(v),1)) for u,v in out]
for pid,g in G.items():
    if only and pid not in only: continue
    qp=Doc(g['qp']); ms=Doc(g['ms'])
    Q={int(k):v for k,v in g['q'].items()}
    # V3
    for n,pi,y,htop in g['q_starts']:
        hit=inband(Q,pi,y+3)
        if hit!=[n] or Q[n][0][0]!=pi: bad['V3'].append((pid,n,hit))
        stat['starts']+=1
    # V2 + V7 (QP)
    paper=g['paper']
    first=g['q_starts'][0]
    for pi in range(1,qp.n):
        cls=classify_qp(qp,pi,paper)
        ink=PageInk(qp,pi,cls,(30,qp.size(pi)[0]-30),False)
        for r,c in cls:
            if c not in('content','dots'): continue
            if (pi,r['y0'])<(first[1],first[3]-1): continue
            cy=(r['y0']+r['y1'])/2
            if cy<ink.zt or cy>ink.zb: stat['rows in furniture zone']+=1; continue
            hit=inband(Q,pi,cy); stat['qp rows']+=1
            if len(hit)!=1:
                if c=='dots' and not hit and not any(cc=='content' and ink.zt<=(rr['y0']+rr['y1'])/2<=ink.zb for rr,cc in cls): stat['dotted rows on shared lined pages']+=1; continue
                bad['V2'].append((pid,pi+1,round(cy),hit,r['text'][:50]))
        a=qp.gray(pi)
        W=a.shape[1]
        dk=(a<DARK)
        for r,c in cls:
            for sp in r['spans']:
                if sp['x0']>515 and sp['text'].strip() in EXAM_USE: dk[max(0,int((sp['y0']-1)*Z)):int((sp['y1']+1)*Z)+1,max(0,int((sp['x0']-1)*Z)):int((sp['x1']+1)*Z)+1]=False
        rulecols=margin_rule_cols(dk); rules=[c/Z for c in rulecols]
        if rules: stat['qp pages with the rule of an examiner column']+=1
        for n,bs in Q.items():
            for b in bs:
                if b[0]!=pi: continue
                for y,how in((b[1],b[3]),(b[2],b[4])):
                    k=min(a.shape[0]-1,max(0,int(round(y*Z))))
                    row=a[k,int(35*Z):W-int(35*Z)]<DARK
                    stat['edges']+=1
                    if row.sum()>8: bad['V7'].append((pid,'qp',pi+1,n,round(y,1),how,int(row.sum())))
                    stat['cut lines tested for crossing strokes']+=1
                    cr=crossing(qp,pi,y,rules,30)
                    if cr: bad['V11'].append((pid,'qp',pi+1,n,round(y,2),how,cr[:6]))
        # V10: ink between header and footer that is in no band
        if (pi,0)>=(first[1],0):
            dark=(a<DARK); Wp=qp.size(pi)[0]
            dark[:,:int(30*Z)]=False; dark[:,int((Wp-30)*Z):]=False
            for c in rulecols: dark[:,max(0,c-2):c+3]=False
            for r,c in cls:
                if c in('content','dots'):
                    for sp in r['spans']:
                        if sp['x0']>515 and sp['text'].strip() in EXAM_USE: dark[max(0,int((sp['y0']-1)*Z)):int((sp['y1']+1)*Z)+1,max(0,int((sp['x0']-1)*Z)):int((sp['x1']+1)*Z)+1]=False
                    continue
                dark[max(0,int((r['y0']-2)*Z)):int((r['y1']+2)*Z)+1,max(0,int((r['x0']-2)*Z)):int((r['x1']+2)*Z)+1]=False
            dark[:max(0,int(round(ink.zt*Z))),:]=False; dark[min(a.shape[0],int(round(ink.zb*Z))):,:]=False
            if pi==first[1]: dark[:int((first[3]-12)*Z),:]=False          # heading of the paper above Question 1
            nb=0
            for n,bs in Q.items():
                for b in bs:
                    if b[0]==pi: dark[max(0,int(round(b[1]*Z))):int(round(b[2]*Z))+1,:]=False; nb+=1
            stat['qp pages tested for ink outside the bands']+=1
            if dark.any():
                inzone=[c for r,c in cls if c in('content','dots') and ink.zt<=(r['y0']+r['y1'])/2<=ink.zb]
                if nb==0 and 'content' not in inzone: lined.append((pid,g['qp'],pi+1))
                else: bad['V10'].append((pid,'qp',pi+1,int(dark.sum()),nb))
    # V9: a question band always holds text (a band of ruled lines only would be a shared answer page)
    for n,bs in Q.items():
        for b in bs:
            ws=[w[4] for w in words_in(qp,b[0],b[1],b[2])]
            if not any(re.search(r'[A-Za-z0-9]',w) and w not in('For','Use',"Examiner's",'Examiner’s') for w in ws): bad['V9'].append((pid,n,b[0]+1))
    if paper==2:
        M={int(k):v for k,v in g['m'].items()}
        m=man2[pid]
        for n,bs in Q.items():
            tot=0
            for b in bs:
                for w in words_in(qp,b[0],b[1],b[2]):
                    for mm in re.finditer(r'\[(\d{1,2})\]',w[4]): tot+=int(mm.group(1))
            stat['p2 questions']+=1
            if tot!=m['qmarks'][str(n)]: bad['V1'].append((pid,n,tot,m['qmarks'][str(n)]))
        # V8 (information): mark codes inside the scheme bands against the marks of the question
        dev={}
        for n,bs in M.items():
            sm=0
            for b in bs:
                for w in words_in(ms,b[0],b[1],b[2]):
                    t=w[4].strip('.,;:()[]')
                    if re.fullmatch(r'(?:[BCMA]\d)+',t): sm+=sum(int(d) for d in re.findall(r'[BCMA](\d)',t))
            dev[n]=sm-m['qmarks'][str(n)]
            if sm==0: stat['scheme bands without letter mark codes']+=1
        for n,dv in dev.items():
            if dv and dev.get(n+1)==-dv: bad['V8'].append((pid,n,dv,n+1,-dv))
        for n,pi,y,htop in g['m_starts']:
            if n is None: continue
            hit=inband(M,pi,y+3)
            if hit!=[n]: bad['V3ms'].append((pid,n,hit))
        firstm=g['m_starts'][0]
        for pi in g['ms_use']:
            cls=classify_ms(ms,pi)
            ink=PageInk(ms,pi,cls,(25,ms.size(pi)[0]-25),True)
            for r,c in cls:
                if c!='content': continue
                cy=(r['y0']+r['y1'])/2
                if cy<ink.zt or cy>ink.zb: stat['ms rows in furniture zone']+=1; continue
                hit=inband(M,pi,cy); stat['ms rows']+=1
                if len(hit)!=1: bad['V4'].append((pid,pi+1,round(cy),hit,r['text'][:60]))
            a=ms.gray(pi); W=a.shape[1]
            for n,bs in M.items():
                for b in bs:
                    if b[0]!=pi: continue
                    for y,how in((b[1],b[3]),(b[2],b[4])):
                        if how=='rule': stat['cut lines on a table rule']+=1; continue
                        k=min(a.shape[0]-1,max(0,int(round(y*Z))))
                        row=a[k,int(25*Z):W-int(25*Z)]<DARK
                        stat['edges']+=1
                        if row.sum()>8: bad['V7'].append((pid,'ms',pi+1,n,round(y,1),how,int(row.sum())))
                        stat['cut lines tested for crossing strokes']+=1
                        cr=crossing(ms,pi,y,[],25)
                        if cr: bad['V11'].append((pid,'ms',pi+1,n,round(y,2),how,cr[:6]))
            # V10: ink outside the bands must coincide with text rows listed by V4
            dark=(a<DARK); Wp=ms.size(pi)[0]
            dark[:,:int(25*Z)]=False; dark[:,int((Wp-25)*Z):]=False
            for r,c in cls:
                if c!='content': dark[max(0,int((r['y0']-2)*Z)):int((r['y1']+2)*Z)+1,max(0,int((r['x0']-2)*Z)):int((r['x1']+2)*Z)+1]=False
            dark[:max(0,int(round(ink.zt*Z))),:]=False; dark[min(a.shape[0],int(round(ink.zb*Z))):,:]=False
            for n,bs in M.items():
                for b in bs:
                    if b[0]==pi: dark[max(0,int(round(b[1]*Z))):int(round(b[2]*Z))+1,:]=False
            stat['ms pages tested for ink outside the bands']+=1
            if dark.any():
                v4here=[x for x in bad['V4'] if x[0]==pid and x[1]==pi+1]
                if v4here: stat['ms pages with listed rows outside the bands']+=1
                else: bad['V10'].append((pid,'ms',pi+1,int(dark.sum())))
    else:
        for n,bs in Q.items():
            stat['p1 questions']+=1
            if len(bs)!=1: bad['V5'].append((pid,n,'bands',len(bs))); continue
            b=bs[0]
            rows=[r for r in parse_p1.clean_rows(qp.page(b[0])) if b[1]<=(r['y0']+r['y1'])/2<=b[2]]
            t=' '.join(r['text'] for r in rows); t=re.sub(r'^\d{1,2}\s*','',t)
            want=q1[pid][n-1]['text'].replace(' | ',' ')
            norm=lambda s:re.sub(r'\s+','',s)
            if norm(t)!=norm(want) and not (norm(want).startswith(norm(t)) and re.search(r'publisher|copyright|UCLES',want[len(t)-5:])): bad['V5'].append((pid,n,t[:40],want[:40]))
        K={int(k):v for k,v in g['k'].items()}
        for n,k in K.items():
            ws=[w[4] for w in ms.page(k[0]).get_text('words') if k[1]<=(w[0]+w[2])/2<=k[3] and k[2]<=(w[1]+w[3])/2<=k[4]]
            stat['key rows']+=1
            if sorted(ws) not in (sorted([str(n),k[5]]),sorted([str(n),k[5],'1'])) or k[5]!=keys[pid]['key'][n-1]: bad['V6'].append((pid,n,ws))
print('checked:',dict(stat))
for k in ['V1','V2','V3','V3ms','V4','V5','V6','V7','V8','V9','V10','V11']:
    v=bad.get(k,[])
    print(k,'problems:',len(v))
    for x in v[:int(sys.argv[1]) if (only and only[0].isdigit()) else 25]: print('    ',x)
print('shared lined pages (no band, ruled lines only):',len(lined),lined)
json.dump(dict(stat=dict(stat),problems={k:bad.get(k,[]) for k in ['V1','V2','V3','V3ms','V4','V5','V6','V7','V8','V9','V10','V11']},lined=lined,geom_sha1=__import__('hashlib').sha1(open(OUT+'/geom.json','rb').read()).hexdigest(),info={pid:g.get('info',[]) for pid,g in G.items() if g.get('info')},pairs=len(G) if not only else len(only),
               when=__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')),open(OUT+'/geom_check.json','w'))
