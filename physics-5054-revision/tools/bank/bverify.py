#!/usr/bin/env python3
"""bverify.py [sheets] — verification of the finished bank PDF  -> WORK/bank/verify.json (+ contact sheets with 'sheets')

The PDF is reopened from disk and every page is rendered. Nothing is taken on trust from the build:
 A structure   page count, one record per entry, order of the records (newest first), pages of an entry adjacent,
               question pictures first and scheme pictures directly after them (Paper 1: the answer line), bookmarks,
               file size
 B pictures    The bank is white on black. Pass 1 renders every page: no rendering warning, the page is dark (white
               print on black, not a light page), not blank, nothing outside the pictures, the answer lines and the
               bars, pictures inside the page. Pass 2 takes every picture: it is on the page at the planned place; its
               stored pixels are identical to the INVERTED fresh rendering of the same region of the SOURCE PDF (source
               rendered as printed, 16 grey levels, v -> 15 - v); the page rendered on the pixel grid of the picture
               shows exactly these pixels; its cut lines (outermost pixel rows) are free of ink; it is shown at
               original size
 C text        header, source lines and footer of every page against the entry (subsection, year, session, paper,
               variant, question, source file names and source page numbers, record ID, page number); the marks of the
               question named in the header of a Paper 2 record against the marks printed on the question paper inside
               its pictures (EITHER/OR questions: the marks of one alternative); the answer line of every Paper 1
               record against the key row of the mark scheme, read again from the source PDF
With 'sheets' it also writes contact sheets of ALL pages (WORK/bank/sheets/cs_NNN.png) for the visual review."""
import sys, os, re, json, collections
import numpy as np
from PIL import Image, ImageDraw
from bgeom import *
import bentries
REPO='/home/user/p/physics-5054-revision'
PDF=REPO+'/question_bank/physics_5054_past_paper_questions_with_ms.pdf'
TOP=33.0; BOT=17.0; CAP=11.0
# Cut lines whose outermost pixel rows hold ink. Each was inspected by eye, enlarged, next to the source page (bedge.py):
# the last line of the question (or a frame of the scheme) ends directly at the page footer and is complete in the
# picture. (source file, page index, edge) -> what was seen
EDGE_OK={
 ('5054_s05_qp_2.pdf',1,'bottom'):"the mark '[1]' of the last answer line ends directly above the page footer; the brackets are complete and nothing crosses the cut line",
 ('5054_s04_qp_2.pdf',10,'bottom'):"the mark '[9]', last line of Question 10, touches the footer '[Turn over' (gap 0.12 pt); the cut is at the lower end of the brackets, '[9]' is complete; the last pixel row may carry a faint grey trace of the top of the footer text",
 ('5054_s25_qp_22.pdf',5,'bottom'):"the corner marks of the page (page furniture) stand beside the last answer line of Question 4; the cut is in the blank row below that line and passes through the two corner marks only; nothing of the question is cut",
 ('5054_s26_ms_22.pdf',10,'bottom'):"the frame of the note 'bod' below the table ends 0.5 pt above the page footer; the frame is complete",
 ('5054_s23_qp_21.pdf',4,'bottom'):"'[Total: 6]' ends directly above the footer '[Turn over'; the brackets are complete and nothing crosses the cut line",
 ('5054_s23_qp_22.pdf',10,'bottom'):"'[Total: 9]' ends directly above the footer '[Turn over'; the brackets are complete and nothing crosses the cut line",
}
_docs=collections.OrderedDict()
def doc_of(fn):
    if fn in _docs: _docs.move_to_end(fn); return _docs[fn]
    d=Doc(fn); _docs[fn]=d
    if len(_docs)>10: _docs.popitem(last=False)
    return d
