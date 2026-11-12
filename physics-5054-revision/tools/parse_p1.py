from lib import *
BOILER=re.compile(r'^(©\s*UCLES|\[Turn over|BLANK PAGE|Permission to reproduce|Space for working|University of Cambridge International Examinations is part|To avoid the issue of disclosure|Cambridge International Examinations is part|Cambridge Assessment International Education is part|reasonable effort has been made|Every reasonable effort|been made by the publisher|at www\.cambridgeinternational|publisher will be pleased|Cambridge Assessment is the brand|Local Examinations Syndicate|after the live examination series|Copyright Acknowledgements Booklet|be pleased to make amends|Cambridge Assessment Group|download at www|is a department of the University)',re.I)
def clean_rows(page):
    rows=page_rows(page)
    H=page.rect.height
    out=[]
    for r in rows:
        t=r['text'].strip()
        if not t: continue
        if r['y0']<52 and re.fullmatch(r'\d{1,2}',t): continue
        if BOILER.search(t): continue
        if r['y0']>H-62 and (re.search(r'5054/\d',t) or 'UCLES' in t or 'Turn over' in t or r['size']<9): continue
        if re.fullmatch(r'5054/\d+/[A-Z]/[A-Z]/\d+',t): continue
        if r['size']<8.6 and r['y0']>H-120: continue
        out.append(r)
    return out
def fig_info(page,y0,y1,draws,imgs):
    nax=0;nnon=0;rects=[]
    for d in draws:
        R=d['rect']
        if R.y1<y0 or R.y0>=y1: continue
        cy=(R.y0+R.y1)/2
        if not (y0<=cy<y1): continue
        if R.height>600 or (R.width<3 and R.x0>540 and R.height>300): continue  # margin rules
        non=False
        for it in d['items']:
            if it[0]=='l':
                p1,p2=it[1],it[2]
                if abs(p1.x-p2.x)>0.7 and abs(p1.y-p2.y)>0.7: non=True
            elif it[0] in ('c','qu'): non=True
        if d.get('fill') is not None and R.width>2.5 and R.height>2.5 and not (R.width>100 and R.height>10 and d.get('fill') in [(1,1,1),(1.0,1.0,1.0)]):
            # filled shapes other than hairline rules
            if not (R.height<1.5 or R.width<1.5): non=True
        if non: nnon+=1
        else: nax+=1
        rects.append(R)
    nimg=0
    for R in imgs:
        cy=(R.y0+R.y1)/2
        if y0<=cy<y1 and R.width>15 and R.height>15: nimg+=1; rects.append(R)
    return nax,nnon,nimg,rects
def parse_qp1(qpfile):
    doc=fitz.open(os.path.join(SRC,qpfile))
    qs=[];expected=1
    for pi in range(1,len(doc)):
        page=doc[pi]
        rows=clean_rows(page)
        if not rows: continue
        H=page.rect.height
        marks=[]
        for i,r in enumerate(rows):
            m=re.match(r'^(\d{1,2})(?=\s|$)',r['text'])
            if m and r['x0']<64 and int(m.group(1))==expected and expected<=40:
                marks.append((i,expected)); expected+=1
        if not marks: continue
        try: draws=page.get_drawings()
        except Exception: draws=[]
        imgs=[]
        for im in page.get_image_info():
            imgs.append(fitz.Rect(im['bbox']))
        for k,(i,n) in enumerate(marks):
            j=marks[k+1][0] if k+1<len(marks) else len(rows)
            y0=rows[i]['y0']-3
            y1=(rows[marks[k+1][0]]['y0']-3) if k+1<len(marks) else H-58
            qrows=rows[i:j]
            # build text
            parts=[];prev=None
            for r in qrows:
                t=r['text']
                if prev is None:
                    t=re.sub(r'^\d{1,2}\s*','',t)
                    parts.append(t)
                else:
                    cont=(prev['x1']>480 and abs(r['x0']-70.9)<6 and not re.match(r'^[ABCD]\s',t)) 
                    parts.append((' ' if cont else ' | ')+t)
                prev=r
            text=''.join(parts).strip()
            nax,nnon,nimg,rects=fig_info(page,y0,y1,draws,imgs)
            ff='F' if (nimg or nnon>0) else ('T' if nax>0 else '')
            # content bbox for crop: full question
            cb=fitz.Rect(40,y0,page.rect.width-30,min(y1,max([r['y1'] for r in qrows]+[R.y1 for R in rects])+5))
            fb=None
            if rects:
                fb=fitz.Rect(rects[0])
                for R in rects[1:]: fb|=R
                # include label rows overlapping fig bbox vertically
                for r in qrows:
                    if r['y1']>fb.y0-2 and r['y0']<fb.y1+2:
                        fb|=fitz.Rect(r['x0'],r['y0'],r['x1'],r['y1'])
                fb=fitz.Rect(max(30,fb.x0-8),max(y0,fb.y0-6),min(page.rect.width-20,fb.x1+8),min(y1,fb.y1+6))
            qs.append(dict(n=n,page=pi+1,text=text,fig=ff,nax=nax,nnon=nnon,nimg=nimg,qbox=[cb.x0,cb.y0,cb.x1,cb.y1],fbox=[fb.x0,fb.y0,fb.x1,fb.y1] if fb else None))
    return qs
if __name__=='__main__':
    pairs,excl=list_pairs()
    res={}
    for p in pairs:
        if p['paper']!=1: continue
        qs=parse_qp1(p['qp'])
        res[p['id']]=qs
        if len(qs)!=40: print('BAD',p['id'],len(qs),[q['n'] for q in qs][-3:])
    json.dump(res,open(WORK+'/p1_questions.json','w'))
    import collections
    c=collections.Counter(q['fig'] for qs in res.values() for q in qs)
    print('papers',len(res),'figflags',dict(c),'total chars',sum(len(q['text']) for qs in res.values() for q in qs))
