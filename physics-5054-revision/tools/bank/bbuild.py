#!/usr/bin/env python3
"""bbuild.py [limit] — renders the crops from the source PDFs and assembles the question bank PDF.

  physics-5054-revision/question_bank/physics_5054_past_paper_questions_with_ms.pdf
  WORK/bank/manifest.json      one record per output page: entry, part, and every source crop placed on it

Every picture in the bank is rendered here, directly from the PDFs in physics-5054/ (colour inversion of the stored
copies undone, rotation removed — see bgeom.Doc). Nothing is taken from an earlier bank.

Layout
  * one entry = one original question in one syllabus subsection; every entry starts on a new page;
  * Paper 2: the question crops follow each other in source order (one crop per source page of the question); the mark
    scheme starts on a new page (landscape page for the landscape schemes); Paper 1: question and the row of the answer
    key on the same page;
  * crops are placed at their original size (scale 1; a crop taller than the page area is reduced to fit and the scale
    is recorded); a crop is never split and nothing inside a crop is moved or removed;
  * grey bars (page header, source line above each crop, page footer) are added by the bank and carry the syllabus
    subsection, year, session, paper, variant, question number, source file name and source page number.
Pictures: 4-bit grey (16 levels), 180 dpi (252 dpi for the small-print Oct/Nov 2019 and 2020 mark schemes), Flate."""
import sys, os, re, json, zlib, hashlib, pickle, collections, datetime
import numpy as np
from bgeom import *
import bentries
REPO='/home/user/p/physics-5054-revision'
QB=REPO+'/question_bank'; os.makedirs(QB,exist_ok=True)
PDF=QB+'/physics_5054_past_paper_questions_with_ms.pdf'
IMG=OUT+'/img'; os.makedirs(IMG,exist_ok=True)
ZQ=2.5
PW,PH=595.28,841.89
TOP=33.0; BOT=17.0; CAP=11.0; GAP=6.0
GREY=(0.90,0.90,0.90); DGREY=(0.32,0.32,0.32)
SECT=bentries.SECT; CHAPTER=bentries.CHAPTER; PARENT=bentries.PARENT

_docs=collections.OrderedDict()
def doc_of(fn):
    if fn in _docs: _docs.move_to_end(fn); return _docs[fn]
    d=Doc(fn); _docs[fn]=d
    if len(_docs)>10: _docs.popitem(last=False)
    return d
