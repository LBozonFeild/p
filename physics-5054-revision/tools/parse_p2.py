from lib import *
QP_BOILER=re.compile(r'^(©\s*UCLES|\[Turn over|BLANK PAGE|Permission to reproduce|University of Cambridge International Examinations is part|To avoid the issue of disclosure|Cambridge International Examinations is part|Cambridge Assessment International Education is part|reasonable effort has been made|Every reasonable effort|been made by the publisher|at www\.cambridgeinternational|publisher will be pleased|Cambridge Assessment is the brand|Local Examinations Syndicate|after the live examination series|Copyright Acknowledgements Booklet|be pleased to make amends|Cambridge Assessment Group|download at www|is a department of the University|DO NOT WRITE IN THIS MARGIN|\* ?\d{10,} ?\*|Please turn over|Question \d+ (is|begins) on|\[?Turn over\]?$|DFD$|ĬÕ)',re.I)
EXAM_USE={'For','Examiner’s','Examiner\'s','Use','Examiner’s Use','For Examiner’s Use','For Examiner’s','Examiner\u2019s'}
ROM=re.compile(r'^(i{1,3}|iv|v|vi{1,3}|ix|x)$')
def qp_rows(page):
    rows=page_rows(page)
    H=page.rect.height
    out=[]
    for r in rows:
        # strip examiner-use column spans
        sp=[s for s in r['spans'] if not (s['x0']>515 and s['text'].strip() in EXAM_USE)]
        if len(sp)!=len(r['spans']):
            if not sp: continue
            t=r['text']
            for w in ['   For Examiner’s Use','   Examiner’s Use','   Examiner’s','   For','   Use']:
                if t.endswith(w): t=t[:-len(w)]
            r=dict(r); r['text']=t.rstrip(); r['spans']=sp
        t=r['text'].strip()
        if not t: continue
        if r['y0']<56 and re.fullmatch(r'\d{1,2}',t): continue
        if QP_BOILER.search(t) or re.match(r'^(Trace ID:|Re-uploading, mirroring)',t): continue
        if r['y0']>H-62 and (re.search(r'5054/\d',t) or 'UCLES' in t or 'Turn over' in t or r['size']<9): continue
        if r['size']<6 : continue
        if re.fullmatch(r'[.\s…]+',t): continue
        if re.fullmatch(r'[,\s]+',t): continue
        t2=re.sub(r'\.{4,}',' … ',r['text'])
        t2=re.sub(r'\s+',' ',t2).strip() if '   ' not in r['text'] else re.sub(r'[ ]{4,}','   ',t2).strip()
        r=dict(r); r['text']=t2
        out.append(r)
    return out
CAP=re.compile(r'^(?:Fig\.|Figure) ?(\d+)\.(\d+)\s*(?:\([^)]*\))?\s*$')
def is_body(r):
    t=r['text']
    x=r['x0']
    if x<64 and re.match(r'^\d{1,2}(\s|$)',t): return True
    if re.match(r'^\([a-z]{1,4}\)\s',t) and x<125: return True
    atind=any(abs(x-v)<2.5 for v in (49.6,70.9,72.3,95.0,96.0,92.9,117.7,106.3,113.4,90.0))
    if atind and (len(t)>=58 or (len(t)>=24 and t.rstrip()[-1:] in '.:?')): return True
    if re.search(r'\[\d{1,2}\]\s*$',t) or '…' in t: return True
    if re.search(r'\[Total',t): return True
    return False
def page_figs(page,rows):
    """detect figures by caption rows and the region between last body-text row and the caption"""
    caps=[r for r in rows if CAP.match(r['text']) and len(r['text'])<48]
    if not caps: return []
    try: draws=page.get_drawings()
    except Exception: draws=[]
    W=page.rect.width; H=page.rect.height
    rects=[]
    for d in draws:
        R=d['rect']
        if R.height>520: continue
        if R.width<4 and R.height>250: continue
        if R.x0>W-62 and R.width<45: continue      # examiner-use column
        if R.x1<45 or R.x0>W-45 or R.y1<58 or R.y0>H-58: continue
        if R.width<0.5 and R.height<0.5: continue
        rects.append(fitz.Rect(R))
    for im in page.get_image_info():
        R=fitz.Rect(im['bbox'])
        if R.width>15 and R.height>15 and R.x0>30 and R.x1<W-20 and R.height<520 and R.y0>50: rects.append(R)
    figs=[];prevcap=50
    caps.sort(key=lambda r:r['y0'])
    for c in caps:
        body=[r for r in rows if r['y1']<=c['y0']+1 and r['y0']>=prevcap-1 and r is not c and is_body(r)]
        limit=max([prevcap]+[r['y1'] for r in body])
        lab=[r for r in rows if r['y0']>=limit-1 and r['y1']<=c['y0']+1 and r is not c]
        cand=[R for R in rects if R.y1<=c['y0']+5 and R.y0>=limit-4]
        m=CAP.match(c['text'])
        fid=f"{m.group(1)}.{m.group(2)}"
        box=fitz.Rect(c['x0'],c['y0'],c['x1'],c['y1'])
        for R in cand: box|=R
        for r in lab: box|=fitz.Rect(r['x0'],r['y0'],r['x1'],r['y1'])
        found=bool(cand)
        if not cand and not lab:
            box|=fitz.Rect(70,max(limit+2,c['y0']-200),W-70,c['y0'])
        box=fitz.Rect(max(28,box.x0-8),max(limit-2,box.y0-8),min(W-24,box.x1+8),c['y1']+3)
        figs.append(dict(id=fid,box=[box.x0,box.y0,box.x1,box.y1],found=found,cap_y=c['y0'],label_rows=[id(r) for r in lab]))
        prevcap=c['y1']
    return figs