def main(sheets=False):
    M=json.load(open(OUT+'/manifest.json')); E=json.load(open(OUT+'/entries.json')); G=json.load(open(OUT+'/geom.json'))
    P=M['pages']; byrid={e['rid']:e for e in E}
    doc=fitz.open(PDF)
    res=collections.OrderedDict(); fails=collections.defaultdict(list); info={}
    import hashlib
    info['pdf_sha256']=hashlib.sha256(open(PDF,'rb').read()).hexdigest()          # ties these results to one file
    info['geom_sha1']=hashlib.sha1(open(OUT+'/geom.json','rb').read()).hexdigest()
    info['built']=M.get('built')
    def check(name,ok,detail=''):
        res[name]=dict(ok=bool(ok),detail=detail)
    # ---------------- A structure
    check('A1 page count of the PDF equals the build manifest',len(doc)==M['n_pages']==len(P),f'{len(doc)} pages')
    rids=[p['rid'] for p in P if p['kind']=='entry']
    order=[];seen=set()
    for r in rids:
        if r not in seen: order.append(r); seen.add(r)
    check('A2 every entry is in the PDF and no record ID occurs twice',order==[e['rid'] for e in E] and len(set(e['rid'] for e in E))==len(E),f'{len(order)} entries in page order, {len(E)} expected')
    # newest first: later year first; within a year October/November before May/June; then variant, paper, question
    SESS={'October/November':0,'May/June':1}
    keyf=lambda e:(bentries.ORDER[e['sec']],-int(e['year']),SESS[e['session']],e['variant'],e['paper'],e['q'])
    check('A3 order: subsection; newest first (year descending, October/November before May/June); variant, paper, question number',all(keyf(E[i])<keyf(E[i+1]) for i in range(len(E)-1)),
          f"strictly increasing sort key; first record {E[0]['rid']}, last record {E[-1]['rid']}")
    check('A4 one record per original question and subsection',len({(e['pid'],e['q'],e['sec']) for e in E})==len(E),f'{len({(e["pid"],e["q"]) for e in E})} original questions, {len(E)} records')
    bad=[]
    pages_of=collections.defaultdict(list)
    for p in P:
        if p['kind']=='entry': pages_of[p['rid']].append(p)
    for e in E:
        ps=pages_of[e['rid']]; nums=[p['page'] for p in ps]
        if nums!=list(range(nums[0],nums[0]+len(nums))): bad.append((e['rid'],'pages not adjacent')); continue
        items=[it for p in ps for it in p['items']]
        parts=[it['part'] for it in items]
        nq=len(e['qbands']); nm=0 if e['paper']==1 else len(e['mbands'])
        if parts!=['Q']*nq+['MS']*nm: bad.append((e['rid'],f'parts {parts}')); continue
        if nq<1 or (e['paper']==2 and nm<1): bad.append((e['rid'],'question or scheme missing')); continue
        g=G[e['pid']]
        want=[[e['qp'],b[0],0.0,b[1],g['qp_size'][b[0]][0],b[2]] for b in e['qbands']]
        want+=[] if e['paper']==1 else [[e['ms'],b[0],0.0,b[1],g['ms_size'][b[0]][0],b[2]] for b in e['mbands']]
        if [it['spec'] for it in items]!=want: bad.append((e['rid'],'pictures differ from the geometry'))
        # Paper 1: one answer line, on the last page of the record, below the last question picture, for the key row of
        # this question; Paper 2: no answer line
        ans=[(p['page'],p['answer']) for p in ps if p.get('answer')]
        if e['paper']==2:
            if ans: bad.append((e['rid'],'answer line in a Paper 2 record'))
            continue
        if len(ans)!=1 or ans[0][0]!=nums[-1]: bad.append((e['rid'],'answer line missing, repeated or not on the last page')); continue
        an=ans[0][1]; lastq=[it for it in ps[-1]['items']]
        if an['spec']!=[e['ms'],e['key'][0]]+e['key'][1:5] or an['letter']!=e['letter'] or an['letter']!=e['key'][5] or an['q']!=e['q']: bad.append((e['rid'],'answer line does not belong to the key row of the question'))
        if lastq and an['capy']<lastq[-1]['rect'][3]-0.01: bad.append((e['rid'],'answer line above the question picture'))
        if 'MS' not in ps[-1]['parts']: bad.append((e['rid'],'answer line not announced in the header'))
    check('A5 pages of an entry are adjacent; question pictures first, complete scheme directly after, in source order (Paper 1: the answer line directly after the question)',not bad,f'{len(bad)} entries with a problem'); fails['A5']=bad[:50]
    toc=doc.get_toc(simple=True)
    l3=[t for t in toc if t[0]==3]; l2=[t for t in toc if t[0]==2]; l1=[t for t in toc if t[0]==1]
    okb=len(l3)==len(E) and all(t[2]==M['first'][e['rid']] for t,e in zip(l3,E)) and all(f"Question {e['q']}" in t[1] and str(e['year']) in t[1] for t,e in zip(l3,E))
    secs=[s for s,_ in bentries.SECS if s in M['secpage']]
    okb2=len(l2)==len(secs) and all(t[2]==M['secpage'][s] and t[1].startswith(s+' ') for t,s in zip(l2,secs))
    check('A6 bookmarks: one per chapter, subsection and entry, each pointing to the first page of its target',okb and okb2,f'{len(l1)} top-level, {len(l2)} subsection and {len(l3)} question bookmarks')
    size=os.path.getsize(PDF)
    check('A7 file size below 100 MB',size<100*1024*1024,f'{size/1e6:.1f} MB ({size} bytes)')
    # ---------------- pass 1: every page rendered (B0, B1, B2, B4, B5, C1); no source PDF is open yet
    N=len(doc); light=[];blank=[];mism=[];outside=[];edges=[];bounds=[];textbad=[];small=[]; ptxt={}; atxt={}; brightness=[]
    stats=collections.Counter()
    thumbs=[]
    notplaced=[]; pixdiff=[]; xseen={}
    fitz.TOOLS.reset_mupdf_warnings()
    for pi in range(N):
        pg=doc[pi]; p=P[pi]; pw,ph=pg.rect.width,pg.rect.height
        pix=pg.get_pixmap(matrix=fitz.Matrix(1,1),colorspace=fitz.csGRAY,alpha=False)
        a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width)
        if sheets:
            im=Image.fromarray(a); tw=118 if pw<700 else 166; thumbs.append((pi+1,im.resize((tw,int(a.shape[0]*tw/a.shape[1])),Image.LANCZOS)))
        stats['pages rendered']+=1
        # white on black: a page is mostly black. A page that is not (a picture left un-inverted, a white page) is light.
        bright=float((a>128).mean()); brightness.append((round(bright,4),pi+1))
        if a.mean()>100 or bright>0.40: light.append((pi+1,round(float(a.mean()),1),round(bright,3)))
        orient='P' if pw<ph else 'L'
        if orient!=p['orient']: bounds.append((pi+1,'orientation differs from the manifest'))
        if pg.rotation: bounds.append((pi+1,'page carries a rotation'))
        txt=pg.get_text('text')
        if f'Page {pi+1} of {N}' not in txt: textbad.append((pi+1,'page number'))
        if p['kind']!='entry':
            if (a>128).mean()<0.002: blank.append((pi+1,'front or divider page without content'))
            continue
        e=byrid[p['rid']]
        if e['paper']==2: ptxt[pi]=txt
        else: atxt[pi]=txt
        need=[f"{e['sec']}  {bentries.SECT[e['sec']]}"[:40],f"{e['year']} {e['session']}",f"Paper {e['paper']}",f"Variant {e['variant']}",f"Question {e['q']}",f"record {e['rid']}",f"record {e['seq']} of {len(E)}"]
        if e['paper']==2: need.append(f"parts on {e['sec']}: {', '.join(e['parts'])} ({e['marks_sec']} of {e['marks_q']} marks)")
        for it in p['items']:
            need.append(it['spec'][0]); need.append(f"source page {it['spec'][1]+1} of")
        an=p.get('answer')
        if an: need+=[an['spec'][0],f"source page {an['spec'][1]+1} of",f"row for Question {an['q']}",f"Answer: {an['letter']}"]
        for t in need:
            if t not in txt: textbad.append((pi+1,t)); break
        mask=np.zeros(a.shape,bool)
        mask[:int(TOP)+1,:]=True; mask[int(ph-BOT):,:]=True
        prev=TOP-6; inkin=0
        for it in p['items']:
            x0,y0,x1,y1=it['rect']
            if y0<TOP-0.5 or y1>ph-BOT+1.0 or x0<-0.5 or x1>pw+1.5 or y0<prev: bounds.append((pi+1,[round(v,1) for v in it['rect']]))
            prev=y1
            cy0=y0-CAP-2
            mask[max(0,int(cy0)-1):int(cy0+CAP)+2,:]=True
            ix0,iy0,ix1,iy1=max(0,int(round(x0))),int(round(y0)),min(a.shape[1],int(round(x1))),min(a.shape[0],int(round(y1)))
            mask[max(0,iy0-1):iy1+1,max(0,ix0-1):ix1+1]=True
            inkin+=int((a[iy0:iy1,ix0:ix1]>128).sum())
        if an:
            # the answer line of a Paper 1 record: its source line and the zone reserved for the text
            x0,y0,x1,y1=an['rect']
            if y0<prev or y1>ph-BOT+1.0: bounds.append((pi+1,'answer line',[round(v,1) for v in an['rect']]))
            mask[max(0,int(an['capy'])-1):int(an['capy']+CAP)+2,:]=True
            mask[max(0,int(y0)-1):int(y1)+1,:]=True
            if int((a[int(y0):int(y1),:]>128).sum())<20: blank.append((pi+1,'answer line without text'))
        if p['items'] and inkin<40: blank.append((pi+1,'no ink inside the pictures of the page'))
        out=(a>95)&~mask
        if out.sum()>3: outside.append((pi+1,int(out.sum())))
        if (pi+1)%1000==0: print('  pass 1: pages rendered',pi+1,'of',N,flush=True)
    warn=fitz.TOOLS.mupdf_warnings()
    check('B0 every page of the PDF renders without a MuPDF error or warning',not warn.strip(),f'{N} pages rendered; warnings: {warn.strip()[:200] or "none"}')
    # ---------------- pass 2: every picture (B3a, B3b, B3c, B6, B7)
    scales=collections.Counter(); mindpi=1e9
    for pi in range(N):
        pg=doc[pi]; p=P[pi]
        if p['kind']!='entry': continue
        imgs=pg.get_image_info(xrefs=True)
        if len(imgs)!=len(p['items']): notplaced.append((pi+1,'number of pictures on the page',len(imgs),len(p['items'])))
        for it in p['items']:
            fn,spi,sx0,sy0,sx1,sy1=it['spec']
            stats['pictures placed']+=1
            # B3a: the picture is on the page at the planned position
            hit=[im for im in imgs if max(abs(im['bbox'][k]-it['rect'][k]) for k in range(4))<0.6]
            if len(hit)!=1: notplaced.append((pi+1,it['spec'][:2],len(hit))); continue
            xref=hit[0]['xref']; bb=hit[0]['bbox']
            px=fitz.Pixmap(doc,xref)
            got=np.frombuffer(px.samples,dtype=np.uint8).reshape(px.height,px.width)
            if xref not in xseen:
                # B3b: the stored pixels are identical to the inverted fresh rendering of the source region: the source
                # is rendered as printed (black on white), reduced to 16 grey levels and inverted (white on black)
                fresh=doc_of(fn).gray(spi,it['z'],clip=(sx0,sy0,sx1,sy1))
                want=((15-np.round(fresh.astype(np.float32)/255*15))*17).astype(np.uint8)
                same=got.shape==want.shape and bool((got==want).all())
                xseen[xref]=tuple(it['spec'])
                stats['distinct pictures']+=1
                if not same: pixdiff.append((pi+1,it['spec'][:2],got.shape,want.shape))
                if (got>128).mean()<0.0008: blank.append((pi+1,'picture nearly empty',it['spec'][:2]))
                # B6: the cut lines. The outermost two pixel rows of the picture (centre 88 % of the width; margin
                # rules and margin text are at the sides) must be free of ink. Rows of the key table and cuts placed
                # on a table rule end on a ruled line by design.
                ww=got.shape[1]; xa=int(ww*0.06); xb=int(ww*0.94)
                for nm,row,kind in(('top',got[:2,xa:xb],it['edges'][0]),('bottom',got[-2:,xa:xb],it['edges'][1])):
                    if kind in('key','rule'): stats['edges on a ruled line by design']+=1; continue
                    stats['picture edges checked']+=1
                    n=int((row>95).sum())                    # ink is light on the inverted picture
                    if n>3: edges.append((pi+1,nm,it['spec'],n))
            elif xseen[xref]!=tuple(it['spec']): pixdiff.append((pi+1,it['spec'][:2],'picture object reused for a different region'))
            # B3c: the page as rendered shows exactly the stored picture. The region of the page is rendered on the
            # pixel grid of the picture, so every pixel can be compared (an overlay, a mirrored or displaced picture
            # or a wrong colour interpretation would show).
            zx=px.width/(bb[2]-bb[0]); zy=px.height/(bb[3]-bb[1])
            pm=pg.get_pixmap(matrix=fitz.Matrix(1,0,0,1,-bb[0],-bb[1])*fitz.Matrix(zx,zy),clip=fitz.Rect(bb),colorspace=fitz.csGRAY,alpha=False)
            O=np.frombuffer(pm.samples,dtype=np.uint8).reshape(pm.height,pm.width)
            stats['placements compared']+=1
            if O.shape!=got.shape: mism.append((pi+1,it['spec'][:2],'size',O.shape,got.shape))
            else:
                nd=int((O!=got).sum())
                if nd: mism.append((pi+1,it['spec'][:2],nd))
            # B7: size and resolution as shown
            sc=round(((bb[2]-bb[0])/(sx1-sx0)),3); scales[sc]+=1
            mindpi=min(mindpi,zx*72,zy*72)
            if sc<0.99 or min(zx,zy)*72<178: small.append((pi+1,it['spec'][:2],sc,round(min(zx,zy)*72)))
        if (pi+1)%1000==0: print('  pass 2: pages checked',pi+1,'of',N,flush=True)
    check('B1 every page is white on black: no page is light (every page rendered; a page counts as light if more than 40 % of it is bright)',not light,
          f"{len(light)} light pages of {N}; the brightest page is {max(brightness)[0]*100:.0f} % bright (page {max(brightness)[1]})"); fails['B1']=light[:50]
    info['brightest']=sorted(brightness,reverse=True)[:60]
    check('B2 no blank page and no empty picture',not blank,f'{len(blank)} findings'); fails['B2']=blank[:50]
    check('B3a every picture is on its page at the planned position (picture boxes read back from the PDF)',not notplaced,f"{stats['pictures placed']} placements, {len(notplaced)} not found"); fails['B3a']=notplaced[:50]
    check('B3b the stored pixels of every distinct picture are identical to the inverted fresh rendering of its region of the source PDF',not pixdiff,f"{stats['distinct pictures']} distinct pictures, {len(pixdiff)} differ"); fails['B3b']=pixdiff[:50]
    check('B3c every page, rendered on the pixel grid of its pictures, shows exactly the stored pictures (nothing over them, none displaced)',not mism,f"{stats['placements compared']} placements compared pixel by pixel, {len(mism)} differ"); fails['B3c']=mism[:50]
    check('B4 nothing printed outside the pictures, the answer lines and the bars; the rest of every page is black',not outside,f'{len(outside)} pages with stray ink'); fails['B4']=outside[:50]
    check('B5 pictures lie inside the page area, below the header and above the footer, without overlap; orientation as planned; no page rotation',not bounds,f'{len(bounds)} findings'); fails['B5']=bounds[:50]
    known=[x for x in edges if (x[2][0],x[2][1],x[1]) in EDGE_OK]; new_edges=[x for x in edges if (x[2][0],x[2][1],x[1]) not in EDGE_OK]
    info['edges']=edges; info['edges_reviewed']=[dict(page=x[0],edge=x[1],source=x[2][0],source_page=x[2][1]+1,pixels=x[3],reason=EDGE_OK[(x[2][0],x[2][1],x[1])]) for x in known]
    check('B6 the cut lines (outermost pixel rows of every picture) are free of ink; cuts on a table rule excepted',not new_edges,
          f"{stats['picture edges checked']} cut lines checked, {stats['edges on a ruled line by design']} on a ruled line by design; {len(edges)} with ink, of which {len(known)} reviewed and accepted (listed in the audit), {len(new_edges)} not reviewed"); fails['B6']=new_edges[:50]
    check('B7 every picture is shown at its original size (99.9 % or more) and at 180 dpi or more',not small,f"{stats['placements compared']} placements; scales {dict(sorted(scales.items()))}; lowest resolution {mindpi:.0f} dpi"); fails['B7']=small[:50]
    check('C1 header, source lines, record ID and page number of every page agree with the entry',not textbad,f'{len(textbad)} pages with a missing text'); fails['C1']=textbad[:50]
    # ---------------- C2: the marks named in the header of the Paper 2 records, against the marks printed on the question paper.
    # Read from the PDF: the header text of every page. Read from the source: the text rows inside the question pictures.
    RX_HDR=re.compile(r'\((\d+) of (\d+) marks\)'); RX_TOT=re.compile(r'\[\s*Total\s*:?\s*(\d+)\s*\]',re.I); RX_MK=re.compile(r'\[\s*(\d{1,2})\s*\]')
    REMARK='EITHER / OR question'
    recs=collections.OrderedDict()
    for pi,p in enumerate(P):
        if p['kind']=='entry' and pi in ptxt: recs.setdefault(p['rid'],[]).append(pi)
    marksbad=[]; nplain=0; neo=[]; byq=collections.defaultdict(list)
    for rid,pis in recs.items():
        e=byrid[rid]
        hd=set()
        for pi in pis:
            m=RX_HDR.search(ptxt[pi]); hd.add((m.group(1),m.group(2),REMARK in ptxt[pi]) if m else None)
        if len(hd)!=1 or None in hd: marksbad.append((pis[0]+1,rid,'header marks missing or not the same on all pages of the record',sorted(map(str,hd)))); continue
        a_,b_,rem=list(hd)[0]; a_=int(a_); b_=int(b_)
        ei=[];orr=[];tot=[];mk=[];before=[]
        for pi in pis:
            for it in P[pi]['items']:
                if it['part']!='Q': continue
                fn,spi,sx0,sy0,sx1,sy1=it['spec']
                for r in doc_of(fn).rows(spi):
                    if not sy0<=(r['y0']+r['y1'])/2<=sy1: continue
                    t=r['text'].strip()
                    if re.match(r'^(\d{1,2}\s+)?EITHER\b',t): ei.append(t[:40])
                    elif re.match(r'^(\d{1,2}\s+)?OR\b',t) and ei: orr.append(t[:40])
                    tot+=[int(x) for x in RX_TOT.findall(t)]
                    for x in RX_MK.findall(RX_TOT.sub(' ',t)):
                        mk.append(int(x))
                        if not orr: before.append(int(x))
        alt=bool(ei and orr)
        if alt!=rem: marksbad.append((pis[0]+1,rid,f'EITHER/OR rows in the pictures: {alt}; remark in the header: {rem}'))
        if not alt:
            nplain+=1
            if sum(mk)!=b_ or (tot and set(tot)!={b_}): marksbad.append((pis[0]+1,rid,f'header: {b_} marks; printed marks {mk} = {sum(mk)}; printed totals {tot}'))
        else:
            want=tot[0] if tot and len(set(tot))==1 else (sum(before) if not tot else None)
            neo.append(f"{rid}: {b_} marks ({'printed total' if tot else 'printed marks above the OR alternative'})")
            if want!=b_: marksbad.append((pis[0]+1,rid,f'EITHER/OR question, header: {b_} marks; printed totals {tot}; printed marks above OR {before}'))
        if not 1<=a_<=b_: marksbad.append((pis[0]+1,rid,f'{a_} of {b_} marks'))
        byq[(e['pid'],e['q'])].append((a_,b_))
    for k,v in byq.items():
        if len({b for a,b in v})!=1 or sum(a for a,b in v)>v[0][1]: marksbad.append((0,str(k),f'records of one question: {v}'))
    check('C2 marks of the question named in the header of every Paper 2 record = marks printed on the question paper inside its pictures',not marksbad,
          f"{len(recs)} records of {len(byq)} questions: {nplain} records without alternatives (sum of all printed '[n]' and the printed '[Total: n]'), {len(neo)} records of EITHER/OR questions (marks of one alternative); {len(marksbad)} differ"); fails['C2']=marksbad[:50]
    info['either_or_records']=neo
    # ---------------- C3: the answer line of the Paper 1 records. Read from the PDF: the text of the page. Read from the
    # source: the words inside the key row of the mark scheme (question number, key letter and, where printed, the mark),
    # and the key string that ../parse_ms1.py read from the whole key table.
    keys=json.load(open(WORK+'/keys_p1.json'))
    RX_ANS=re.compile(r'^Answer: ([A-D])$',re.M)
    ansbad=[]; nans=0; letters=collections.Counter()
    for pi,p in enumerate(P):
        if p['kind']!='entry' or pi not in atxt: continue
        e=byrid[p['rid']]; an=p.get('answer'); found=RX_ANS.findall(atxt[pi])
        if not an:
            if found: ansbad.append((pi+1,p['rid'],'answer text on a page without an answer line'))
            continue
        nans+=1
        if len(found)!=1: ansbad.append((pi+1,p['rid'],f'answer lines in the page text: {found}')); continue
        fn,spi,kx0,ky0,kx1,ky1=an['spec']
        ws=sorted(w[4] for w in doc_of(fn).page(spi).get_text('words') if kx0<=(w[0]+w[2])/2<=kx1 and ky0<=(w[1]+w[3])/2<=ky1)
        src=[w for w in ws if w in ('A','B','C','D')]
        okrow=ws in (sorted([str(e['q']),found[0]]),sorted([str(e['q']),found[0],'1']))
        if not okrow or len(src)!=1 or found[0]!=e['letter'] or found[0]!=keys[e['pid']]['key'][e['q']-1] or fn!=e['ms']:
            ansbad.append((pi+1,p['rid'],f"page: {found[0]}; key row of {fn} p. {spi+1}: {ws}; findings: {e['letter']}; key table: {keys[e['pid']]['key'][e['q']-1]}"))
        letters[found[0]]+=1
    n1=sum(1 for e in E if e['paper']==1)
    check('C3 Paper 1: the answer typeset on the page = the key letter in the row of that question in the mark scheme (read again from the source PDF) = the key of the verified findings',
          not ansbad and nans==n1,f"{nans} answer lines of {n1} Paper 1 records; {len(ansbad)} differ; letters {dict(sorted(letters.items()))}"); fails['C3']=ansbad[:50]
    info['theme']='white on black'; info['order']='newest first'; info['p1_answers']=nans
    info['orientation']=dict(collections.Counter(p['orient'] for p in P))
    info['pages']=N; info['entries']=len(E); info['size']=size; info['bookmarks']=len(toc); info['pictures']=stats['pictures placed']; info['distinct_pictures']=stats['distinct pictures']; info['edges_checked']=stats['picture edges checked']; info['edges_by_design']=stats['edges on a ruled line by design']; info['scales']={str(k):v for k,v in sorted(scales.items())}; info['min_dpi']=round(mindpi)
    info['pages_by_kind']=dict(collections.Counter(p['kind'] for p in P))
    ok=all(v['ok'] for v in res.values())
    json.dump(dict(ok=ok,checks=res,fails={k:v for k,v in fails.items() if v},info=info,when=__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')),open(OUT+'/verify.json','w'))
    for k,v in res.items(): print('PASS' if v['ok'] else 'FAIL',k,'|',v['detail'])
    for k,v in fails.items():
        if v: print('  ',k,v[:12])
    print('RESULT:','all checks passed' if ok else 'FAILED')
    if sheets:
        os.makedirs(OUT+'/sheets',exist_ok=True)
        for f in os.listdir(OUT+'/sheets'): os.remove(OUT+'/sheets/'+f)
        W=1740; x=y=0; rowh=0; cur=[]; n=0
        def flush():
            nonlocal cur,x,y,rowh,n
            if not cur: return
            sh=Image.new('L',(W,y+rowh),96)
            for im,px,py in cur: sh.paste(im,(px,py))
            n+=1; sh.save(f'{OUT}/sheets/cs_{n:03d}.png'); cur=[];x=y=0;rowh=0
        for num,im in thumbs:
            t=Image.new('L',(im.width,im.height+11),255); t.paste(im,(0,11)); ImageDraw.Draw(t).text((2,0),str(num),fill=0)
            if x+t.width>W: x=0; y+=rowh+5; rowh=0
            if y+t.height>1560: flush()
            cur.append((t,x,y)); x+=t.width+5; rowh=max(rowh,t.height)
        flush(); print('contact sheets:',n)
    return ok
if __name__=='__main__':
    sys.exit(0 if main('sheets' in sys.argv[1:]) else 1)