_zf={}
def zoom_of(fn,pi):
    """180 dpi; schemes printed in small type (landscape pages reduced onto portrait pages) get proportionally more."""
    k=(fn,pi)
    if k not in _zf:
        d=doc_of(fn); sz=sorted(r['size'] for r in d.rows(pi) if r['text'].strip())
        med=sz[len(sz)//2] if sz else 11.0
        _zf[k]=ZQ*min(1.45,max(1.0,10.3/med)) if '_ms' in fn else ZQ
    return round(_zf[k],3)
def render(spec):
    """spec=(file, page index, x0, y0, x1, y1) in display points -> dict(w,h,z,data): 4-bit grey, flate-compressed."""
    fn,pi,x0,y0,x1,y1=spec; z=zoom_of(fn,pi)
    key=hashlib.sha1(f'{fn}|{pi}|{x0:.2f}|{y0:.2f}|{x1:.2f}|{y1:.2f}|{z}|v4'.encode()).hexdigest()
    cf=f'{IMG}/{key}.pkl'
    if os.path.exists(cf): return pickle.load(open(cf,'rb'))
    d=doc_of(fn)
    a=d.gray(pi,z,clip=(x0,y0,x1,y1))
    h,w=a.shape
    q=np.round(a.astype(np.float32)/255*15).astype(np.uint8)
    if w%2: q=np.concatenate([q,np.full((h,1),15,np.uint8)],axis=1)
    packed=((q[:,0::2]<<4)|q[:,1::2]).astype(np.uint8).tobytes()
    r=dict(w=w,h=h,z=z,data=zlib.compress(packed,9),ink=float((a<200).mean()),wpt=w/z,hpt=h/z)
    pickle.dump(r,open(cf,'wb'))
    return r

def plan_entries(E,G):
    """layout plan: list of pages; page=dict(kind,orient,rid,parts,items) ; item=dict(spec,x,y,w,h,scale,cap,part)."""
    pages=[]
    def size(orient): return (PW,PH) if orient=='P' else (PH,PW)
    cursec=None
    for e in E:
        g=G[e['pid']]
        if e['sec']!=cursec:
            cursec=e['sec']; pages.append(dict(kind='divider',orient='P',sec=cursec,items=[]))
        blocks=[]
        for b in e['qbands']:
            W=g['qp_size'][b[0]][0]
            blocks.append(dict(part='Q',spec=(e['qp'],b[0],0.0,b[1],W,b[2]),orient='P',edges=[b[3],b[4]],
                cap=f"QUESTION  \xb7  {e['qp']}  \xb7  source page {b[0]+1} of {g['qp_pages']}"))
        if e['paper']==1:
            k=e['key']
            blocks.append(dict(part='MS',spec=(e['ms'],k[0],k[1],k[2],k[3],k[4]),orient='P',gap=22.0,keep_x=True,edges=['key','key'],
                cap=f"MARK SCHEME (official answer key)  \xb7  {e['ms']}  \xb7  source page {k[0]+1} of {g['ms_pages']}  \xb7  row for Question {e['q']}"))
        else:
            for j,b in enumerate(e['mbands']):
                W=g['ms_size'][b[0]][0]
                blocks.append(dict(part='MS',spec=(e['ms'],b[0],0.0,b[1],W,b[2]),orient='L' if W>700 else 'P',newpage=(j==0),edges=[b[3],b[4]],
                    cap=f"MARK SCHEME  \xb7  {e['ms']}  \xb7  source page {b[0]+1} of {g['ms_pages']}  \xb7  Question {e['q']}"))
        cur=None
        for blk in blocks:
            fn,pi,x0,y0,x1,y1=blk['spec']
            pw,ph=size(blk['orient'])
            w=x1-x0; h=y1-y0
            avail=ph-TOP-BOT-CAP-2
            s=min(1.0,pw/w,avail/h)
            need=CAP+2+h*s
            gap=blk.get('gap',GAP)
            if cur is None or cur['orient']!=blk['orient'] or blk.get('newpage') or cur['y']+(gap if cur['items'] else 0)+need>ph-BOT+0.01:
                cur=dict(kind='entry',orient=blk['orient'],rid=e['rid'],seq=e['seq'],items=[],y=TOP,parts=[])
                pages.append(cur)
            y=cur['y']+(gap if cur['items'] else 0)
            x=(x0*s if blk.get('keep_x') else (pw-w*s)/2)
            cur['items'].append(dict(spec=list(blk['spec']),x=round(x,2),y=round(y+CAP+2,2),w=round(w*s,2),h=round(h*s,2),scale=round(s,4),cap=blk['cap'],capy=round(y,2),part=blk['part'],edges=blk['edges']))
            if blk['part'] not in cur['parts']: cur['parts'].append(blk['part'])
            cur['y']=y+need
    return pages

def tl(text,font,size): return fitz.get_text_length(text,fontname=font,fontsize=size)
def fit(text,font,size,maxw):
    if tl(text,font,size)<=maxw: return text
    while len(text)>4 and tl(text+' ...',font,size)>maxw: text=text[:-1]
    return text.rstrip(' ,;')+' ...'
def header(shape,pw,line1,line2,right1,right2,note=''):
    shape.draw_rect(fitz.Rect(0,0,pw,TOP-5)); shape.finish(color=None,fill=GREY)
    t1=fit(line1,'hebo',9,pw-36-tl(right1,'helv',7.5)-12)
    shape.insert_text((18,11.5),t1,fontname='hebo',fontsize=9,color=(0,0,0))
    if note:
        # short remark after the subsection title (only if it fits completely)
        x=18+tl(t1,'hebo',9)+14
        if x+tl(note,'helv',7.5)<=pw-18-tl(right1,'helv',7.5)-12: shape.insert_text((x,11.5),note,fontname='helv',fontsize=7.5,color=(0,0,0))
        else: raise RuntimeError('header note does not fit: '+note)
    shape.insert_text((pw-18-tl(right1,'helv',7.5),11.5),right1,fontname='helv',fontsize=7.5,color=DGREY)
    # second line: the list of parts can be long; the type is reduced (not below 6.6 pt) before anything is cut
    maxw=pw-36-tl(right2,'hebo',8)-12; fs=8.0
    while fs>6.6 and tl(line2,'helv',fs)>maxw: fs-=0.1
    if tl(line2,'helv',fs)>maxw: raise RuntimeError('header line does not fit: '+line2)
    shape.insert_text((18,23),line2,fontname='helv',fontsize=fs,color=(0,0,0))
    shape.insert_text((pw-18-tl(right2,'hebo',8),23),right2,fontname='hebo',fontsize=8,color=(0,0,0))
def footer(shape,pw,ph,left,n,N):
    shape.draw_line((18,ph-BOT+3),(pw-18,ph-BOT+3)); shape.finish(color=(0.6,0.6,0.6),width=0.4)
    shape.insert_text((18,ph-5),left,fontname='helv',fontsize=7,color=DGREY)
    t=f'Page {n} of {N}'
    shape.insert_text((pw-18-tl(t,'hebo',8),ph-5),t,fontname='hebo',fontsize=8,color=(0,0,0))

def build(limit=None):
    E=bentries.build()
    if limit: E=E[:limit]
    G=json.load(open(OUT+'/geom.json'))
    plan=plan_entries(E,G)
    byrid={e['rid']:e for e in E}
    NFRONT=2
    N=len(plan)+NFRONT
    # page numbers
    for i,p in enumerate(plan): p['page']=i+1+NFRONT
    first={}                                    # rid -> first page ; sec -> divider page
    secpage={}
    for p in plan:
        if p['kind']=='divider': secpage[p['sec']]=p['page']
        else: first.setdefault(p['rid'],p['page'])
    cnt=collections.Counter((e['sec'],e['paper']) for e in E)
    out=fitz.open()
    out.set_metadata(dict(title='Cambridge O Level Physics 5054 - past-paper question bank with mark schemes (Papers 1 and 2)',
        subject='Whole questions followed by their official mark schemes, by syllabus subsection (1.1-1.7, 3.1-3.4, 4.2)',
        creator='physics-5054-revision/tools/bank/bbuild.py',producer='PyMuPDF',keywords='5054, Physics, O Level, past papers, mark schemes'))
    # ---------------- front matter
    pg=out.new_page(width=PW,height=PH); sh=pg.new_shape()
    sh.draw_rect(fitz.Rect(0,0,PW,120)); sh.finish(color=None,fill=GREY)
    sh.insert_text((40,58),'Cambridge O Level Physics 5054',fontname='hebo',fontsize=22)
    sh.insert_text((40,84),'Past-paper question bank with official mark schemes',fontname='hebo',fontsize=15)
    sh.insert_text((40,104),'Paper 1 (multiple choice) and Paper 2 (theory)  \xb7  May/June 2004 to May/June 2026  \xb7  by syllabus subsection',fontname='helv',fontsize=9.5)
    nq2=len({(e['pid'],e['q']) for e in E if e['paper']==2})
    paras=[
     ('What is in this file',[
      f'{len(E)} entries on {N} pages: {sum(1 for e in E if e["paper"]==1)} Paper 1 questions and {sum(1 for e in E if e["paper"]==2)} Paper 2 entries ({nq2} original Paper 2 questions).',
      'Only questions on the selected syllabus sections: 1.1 to 1.7 (pressure, 1.8, is not included), 3.1 to 3.4 and 4.2.',
      'Only papers that have an official mark scheme in the repository (156 question papers). Questions of papers without a mark scheme are listed in the exclusions file and are not shown.']),
     ('How an entry is built',[
      'An entry is one original question. It shows the WHOLE question as printed (introduction, diagrams, tables, graphs, data, answer spaces and every part), followed at once by the WHOLE official mark scheme of that question.',
      'Paper 2: the question comes first, one picture for each source page it occupies; its mark scheme starts on a new page. A question with EITHER / OR alternatives keeps both alternatives and both schemes.',
      'Paper 1: the question and the row of the published answer key for that question are on the same page.',
      'A Paper 2 question that tests several subsections appears once in each of them. The header names the parts that belong to the subsection and their marks, out of the marks of the question (EITHER / OR question: the marks with one alternative).']),
     ('Order',[
      'Syllabus chapter and subsection; then year (oldest first); session (May/June, then October/November); variant (1, then 2); paper number; original question number. Before 2010 there is one variant.']),
     ('Reading a page',[
      'Grey bars are added by this bank: the header (subsection, year, session, paper, variant, question, record number), the line above each picture (source file name and source page number) and the footer (record ID and page number).',
      'Everything else is a picture of the original PDF at its original size. Page numbers, copyright footers, blank pages and the shared lined answer pages of the older papers are not reproduced. (In the Paper 2 papers of 2004 to 2007 the page number stands on the line of the examiner label at the top of the page and is inside the picture.)',
      'The repository stores the source PDFs with inverted colours; the pictures here show the restored original pages (black on white).']),
     ('Companion files',[
      'physics_5054_question_bank_tracker (every entry and every excluded question), physics_5054_question_bank_exclusions (what is left out and why) and physics_5054_question_bank_audit (counts and checks).',
      'The subsection of each question was assigned in this project by reading the question together with its mark scheme. It is not an official classification by Cambridge.'])]
    y=150
    for title,items in paras:
        sh.insert_text((40,y),title,fontname='hebo',fontsize=11); y+=6
        for it in items:
            r=fitz.Rect(52,y,PW-40,y+80)
            used=sh.insert_textbox(r,it,fontname='helv',fontsize=9.5,align=0)
            sh.insert_text((43,y+11),'\xb7',fontname='hebo',fontsize=11)
            y+=80-used+3 if used>=0 else 80
        y+=13
    footer(sh,PW,PH,'Physics 5054 question bank',1,N); sh.commit()
    pg=out.new_page(width=PW,height=PH); sh=pg.new_shape()
    sh.draw_rect(fitz.Rect(0,0,PW,TOP-5)); sh.finish(color=None,fill=GREY)
    sh.insert_text((18,18),'Contents',fontname='hebo',fontsize=12)
    y=62
    sh.insert_text((40,y),'Syllabus subsection',fontname='hebo',fontsize=9); sh.insert_text((372,y),'Paper 1',fontname='hebo',fontsize=9); sh.insert_text((424,y),'Paper 2',fontname='hebo',fontsize=9); sh.insert_text((478,y),'entries',fontname='hebo',fontsize=9); sh.insert_text((528,y),'page',fontname='hebo',fontsize=9)
    y+=8; lastch=None; lastpar=None
    for s,t in bentries.SECS:
        if s not in secpage: continue
        ch=s.split('.')[0]
        if ch!=lastch:
            y+=16; sh.insert_text((40,y),CHAPTER[ch],fontname='hebo',fontsize=10.5); lastch=ch; lastpar=None; y+=4
        par='.'.join(s.split('.')[:2])
        if len(s.split('.'))==3 and par!=lastpar:
            y+=14; sh.insert_text((52,y),PARENT[par],fontname='hebo',fontsize=9.5); lastpar=par
        y+=14
        ind=64 if len(s.split('.'))==3 else 52
        sh.insert_text((ind,y),f'{s}  {t}',fontname='helv',fontsize=9.5)
        for xr,v in((404,cnt[(s,1)]),(456,cnt[(s,2)]),(506,cnt[(s,1)]+cnt[(s,2)]),(550,secpage[s])):
            v=str(v); sh.insert_text((xr-tl(v,'helv',9.5),y),v,fontname='helv',fontsize=9.5)
    y+=24
    sh.insert_text((40,y),f'Total: {len(E)} entries ({sum(1 for e in E if e["paper"]==1)} Paper 1, {sum(1 for e in E if e["paper"]==2)} Paper 2) on {N} pages.',fontname='hebo',fontsize=9.5)
    footer(sh,PW,PH,'Physics 5054 question bank',2,N); sh.commit()
    toc=[[1,'About this question bank',1],[1,'Contents',2]]
    # ---------------- pages
    xrefs={}; manifest=[dict(page=1,kind='front',orient='P',items=[]),dict(page=2,kind='front',orient='P',items=[])]
    lastch=None
    for p in plan:
        pw,ph=(PW,PH) if p['orient']=='P' else (PH,PW)
        pg=out.new_page(width=pw,height=ph); sh=pg.new_shape()
        if p['kind']=='divider':
            s=p['sec']; ch=s.split('.')[0]
            if ch!=lastch: toc.append([1,CHAPTER[ch],p['page']]); lastch=ch
            toc.append([2,f'{s} {SECT[s]}',p['page']])
            sh.draw_rect(fitz.Rect(0,250,PW,420)); sh.finish(color=None,fill=GREY)
            sh.insert_text((50,292),'Chapter '+CHAPTER[ch],fontname='helv',fontsize=12)
            par='.'.join(s.split('.')[:2])
            if len(s.split('.'))==3: sh.insert_text((50,312),PARENT[par],fontname='helv',fontsize=12)
            fs=24.0
            while tl(f'{s}  {SECT[s]}','hebo',fs)>PW-100 and fs>12: fs-=0.5
            sh.insert_text((50,356),f'{s}  {SECT[s]}',fontname='hebo',fontsize=fs)
            n1=cnt[(s,1)]; n2=cnt[(s,2)]
            sh.insert_text((50,392),f'{n1+n2} entries: {n1} Paper 1 questions, {n2} Paper 2 questions',fontname='helv',fontsize=11)
            sh.insert_text((50,450),'Order: year, session (May/June, then October/November), variant, paper, question number.',fontname='helv',fontsize=9.5,color=DGREY)
            sh.insert_text((50,464),'Each entry: the whole question, followed at once by the whole official mark scheme of that question.',fontname='helv',fontsize=9.5,color=DGREY)
            footer(sh,pw,ph,f'Physics 5054 question bank  \xb7  {s} {SECT[s]}',p['page'],N); sh.commit()
            manifest.append(dict(page=p['page'],kind='divider',orient='P',sec=s,items=[]))
            continue
        e=byrid[p['rid']]
        if first[p['rid']]==p['page']:
            toc.append([3,f"{e['year']} {e['session']}  \xb7  Paper {e['paper']} variant {e['variant']}  \xb7  Question {e['q']}",p['page']])
        what=' and '.join({'Q':'QUESTION','MS':'MARK SCHEME'}[x] for x in p['parts'])
        line1=f"{e['sec']}  {SECT[e['sec']]}"
        line2=f"{e['year']} {e['session']}  \xb7  Paper {e['paper']}  \xb7  Variant {e['variant']}  \xb7  Question {e['q']}"
        if e['paper']==2:
            line2+=f"  \xb7  parts on {e['sec']}: {', '.join(e['parts'])} ({e['marks_sec']} of {e['marks_q']} marks)"
        note='EITHER / OR question: both alternatives and both schemes are shown' if e['either_or'] else ''
        header(sh,pw,line1,line2,f"record {e['seq']} of {len(E)}",what,note)
        sh.commit()
        for it in p['items']:
            spec=tuple(it['spec']); r=render(spec)
            if spec not in xrefs:
                x=out.get_new_xref()
                out.update_object(x,f"<</Type/XObject/Subtype/Image/Width {r['w']}/Height {r['h']}/ColorSpace/DeviceGray/BitsPerComponent 4>>")
                out.update_stream(x,r['data'],compress=False); out.xref_set_key(x,'Filter','/FlateDecode')
                xrefs[spec]=x
            # exact placement: the picture covers w x h points of the source at the recorded scale
            rect=fitz.Rect(it['x'],it['y'],it['x']+r['wpt']*it['scale'],it['y']+r['hpt']*it['scale'])
            pg.insert_image(rect,xref=xrefs[spec],keep_proportion=False)
            it['px']=[r['w'],r['h']]; it['z']=r['z']; it['rect']=[round(v,2) for v in rect]
        sh=pg.new_shape()
        for it in p['items']:
            sh.draw_rect(fitz.Rect(18,it['capy'],pw-18,it['capy']+CAP)); sh.finish(color=None,fill=GREY)
            cap=it['cap']+(f"  \xb7  shown at {it['scale']*100:.0f}% of its size" if it['scale']<0.99 else '')
            sh.insert_text((22,it['capy']+8.2),fit(cap,'helv',7.5,pw-44),fontname='helv',fontsize=7.5,color=(0,0,0))
        footer(sh,pw,ph,f"Physics 5054 question bank  \xb7  record {e['rid']}",p['page'],N); sh.commit()
        manifest.append(dict(page=p['page'],kind='entry',orient=p['orient'],rid=p['rid'],seq=p['seq'],parts=p['parts'],
            items=[dict(spec=it['spec'],rect=it['rect'],scale=it['scale'],part=it['part'],px=it['px'],z=it['z'],edges=it['edges']) for it in p['items']]))
        if p['page']%500==0: print('  pages built',p['page'],'of',N,flush=True)
    out.set_toc(toc)
    json.dump(E,open(OUT+'/entries.json','w'))          # the entries exactly as built
    out.save(PDF,garbage=3,deflate=True,use_objstms=1)
    json.dump(dict(pages=manifest,n_pages=N,n_entries=len(E),first=first,secpage=secpage,built=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
                   images=len(xrefs),zoom=ZQ),open(OUT+'/manifest.json','w'))
    print('pages',N,'| entries',len(E),'| distinct pictures',len(xrefs),'| bookmarks',len(toc),'| file',PDF,'%.1f MB'%(os.path.getsize(PDF)/1e6))
if __name__=='__main__':
    build(int(sys.argv[1]) if len(sys.argv)>1 else None)