def parse_qp2(qpfile):
    doc=fitz.open(os.path.join(SRC,qpfile))
    qs=[];cur=None;expected=1
    letter=None;roman=None
    figs_all=[]
    for pi in range(1,len(doc)):
        page=doc[pi]
        rows=qp_rows(page)
        if not rows: continue
        figs=page_figs(page,rows)
        labset={}
        for f in figs:
            for rid in f['label_rows']: labset[rid]=f['id']
            figs_all.append(dict(id=f['id'],page=pi+1,box=f['box'],found=f['found']))
        pend_fig=None;fig_buf=[]
        def flush():
            nonlocal fig_buf,pend_fig
            if fig_buf and cur is not None:
                cur['lines'].append('{fig '+pend_fig+': '+' | '.join(fig_buf)+'}')
            fig_buf=[];pend_fig=None
        for r in rows:
            t=r['text']
            m=re.match(r'^(\d{1,2})(?=\s|$)',t)
            if m and r['x0']<64 and int(m.group(1))==expected and expected<=14 and id(r) not in labset:
                flush()
                cur=dict(n=expected,lines=[],leaves=[],total=None,pages=[pi+1],figs=[])
                qs.append(cur); expected+=1; letter=None; roman=None
                t=t[m.end():].strip(); qstart=True
                if not t: continue
            else: qstart=False
            if cur is None:
                continue
            if pi+1 not in cur['pages']: cur['pages'].append(pi+1)
            if id(r) in labset:
                if pend_fig!=labset[id(r)]: flush(); pend_fig=labset[id(r)]
                fig_buf.append(t); continue
            flush()
            mf=re.match(r'^(?:Fig\.|Figure) ?(\d+\.\d+)\s*(?:\([^)]*\))?\s*$',t)
            if mf and len(t)<48 and mf.group(1) not in cur['figs']: cur['figs'].append(mf.group(1))
            # labels
            tt=t; first=True; had_letter=False
            RO=['i','ii','iii','iv','v','vi','vii','viii','ix','x']
            while True:
                ml=re.match(r'^\(([a-z]{1,4})\)(\s+|$)',tt)
                if not ml: break
                lab=ml.group(1)
                isrom=bool(ROM.match(lab)) and not (lab=='i' and letter=='h' and roman is None)
                if isrom and lab in ('i','v','x') and first and r['x0']<82 and letter is not None and len(lab)==1 and ord(lab)==ord(letter)+1:
                    isrom=False   # letter sequence ... (h) (i)
                if isrom:
                    okpos=(r['x0']<101.5 and first) or had_letter or qstart
                    okseq=(roman is None and lab=='i') or (roman in RO and lab in RO and RO.index(lab)>RO.index(roman)) or had_letter
                    if not (okpos and okseq): break
                    roman=lab
                elif len(lab)==1:
                    okpos=(r['x0']<82 and first) or qstart
                    okseq=(letter is None) or (ord(lab)>ord(letter))
                    if not (okpos and okseq): break
                    letter=lab; roman=None; had_letter=True
                else: break
                tt=tt[ml.end():]; first=False
            mt=re.search(r'\[Total:?\s*(\d+)\s*(marks?)?\]',t)
            if mt:
                cur['total']=int(mt.group(1))
            else:
                for mm in re.finditer(r'\[(\d{1,2})\]',t):
                    label=f"{cur['n']}{letter or ''}{roman or ''}"
                    cur['leaves'].append([label,int(mm.group(1))])
            cur['lines'].append(t)
        flush()
    # merge duplicate leaf labels
    for q in qs:
        merged=[];seen={}
        for lab,mk in q['leaves']:
            if lab in seen: merged[seen[lab]][1]+=mk; merged[seen[lab]][2]+=1
            else: seen[lab]=len(merged); merged.append([lab,mk,1])
        q['leaves']=merged
        q['marks']=sum(m for _,m,_ in merged)
        q['text']='\n'.join(q['lines']); del q['lines']
    return qs,figs_all
MS_HDR=re.compile(r'^(Page \d+|GCE O ?LEVEL|Cambridge O Level|©|5054/\d|5054\s+\d|Mark Scheme|PHYSICS\s*[–-]|Syllabus|Question\s+Answer\s+Marks|PUBLISHED|GCE Ordinary Level|Cambridge Ordinary Level|Paper$|Syllabus\s+Paper|\d{4}$)',re.I)
def ms_rows(page):
    rows=page_rows(page)
    out=[]
    H=page.rect.height
    for r in rows:
        t=r['text'].strip()
        if not t: continue
        if r['y0']<64 and (MS_HDR.search(t) or re.search(r'Mark Scheme|Syllabus|5054|PUBLISHED|GCE|Cambridge O',t)): continue
        if r['y0']>H-45 and (re.search(r'©|UCLES|Cambridge|Page \d+ of|Turn over',t)): continue
        if re.match(r'^©\s*(UCLES|University of Cambridge|Cambridge)',t): continue
        if re.fullmatch(r'Question\s+Answer\s+Marks?',t): continue
        if re.match(r'^(Trace ID:|Re-uploading, mirroring)',t): continue
        out.append(r)
    return out
def col_bounds(page):
    import collections
    xs=collections.Counter()
    for d in page.get_drawings():
        for it in d['items']:
            if it[0]=='l':
                p1,p2=it[1],it[2]
                if abs(p1.x-p2.x)<0.8 and abs(p1.y-p2.y)>8: xs[round(p1.x)]+=1
            elif it[0]=='re':
                R=it[1]
                if R.width<2.5 and R.height>8: xs[round(R.x0)]+=1
                elif R.width>20 and R.height>8: xs[round(R.x0)]+=1; xs[round(R.x1)]+=1
    W=page.rect.width
    cl=[]
    for x in sorted(xs):
        if x<10 or x>W-10: continue
        if cl and x-cl[-1][0]<=7: cl[-1][1]+=xs[x]; 
        else: cl.append([x,xs[x]])
    return [x for x,n in cl if n>=3]
def parse_ms2(msfile,combined=False):
    doc=fitz.open(os.path.join(SRC,msfile))
    pages=list(range(len(doc)))
    newfmt=False
    raws={}
    for pi in pages:
        raws[pi]=page_rows(doc[pi])
        if any(re.match(r'^Question\s+Answer\s+Marks?',r['text'].strip()) for r in raws[pi]): newfmt=True
    use=[]
    for pi in pages:
        if newfmt:
            if any(re.match(r'^Question\s+Answer\s+Marks?',r['text'].strip()) for r in raws[pi]): use.append(pi)
        else:
            if pi==0: continue
            use.append(pi)
    if combined:
        use=[pi for pi in use if re.search(r'5054\s+0?2\b','\n'.join(r['text'] for r in raws[pi][:3]))]
    qs={};cur=0;order=[]
    for pi in use:
        rows=ms_rows(doc[pi])
        if not rows: continue
        if newfmt:
            lines_=col_bounds(doc[pi])
            hq=ha=hm=hg=None
            for r0 in raws[pi]:
                if re.match(r'^Question\s+Answer\s+Marks?',r0['text'].strip()):
                    for sp in r0['spans']:
                        tx=sp['text'].strip()
                        if tx.startswith('Question'): hq=sp
                        elif tx.startswith('Answer'): ha=sp
                        elif tx.startswith('Mark'): hm=sp
                        elif tx.startswith('Guidance'): hg=sp
                    break
            if hq and hm:
                c1=[x for x in lines_ if x>hq['x1']-4 and x<hq['x1']+40]
                b1=min(c1) if c1 else hq['x1']+8
                c2=[x for x in lines_ if x<hm['x0']+2 and x>hm['x0']-40]
                b2=max(c2) if c2 else hm['x0']-8
                c3=[x for x in lines_ if x>hm['x1']-6 and x<hm['x1']+40]
                b3=min(c3) if c3 else hm['x1']+8
                cb=[0,b1,b2,b3]+([doc[pi].rect.width] if hg else [])
                if not hg: cb=[0,b1,b2,b2+200]
            else:
                cb=lines_
                if len(cb)<4: cb=[60,122,735,780]
            ncol=len(cb)-1
            for r in rows:
                if re.match(r'^Question\s+Answer\s+Marks?',r['text'].strip()): continue
                cols=[[] for _ in range(ncol)]
                for sp in r['spans']:
                    k=sum(1 for b in cb if b<=sp['x0']+3)-1
                    k=max(0,min(ncol-1,k))
                    cols[k].append(sp)
                def ctext(sps):
                    if not sps: return ''
                    rr=dict(r); 
                    parts=[];prev=None
                    rc=(r['y0']+r['y1'])/2
                    for s_ in sps:
                        t=s_['text']; sc=(s_['y0']+s_['y1'])/2
                        if s_['size']<0.82*r['size'] and prev is not None and s_['x0']-prev['x1']<3:
                            if sc<rc-1.0: t='^'+t.strip()
                            elif sc>rc+1.0: t='_'+t.strip()
                        if prev is not None:
                            gap=s_['x0']-prev['x1']
                            if gap>1.0 and not parts[-1].endswith(' ') and not t.startswith((' ','^','_')): parts.append(' ')
                        parts.append(t); prev=s_
                    return re.sub(r'\s+',' ',''.join(parts)).strip()
                lab=ctext(cols[0]); ans=ctext(cols[1]); mk=ctext(cols[2]); gd=ctext(cols[3]) if ncol>3 else ''
                mm=re.match(r'^(\d)\s+(\S.*)$',mk)
                if mm and ncol>3: mk=mm.group(1); gd=(mm.group(2)+' '+gd).strip()
                m=re.match(r'^(\d{1,2})\s*(?:[EO]\b)?\s*(?=\(|$)',lab.replace('EITHER','E').replace('OR','O'))
                if m:
                    n=int(m.group(1))
                    if n==cur+1 and n<=14:
                        cur=n; qs[cur]=dict(n=cur,lines=[],pages=[pi+1],mk=0,nc=0); order.append(cur)
                if cur==0: continue
                if pi+1 not in qs[cur]['pages']: qs[cur]['pages'].append(pi+1)
                for tok in mk.split():
                    m2=re.match(r'^[BCMA]?(\d)$',tok)
                    if m2: qs[cur]['mk']+=int(m2.group(1)); qs[cur]['nc']+=1
                line=(lab+' ' if lab else '   ')+ans
                if mk: line+='  ['+mk+']'
                if gd: line+='  ‖ '+gd
                qs[cur]['lines'].append(line.rstrip())
        else:
            minx=min(r['x0'] for r in rows)
            for r in rows:
                t=r['text']
                m=re.match(r'^(\d{1,2})\s*(?=\(|\s|$)',t)
                if m and r['x0']<minx+16:
                    n=int(m.group(1))
                    if n==cur+1 and n<=14:
                        cur=n; qs[cur]=dict(n=cur,lines=[],pages=[pi+1]); order.append(cur)
                if cur==0: continue
                if pi+1 not in qs[cur]['pages']: qs[cur]['pages'].append(pi+1)
                qs[cur]['lines'].append(t)
    for q in qs.values():
        txt='\n'.join(q['lines'])
        if newfmt:
            q['marks']=q.pop('mk'); q['ncodes']=q.pop('nc')
        else:
            codes=re.findall(r'(?<![A-Za-z0-9])([BCMA])(\d)(?![0-9A-Za-z.])',txt)
            q['marks']=sum(int(d) for _,d in codes)
            q['ncodes']=len(codes)
        q['text']=txt; del q['lines']
    return [qs[n] for n in order],newfmt
if __name__=='__main__':
    pairs,excl=list_pairs()
    res={}
    for p in pairs:
        if p['paper']!=2: continue
        qs,figs=parse_qp2(p['qp'])
        ms,newfmt=parse_ms2(p['ms'],p['combined'])
        res[p['id']]=dict(qp=qs,figs=figs,ms=ms,newfmt=newfmt)
        qt=sum(q['marks'] for q in qs); mt=sum(q['marks'] for q in ms)
        nl=sum(len(q['leaves']) for q in qs)
        flag=''
        if len(qs)!=len(ms): flag+=' NQDIFF'
        mism=[(q['n'],q['marks'],m['marks']) for q,m in zip(qs,ms) if q['marks']!=m['marks']]
        print(f"{p['id']:7s} nq={len(qs):2d} msq={len(ms):2d} leaves={nl:3d} qpmarks={qt:3d} msmarks={mt:3d} figs={len(figs):2d} nofig={sum(1 for f in figs if not f['found'])} qpchars={sum(len(q['text']) for q in qs):6d} mschars={sum(len(q['text']) for q in ms):6d}{flag} mism={mism[:6]}")
    json.dump(res,open(WORK+'/p2_parsed.json','w'))
