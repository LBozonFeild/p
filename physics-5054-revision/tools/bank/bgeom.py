#!/usr/bin/env python3
"""bgeom.py — crop geometry for the Physics 5054 question bank.

For every verified question paper / mark scheme pair it finds, in the SOURCE PDFs,
  Paper 2 QP : the page bands of every numbered question (whole question, all sub-parts)
  Paper 2 MS : the page bands of the complete scheme of every question
  Paper 1 QP : the band of every multiple-choice question
  Paper 1 MS : the row of the answer key of every question
and writes them to WORK/bank/geom.json.

Coordinates are DISPLAY coordinates in points (top-left origin). Rotated pages (the landscape mark schemes carry
/Rotate 90) are normalised with Page.remove_rotation(), which applies the page's rotation matrix to the content,
so text positions, drawings and rendered pixels all share the display coordinate system.

How a boundary is placed
  * question starts are found exactly as in the verified parsers (parse_p1.py, parse_p2.py): the expected next
    question number at the left margin (QP, old MS) or in the first table column (new MS);
  * the cut between two questions on one page is put in the blank band directly above the next question's first
    row (or above its heading rows / table header), found in an ink profile of the rendered page — never by text
    confidence alone and never through ink;
  * page furniture (page number, copyright footer, 'Turn over', 'BLANK PAGE', copyright notices) is masked and is
    never part of a crop; blank pages give no crop;
  * a crop always spans the full page width, so nothing can be clipped at the sides.
"""
import sys, os, re, json, collections
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.dirname(HERE))
import numpy as np
from lib import *
import parse_p1, parse_p2
Z=2.0            # pixels per point of the ink profile
DARK=200         # a pixel darker than this is ink (third-party watermarks in the 2026 files are lighter)
PAD=4.0          # white margin kept around the ink of a crop, in points
OUT=WORK+'/bank'
os.makedirs(OUT,exist_ok=True)

def fix_arena(doc,page):
    """Undo the colour-inversion wrapper of the repository copies ('%ArenaInvertBase … %ArenaInvertInvert').
    The wrapper paints a white base with `1 1 1 rg`, runs the original page content and then inverts the whole page
    with a white rectangle in a blend mode. Besides showing white text on black, it leaves the fill colour white for
    the original content, so anything the original drew in the default (black) fill colour — in the older papers
    whole blocks of text — is invisible in the stored copy. The fix keeps the original content only: it resets the
    default colours after the base rectangle and drops the inverting rectangle. Returns True if the page was wrapped."""
    if doc.xref_get_key(page.xref,'ArenaInvert')[1]!='true': return False
    data=page.read_contents()
    if not data.startswith(b'%ArenaInvertBase'): raise RuntimeError('ArenaInvert page without the expected prefix')
    key=b're f\nq\n'
    i=data.find(key); j=data.rfind(b'%ArenaInvertInvert')
    if not (0<i<240 and j>i): raise RuntimeError('ArenaInvert wrapper not recognised')
    tail=data[j:]
    if tail.count(b're f')!=1 or not tail.strip().endswith(b'Q'): raise RuntimeError('ArenaInvert suffix not recognised')
    new=data[:i+len(key)]+b'0 g 0 G\n'+data[i+len(key):j]+b'Q\n'
    xref=doc.get_new_xref(); doc.update_object(xref,'<<>>'); doc.update_stream(xref,new)
    page.set_contents(xref)
    return True

class Doc:
    """one source PDF with the stored colour inversion undone and page rotation removed (display coordinates)."""
    def __init__(self,fn,src=None):
        self.fn=fn; self.doc=fitz.open(os.path.join(src or SRC,fn)); self.n=len(self.doc)
        self.inv=[];self.rot=[]
        for pi in range(self.n):
            self.inv.append(fix_arena(self.doc,self.doc[pi]))
            pg=self.doc[pi]
            self.rot.append(pg.rotation)
            if pg.rotation: pg.remove_rotation()
        self._gray={};self._rows={}
    def page(self,pi): return self.doc[pi]
    def size(self,pi):
        r=self.doc[pi].rect; return r.width,r.height
    def gray(self,pi,z=Z,clip=None):
        """rendered page (or clip) as uint8 array, black ink on white.
        MuPDF's store is emptied before every rendering: a bitmap that an earlier call left in the store at another
        resolution (get_text('dict') decodes embedded bitmaps at full size) would otherwise be reused and give
        slightly different pixels for hatchings and dot patterns. With an empty store the same region always
        renders to the same pixels, whatever was done with the document before."""
        key=(pi,z) if (clip is None and z==Z) else None
        if key and key in self._gray: return self._gray[key]
        fitz.TOOLS.store_shrink(100)
        pg=self.doc[pi]
        pix=pg.get_pixmap(matrix=fitz.Matrix(z,z),clip=fitz.Rect(clip) if clip else None,alpha=False,colorspace=fitz.csGRAY)
        a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width).copy()
        if key:
            if len(self._gray)>4: self._gray={}
            self._gray[key]=a
        return a
    def rows(self,pi):
        if pi not in self._rows: self._rows[pi]=page_rows(self.doc[pi])
        return self._rows[pi]

# ---------------------------------------------------------------- page furniture
P1_BOILER=parse_p1.BOILER; QP_BOILER=parse_p2.QP_BOILER; EXAM_USE=parse_p2.EXAM_USE; MS_HDR=parse_p2.MS_HDR
def classify_qp(doc,pi,paper):
    """[(row, class)] with class in content|dots|top|bottom|boiler; mirrors qp_rows()/clean_rows() of the parsers."""
    H=doc.size(pi)[1]; out=[]
    for r in doc.rows(pi):
        sp=[s for s in r['spans'] if not (s['x0']>515 and s['text'].strip() in EXAM_USE)]
        if not sp: out.append((r,'exam')); continue
        t=r['text'].strip()
        if len(sp)!=len(r['spans']):
            # the row shares its line with the label of the examiner column: judge it by its own spans only
            t=' '.join(x['text'].strip() for x in sp).strip()
        if not t: out.append((r,'empty')); continue
        if r['y0']<56 and re.fullmatch(r'\d{1,2}',t): out.append((r,'top')); continue
        if paper==2:
            if QP_BOILER.search(t) or re.match(r'^(Trace ID:|Re-uploading, mirroring)',t): out.append((r,'boiler')); continue
            if r['y0']>H-62 and (re.search(r'5054/\d',t) or 'UCLES' in t or 'Turn over' in t or r['size']<9): out.append((r,'bottom')); continue
            if r['size']<6: out.append((r,'boiler')); continue
        else:
            if P1_BOILER.search(t) or QP_BOILER.search(t): out.append((r,'boiler')); continue
            if r['y0']>H-62 and (re.search(r'5054/\d',t) or 'UCLES' in t or 'Turn over' in t or r['size']<9): out.append((r,'bottom')); continue
            if re.fullmatch(r'5054/\d+/[A-Z]/[A-Z]/\d+',t): out.append((r,'bottom')); continue
            if r['size']<8.6 and r['y0']>H-120: out.append((r,'boiler')); continue
        if re.fullmatch(r'[.\s…]+',t): out.append((r,'dots')); continue
        out.append((r,'content'))
    return out
def classify_ms(doc,pi):
    H=doc.size(pi)[1]; out=[]
    for r in doc.rows(pi):
        t=r['text'].strip()
        if not t: out.append((r,'empty')); continue
        if HDR_RX.match(t): out.append((r,'content')); continue      # table header row: part of the scheme
        if r['y0']<64 and (MS_HDR.search(t) or re.search(r'Mark Scheme|Syllabus|5054|PUBLISHED|GCE|Cambridge O',t)): out.append((r,'top')); continue
        if r['y0']>H-45 and (re.search(r'©|UCLES|Cambridge|Page \d+ of|Turn over',t)): out.append((r,'bottom')); continue
        if re.match(r'^©\s*(UCLES|University of Cambridge|Cambridge)',t): out.append((r,'bottom')); continue
        if re.match(r'^(Trace ID:|Re-uploading, mirroring)',t): out.append((r,'boiler')); continue
        out.append((r,'content'))
    return out

COPY=re.compile(r'^(Permission to reproduce|To avoid the issue of disclosure|University of Cambridge International Examinations is part|Cambridge International Examinations is part|Cambridge Assessment International Education is part|Every reasonable effort|reasonable effort has been made|Copyright Acknowledgements)',re.I)
def margin_rule_cols(dark):
    """pixel columns (Z px/pt) of the vertical rule of the examiner column of the 2004-2013 question papers.
    Only a rule in the right margin (515-545 pt from the left edge) that is ONE unbroken line over more than half of the
    page height counts. (A test on the share of dark rows alone also hit the vertical lines of graph grids and a column
    in which the axes of several small graphs line up; the bottom of an axis was then outside the crop:
    Oct/Nov 2006 Paper 1 Question 33.)"""
    n=dark.shape[0]; out=[]
    for c in range(int(515*Z),min(dark.shape[1],int(545*Z))):
        col=dark[:,c]
        if col.mean()<=0.4: continue
        d=np.diff(np.concatenate(([0],col.astype(np.int8),[0])))
        run=(np.flatnonzero(d==-1)-np.flatnonzero(d==1)).max()
        if run>0.5*n: out.append(c)
    return out

class PageInk:
    """ink profile of one page with the furniture masked: self.p[k] is True when row k (1/Z pt high) holds ink."""
    def __init__(self,doc,pi,cls,xr,is_ms):
        W,H=doc.size(pi); self.W=W; self.H=H
        a=doc.gray(pi)
        self.n=a.shape[0]
        x0=max(0,int(xr[0]*Z)); x1=min(a.shape[1],int(xr[1]*Z))
        dark=(a<DARK)
        dark[:,:x0]=False; dark[:,x1:]=False
        if not is_ms:
            # examiner-use column of the 2006-2011 papers: its label and its long vertical rule are furniture
            for r,c in cls:
                for sp in r['spans']:
                    if sp['x0']>515 and sp['text'].strip() in EXAM_USE:
                        dark[max(0,int((sp['y0']-1)*Z)):int((sp['y1']+1)*Z)+1, max(0,int((sp['x0']-1)*Z)):int((sp['x1']+1)*Z)+1]=False
            for c in margin_rule_cols(dark):
                dark[:,max(0,c-2):c+3]=False
        self.frac=dark[:,x0:x1].mean(axis=1)        # share of the width that is inked, per row
        p=dark.any(axis=1)
        zt=0.0; zb=H
        tops=[r for r,c in cls if c=='top']; bots=[r for r,c in cls if c=='bottom']
        if tops: zt=max(r['y1'] for r in tops)+1.0
        if bots: zb=min(r['y0'] for r in bots)-1.0
        if not is_ms:
            # copyright notice at the foot of the last page: everything from its first line down is furniture
            cr=[r for r,c in cls if r['size']<=7.6 and r['y0']>H-240 and COPY.search(r['text'].strip())]
            if cr: zb=min(zb,min(r['y0'] for r in cr)-1.0)
            for r,c in cls:
                if c=='boiler' and r['y0']>H-62: zb=min(zb,r['y0']-1.0)
            if cr:
                # a ruled line separates the notice from the question: it is furniture too
                k=int(zb*Z); lo=max(0,int((zb-14)*Z))
                for j in range(k,lo,-1):
                    if self.frac[j]>0.5:
                        while j>lo and self.frac[j-1]>0.5: j-=1
                        zb=j/Z-0.5; break
        if is_ms and tops:
            # the header of the older schemes is a ruled box: move the zone end to the first blank row after it
            k=int(zt*Z); lim=min(self.n-1,int((zt+14)*Z))
            while k<lim and p[k]: k+=1
            zt=k/Z
        rowany=dark.any(axis=1)                    # ink per row, furniture rows included (label and rule of the examiner column excluded)
        self.zt0=zt; self.zb0=zb                   # zone limits given by the furniture text rows, before they are moved to a blank row
        self.notes=[]; self.top_extra=None; self.info=[]
        if not is_ms:
            ex=[sp for r,c in cls for sp in r['spans'] if sp['x0']>515 and sp['text'].strip() in EXAM_USE]
            if ex and min(sp['y0'] for sp in ex)<zt+25:
                # 'For Examiner's Use' label beside the first lines: a crop from the page top starts above the label, so the
                # label is never cut through (the page number beside it is then inside the crop as well)
                self.top_extra=min(sp['y0'] for sp in ex)-2.0
        content=[(r['y0']+r['y1'])/2 for r,c in cls if c in('content','dots')]
        # a zone boundary must lie in a blank row: furniture graphics (corner marks, codes) can reach past the footer text
        k=min(self.n-1,int(round(zb*Z)))
        if rowany[k] and bots:
            # The box of a footer row starts a little above its glyphs. If the ink at the boundary is not in the columns of
            # the footer text and a blank row follows above the first ink of the footer text, the boundary belongs in
            # that blank row: a frame or table rule that ends just above the footer is then inside the crop, complete.
            ftop=None
            for r in bots:
                if r['y0']-1.0>zb+3.0: continue            # only the footer row(s) that set the boundary
                for sp in r['spans']:
                    xa_=max(0,int((sp['x0']-1)*Z)); xb_=int((sp['x1']+1)*Z)+1
                    idx=np.flatnonzero(dark[k:min(self.n,int(r['y1']*Z)+1),xa_:xb_].any(axis=1))
                    if len(idx): ftop=k+int(idx[0]) if ftop is None else min(ftop,k+int(idx[0]))
            if ftop is not None and ftop>k:
                j=k
                while j<ftop and rowany[j]: j+=1
                if j<ftop and not rowany[j]:
                    zb=(j+0.5)/Z; k=min(self.n-1,int(round(zb*Z)))
                    self.info.append(f'frame or rule ends directly above the page footer: bottom limit moved down to the blank row at y={zb:.2f}')
        if rowany[k]:
            j=k
            while j>0 and rowany[j] and (k-j)<16*Z: j-=1
            if not rowany[j] and not any(j/Z<=c<=zb for c in content): zb=j/Z
            else:
                # the last line of the question sits directly above the footer (or beside corner marks): put the boundary in
                # the first blank row below that line, measured over the width of the line itself
                near=[r for r,c in cls if c in('content','dots') and r['y1']>zb-16 and (r['y0']+r['y1'])/2<zb+2]
                done=False
                if near:
                    xa=max(0,int((min(r['x0'] for r in near)-2)*Z)); xb=int((max(r['x1'] for r in near)+2)*Z)
                    col=dark[:,xa:xb].any(axis=1)
                    j=int(max((r['y0']+r['y1'])/2 for r in near)*Z); lim=min(self.n-1,int((zb+9)*Z))
                    j0=j
                    while j<lim and col[j]: j+=1
                    if not col[j]: zb=(j+1)/Z; done=True
                    else:
                        # no blank row at the resolution of the profile between the last line and the footer:
                        # look again at 8 pixels per point (a gap of a fraction of a point is enough to separate them)
                        fine=(doc.gray(pi,8.0,clip=(xa/Z,j0/Z,xb/Z,lim/Z))<DARK).any(axis=1)
                        blank=np.flatnonzero(~fine)
                        if len(blank):
                            yb_=j0/Z+blank[0]/8.0; gap=1
                            while blank[0]+gap<len(fine) and not fine[blank[0]+gap]: gap+=1
                            zb=np.floor(yb_*10+1e-6)/10; done=True
                            self.info.append(f'last line of the question touches the page footer: bottom edge put at y={zb:.1f}, at a gap of {gap/8.0:.2f} pt found at 8 pixels per point')
                        else:
                            cnt=dark[j0:lim,xa:xb].sum(axis=1)
                            jm=j0+int(np.argmin(cnt)); zb=(jm+0.5)/Z; done=True
                            self.info.append(f'no blank row between the last line of the question and the page footer: bottom edge put at y={zb:.1f}, the row with the least ink')
                if not done: self.notes.append(f'bottom zone boundary at {zb:.1f} runs through ink')
        k=max(0,int(round(zt*Z)))
        if zt>0 and rowany[k]:
            j=k
            while j<self.n-1 and rowany[j] and (j-k)<16*Z: j+=1
            if not rowany[j] and not any(zt<=c<=j/Z for c in content): zt=(j+1)/Z
            else: self.notes.append(f'top zone boundary at {zt:.1f} runs through ink')
        self.zt=zt; self.zb=zb
        p[:max(0,int(round(zt*Z)))]=False; p[min(self.n,int(round(zb*Z))):]=False
        self.frac=self.frac.copy(); self.frac[:max(0,int(round(zt*Z)))]=0; self.frac[min(self.n,int(round(zb*Z))):]=0
        for r,c in cls:
            if c=='boiler':
                a_=max(0,int((r['y0']-1)*Z)); b_=min(self.n,int((r['y1']+1)*Z)+1)
                p[a_:b_]=False; self.frac[a_:b_]=0
        self.p=p
    def any(self,ya,yb):
        a=max(0,int(round(ya*Z))); b=min(self.n,int(round(yb*Z)))
        return bool(self.p[a:b].any()) if b>a else False
    def extent(self,ya,yb):
        """first and last inked y inside [ya,yb] (points) or None."""
        a=max(0,int(round(ya*Z))); b=min(self.n,int(round(yb*Z)))
        if b<=a: return None
        idx=np.flatnonzero(self.p[a:b])
        if not len(idx): return None
        return (a+idx[0])/Z,(a+idx[-1]+1)/Z
    def cut_above(self,ytext,floor):
        """y of the cut directly above a block whose first text row starts at ytext.
        floor = bottom of the last text row of the block above (the cut is never placed above it).
        Returns (y, kind): kind 'gap' = middle part of a blank band, 'rule' = on a table rule (no blank band)."""
        floor=max(floor,self.zt)
        k=int(round((ytext-2.0)*Z)); k=max(0,min(self.n-1,k))
        lim=min(self.n-1,int((ytext+10)*Z))
        while k<lim and not self.p[k]: k+=1          # first ink of the block's first row
        j=k-1; kf=int(round(floor*Z))
        if j>=0 and self.p[j]:
            # ink right above the text: table borders. climb to the top of that ink, not above `floor`
            while j>kf and self.p[j]: j-=1
            if self.p[j] and j<=kf:
                # no blank band between the two blocks: cut on the horizontal rule nearest above the text
                seg=self.frac[kf:k]
                if len(seg):
                    m=int(np.argmax(seg[::-1])); rule=k-1-m
                    if self.frac[rule]>0.5: return rule/Z+0.5/Z,'rule'
                return (floor+ytext)/2,'mid'
        top_ink=j+1                                   # first inked row of the block
        g=j
        while g>kf and not self.p[g]: g-=1           # blank band is (g, top_ink)
        band=(top_ink-(g+1))/Z
        y=max(self.zt,top_ink/Z-min(PAD,band/2))
        return y,'gap'

# ---------------------------------------------------------------- block starts
def attach_above(rows,i):
    """index of the first row of the line that row i starts: rows of superscripts (e.g. the nucleon number of a nuclide
    symbol) sit above the baseline row and overlap it; they are part of the same printed line."""
    h=i
    while h>0 and rows[h-1]['y1']>rows[h]['y0']+0.5 and rows[h-1]['y0']>rows[h]['y0']-9: h-=1
    return h
HEAD_QP=re.compile(r'^(Section [AB]\b|Answer (all|two|any|only|both|three|one|either)\b|Write your answers|You are advised)',re.I)
def starts_qp2(doc):
    out=[];expected=1
    for pi in range(1,doc.n):
        page=doc.page(pi); rows=parse_p2.qp_rows(page)
        if not rows: continue
        figs=parse_p2.page_figs(page,rows); lab=set()
        for f in figs:
            for rid in f['label_rows']: lab.add(rid)
        sec=None                                  # index of a 'Section A/B' heading row not yet followed by a question
        for i,r in enumerate(rows):
            if re.match(r'^Section [AB]\b',r['text'].strip()): sec=i
            m=re.match(r'^(\d{1,2})(?=\s|$)',r['text'])
            if m and r['x0']<64 and int(m.group(1))==expected and expected<=14 and id(r) not in lab:
                # the section heading and its instructions ('Answer two questions ...') belong to the question that follows
                h=sec if sec is not None else i
                h=attach_above(rows,h)
                out.append(dict(n=expected,pi=pi,y=r['y0'],htop=min(x['y0'] for x in rows[h:i+1]),floor=rows[h-1]['y1'] if h>0 else 0.0,head=i-h)); expected+=1
                sec=None
    return out
def starts_qp1(doc):
    out=[];expected=1
    for pi in range(1,doc.n):
        rows=parse_p1.clean_rows(doc.page(pi))
        for i,r in enumerate(rows):
            m=re.match(r'^(\d{1,2})(?=\s|$)',r['text'])
            if m and r['x0']<64 and int(m.group(1))==expected and expected<=40:
                h=attach_above(rows,i)
                out.append(dict(n=expected,pi=pi,y=r['y0'],htop=min(x['y0'] for x in rows[h:i+1]),floor=rows[h-1]['y1'] if h>0 else 0.0)); expected+=1
    return out
NOTE_RX=re.compile(r'^\d+\s+(unit|mark|sig)\b',re.I)          # general note such as '1 unit penalty per question', not a question
HDR_RX=re.compile(r'^Question\s+Answer\s+Marks?',re.I)       # header row of a table in the newer schemes
TRAILER=re.compile(r'^(Mark Scheme Code|Total for paper|Total for Paper|Paper total|Notes on (the )?[Mm]ark|Abbreviations used|B1\s+Independent mark|Mark scheme code)',re.I)
def ms_pages(doc,combined):
    raws={pi:doc.rows(pi) for pi in range(doc.n)}
    newfmt=any(HDR_RX.match(r['text'].strip()) for pi in raws for r in raws[pi])
    use=[]
    for pi in range(doc.n):
        if newfmt:
            if any(HDR_RX.match(r['text'].strip()) for r in raws[pi]): use.append(pi)
        elif pi>0: use.append(pi)
    if combined:
        use=[pi for pi in use if re.search(r'5054\s+0?2\b','\n'.join(r['text'] for r in raws[pi][:3]))]
    return use,newfmt
def SEC_MS(t):
    """heading of a section in a Paper 2 mark scheme: 'Section A', 'Section B'; three schemes (May/June 2004, May/June 2014
    variant 1, May/June 2017 variant 2) print 'SECTION B' in capitals. The heading belongs to the question that follows."""
    t=t.strip()
    return bool(re.match(r'^Section [AB]\b',t) or re.fullmatch(r'SECTION [AB]',t))
def starts_ms2(doc,combined):
    use,newfmt=ms_pages(doc,combined)
    out=[];cur=0;trail=[]
    for pi in use:
        page=doc.page(pi); rows=parse_p2.ms_rows(page)
        if not rows: continue
        raw=[r for r in doc.rows(pi) if r['text'].strip()]
        if newfmt:
            lines_=parse_p2.col_bounds(page)
            hq=hm=hg=None
            for r0 in raw:
                if HDR_RX.match(r0['text'].strip()):
                    for sp in r0['spans']:
                        tx=sp['text'].strip()
                        if tx.startswith('Question'): hq=sp
                        elif tx.startswith('Mark'): hm=sp
                        elif tx.startswith('Guidance'): hg=sp
                    break
            if hq and hm:
                c1=[x for x in lines_ if x>hq['x1']-4 and x<hq['x1']+40]
                b1=min(c1) if c1 else hq['x1']+8
            else:
                b1=lines_[1] if len(lines_)>=4 else 122
            hdr_rows=[r0 for r0 in raw if HDR_RX.match(r0['text'].strip())]
            for i,r in enumerate(rows):
                if HDR_RX.match(r['text'].strip()): continue
                labsp=[sp for sp in r['spans'] if sp['x0']+3<b1]
                lab=re.sub(r'\s+',' ',''.join(sp['text'] for sp in labsp)).strip()
                m=re.match(r'^(\d{1,2})\s*(?:[EO]\b)?\s*(?=\(|[a-h]\s*\(|$)',lab.replace('EITHER','E').replace('OR','O'))   # also '4a(i)'
                if m and int(m.group(1))==cur+1 and cur+1<=14:
                    cur+=1
                    htop=r['y0']
                    # the table header row directly above belongs to this question
                    above=[h for h in hdr_rows if h['y1']<=r['y0']+1 and r['y0']-h['y1']<40]
                    prevrows=[x for x in rows[:i] if not HDR_RX.match(x['text'].strip())]
                    floor=prevrows[-1]['y1'] if prevrows else 0.0
                    if above and above[-1]['y0']>=floor-1: htop=above[-1]['y0']
                    if prevrows and SEC_MS(prevrows[-1]['text']) and htop-prevrows[-1]['y1']<40:
                        htop=prevrows[-1]['y0']; floor=prevrows[-2]['y1'] if len(prevrows)>1 else 0.0
                    out.append(dict(n=cur,pi=pi,y=r['y0'],htop=htop,floor=floor))
        else:
            minx=min(r['x0'] for r in rows); sec=None
            for i,r in enumerate(rows):
                t=r['text']
                if SEC_MS(t): sec=i
                m=re.match(r'^(\d{1,2})\s*(?=\(|\s|$)',t)
                if m and r['x0']<minx+16 and int(m.group(1))==cur+1 and cur+1<=14 and not NOTE_RX.match(t.strip()):
                    cur+=1
                    h=sec if sec is not None else i
                    h=attach_above(rows,h)
                    out.append(dict(n=cur,pi=pi,y=r['y0'],htop=min(x['y0'] for x in rows[h:i+1]),floor=rows[h-1]['y1'] if h>0 else 0.0)); sec=None
                elif cur>0 and TRAILER.match(t.strip()):
                    trail.append(dict(n=None,pi=pi,y=r['y0'],htop=r['y0'],floor=rows[i-1]['y1'] if i>0 else 0.0,text=t.strip()[:40]))
    # only a trailer that comes after the last question start ends the last question
    if out and trail:
        last=(out[-1]['pi'],out[-1]['y'])
        tr=[t for t in trail if (t['pi'],t['y'])>last]
        if tr: out.append(tr[0])
    return out,use,newfmt

# ---------------------------------------------------------------- bands
def build_bands(doc,starts,inks,pages,has_content=None):
    """{n: [[pi, ytop, ybot, how_top, how_bottom], …]} in page order. `pages` = page indices that may hold content."""
    res=collections.OrderedDict(); notes=[]
    cuts=[]
    for s in starts:
        ink=inks[s['pi']]
        if not ink.any(ink.zt,s['htop']-1.5):
            cuts.append((ink.zt,'page-top'))
        else:
            y,kind=ink.cut_above(s['htop'],s['floor'])
            cuts.append((y,kind))
    pages=sorted(pages)
    for i,s in enumerate(starts):
        if s['n'] is None: continue
        nxt=starts[i+1] if i+1<len(starts) else None
        bands=[]
        for pi in pages:
            if pi<s['pi']: continue
            if nxt and pi>nxt['pi']: break
            ink=inks[pi]
            ya=cuts[i][0] if pi==s['pi'] else ink.zt
            ha=cuts[i][1] if pi==s['pi'] else 'page-top'
            if nxt and pi==nxt['pi']:
                if cuts[i+1][1]=='page-top': break
                yb=cuts[i+1][0]; hb=cuts[i+1][1]
            else: yb=ink.zb; hb='page-bottom'
            ext=ink.extent(ya,yb)
            if ext is None: continue
            top=max(ya,ext[0]-PAD) if ha!='rule' else ya-0.5
            if ha=='page-top' and getattr(ink,'top_extra',None) is not None and top>ink.top_extra: top=ink.top_extra
            bot=min(yb,ext[1]+PAD) if hb!='rule' else yb+0.5
            bands.append([pi,round(float(top),2),round(float(bot),2),ha,hb])
        # shared lined pages at the end of the older papers (answer space for all Section B questions) carry no text:
        # a trailing band without any text row is not part of the question
        if has_content is not None:
            while bands and not has_content(bands[-1][0],bands[-1][1],bands[-1][2]): bands.pop()
        res[s['n']]=bands
    return res

def words_in(doc,pi,ya,yb):
    return [w for w in doc.page(pi).get_text('words') if (w[1]+w[3])/2>=ya and (w[1]+w[3])/2<=yb]
def band_text(doc,bands):
    out=[]
    for pi,ya,yb,_,_ in bands:
        ws=sorted(words_in(doc,pi,ya,yb),key=lambda w:(round(w[1]),w[0]))
        out.append(' '.join(w[4] for w in ws))
    return '\n'.join(out)

# ---------------------------------------------------------------- Paper 1 answer key rows
def key_rows(doc,pages,key):
    """{n: [pi, x0, y0, x1, y1, letter]} — the row of the official key table for each question."""
    res={}
    for pi in [p-1 for p in pages]:
        page=doc.page(pi); W,H=doc.size(pi)
        ws=page.get_text('words')
        nums=[w for w in ws if re.fullmatch(r'\d{1,2}',w[4]) and 1<=int(w[4])<=40]
        lets=[w for w in ws if w[4] in 'ABCD' and len(w[4])==1]
        a=doc.gray(pi); dark=a<DARK
        newfmt=any(w[4]=='Answer' for w in ws) and any(w[4] in('Marks','Mark') for w in ws)
        for nw in nums:
            n=int(nw[4])
            if n in res: continue
            cy=(nw[1]+nw[3])/2
            cand=[l for l in lets if abs((l[1]+l[3])/2-cy)<3.5 and l[0]>nw[2]-1 and l[0]-nw[2]<(430 if newfmt else 95)]
            if not cand: continue
            l=min(cand,key=lambda l:l[0])
            if l[4]!=key[n-1]: continue
            if newfmt:
                # table row: between the horizontal rules above and below the text; full table width
                frac=dark[:, int(40*Z):int((W-40)*Z)].mean(axis=1)
                k=int(cy*Z); up=k
                while up>0 and frac[up]<0.5: up-=1
                dn=k
                while dn<len(frac)-1 and frac[dn]<0.5: dn+=1
                while up>0 and frac[up-1]>=0.5: up-=1          # include the full thickness of the rule
                while dn<len(frac)-1 and frac[dn+1]>=0.5: dn+=1
                cols=np.flatnonzero(dark[up:dn+1].any(axis=0))
                x0=cols[0]/Z-1.5; x1=(cols[-1]+1)/Z+1.5
                res[n]=[pi,round(x0,2),round(up/Z-0.75,2),round(x1,2),round((dn+1)/Z+0.75,2),l[4]]
            else:
                x0=nw[0]-16; x1=l[2]+16
                col=dark[:, int(x0*Z):int(x1*Z)].any(axis=1)
                ka=int(min(nw[1],l[1])*Z); kb=int(max(nw[3],l[3])*Z)
                idx=np.flatnonzero(col[ka:kb+1])
                ta=ka+idx[0]; tb=ka+idx[-1]                      # ink rows of this line of the key
                up=ta
                while up>0 and ta-up<int(2.5*Z) and not col[up-1]: up-=1
                dn=tb
                while dn<len(col)-1 and dn-tb<int(2.5*Z) and not col[dn+1]: dn+=1
                res[n]=[pi,round(x0,2),round(up/Z,2),round(x1,2),round((dn+1)/Z,2),l[4]]
    return res

# ---------------------------------------------------------------- driver
def run(only=None):
    pairs,excl=list_pairs()
    man2=json.load(open(WORK+'/p2_manifest.json')); keys=json.load(open(WORK+'/keys_p1.json'))
    q1=json.load(open(WORK+'/p1_questions.json'))
    G={};problems=[]
    for p in pairs:
        pid=p['id']
        if only and pid not in only: continue
        qp=Doc(p['qp']); ms=Doc(p['ms'])
        g=dict(pid=pid,paper=p['paper'],qp=p['qp'],ms=p['ms'],combined=p['combined'],qp_pages=qp.n,ms_pages=ms.n,
               qp_size=[list(map(lambda v:round(v,1),qp.size(i))) for i in range(qp.n)],ms_size=[list(map(lambda v:round(v,1),ms.size(i))) for i in range(ms.n)],
               qp_rot=qp.rot,ms_rot=ms.rot,qp_inv=qp.inv,ms_inv=ms.inv)
        if p['paper']==2:
            st=starts_qp2(qp)
            cls={pi:classify_qp(qp,pi,2) for pi in range(1,qp.n)}
            inks={pi:PageInk(qp,pi,cls[pi],(30,qp.size(pi)[0]-30),False) for pi in range(1,qp.n)}
            hc=lambda pi,ya,yb: any(c=='content' and ya<=(r['y0']+r['y1'])/2<=yb for r,c in cls[pi])
            g['q']=build_bands(qp,st,inks,range(1,qp.n),hc)
            g['q_starts']=[[s['n'],s['pi'],round(s['y'],1),round(s['htop'],1)] for s in st]
            for pi,ik in inks.items():
                for nt in ik.notes: problems.append(f'{pid}: QP page {pi+1}: {nt}')
                for nt in ik.info: g.setdefault('info',[]).append(f'QP page {pi+1}: {nt}')
            m=man2[pid]
            if len(st)!=m['nq']: problems.append(f'{pid}: QP starts {len(st)} != manifest {m["nq"]}')
            for s in st:
                if m['qpages'][str(s['n'])][0]!=s['pi']+1: problems.append(f'{pid}: Q{s["n"]} start page {s["pi"]+1} != manifest {m["qpages"][str(s["n"])][0]}')
            mst,use,newfmt=starts_ms2(ms,p['combined'])
            xr=(25,ms.size(use[0])[0]-25)
            minks={pi:PageInk(ms,pi,classify_ms(ms,pi),xr,True) for pi in use}
            g['m']=build_bands(ms,mst,minks,use)
            for pi,ik in minks.items():
                for nt in ik.notes: problems.append(f'{pid}: MS page {pi+1}: {nt}')
                for nt in ik.info: g.setdefault('info',[]).append(f'MS page {pi+1}: {nt}')
            g['m_starts']=[[s['n'],s['pi'],round(s['y'],1),round(s['htop'],1)] for s in mst]
            g['ms_new']=newfmt; g['ms_use']=use
            nms=[s['n'] for s in mst if s['n'] is not None]
            if nms!=[s['n'] for s in st]: problems.append(f'{pid}: MS questions {nms} != QP questions {[s["n"] for s in st]}')
            for n in nms:
                mp=m['mspages'].get(str(n))
                got=sorted(set(b[0]+1 for b in g['m'][n]))
                if mp and got!=sorted(mp):
                    nx=[x for x in mst if x['n']==n+1]
                    if nx and sorted(mp)==got+[nx[0]['pi']+1] and nx[0]['htop']<nx[0]['y']-5: continue     # heading row above the next question
                    problems.append(f'{pid}: MS Q{n} pages {got} != manifest {sorted(mp)}')
        else:
            st=starts_qp1(qp)
            cls={pi:classify_qp(qp,pi,1) for pi in range(1,qp.n)}
            inks={pi:PageInk(qp,pi,cls[pi],(30,qp.size(pi)[0]-30),False) for pi in range(1,qp.n)}
            hc=lambda pi,ya,yb: any(c=='content' and ya<=(r['y0']+r['y1'])/2<=yb for r,c in cls[pi])
            g['q']=build_bands(qp,st,inks,range(1,qp.n),hc)
            g['q_starts']=[[s['n'],s['pi'],round(s['y'],1),round(s['htop'],1)] for s in st]
            for pi,ik in inks.items():
                for nt in ik.notes: problems.append(f'{pid}: QP page {pi+1}: {nt}')
                for nt in ik.info: g.setdefault('info',[]).append(f'QP page {pi+1}: {nt}')
            if len(st)!=40: problems.append(f'{pid}: {len(st)} MCQ starts')
            for s in st:
                if q1[pid][s['n']-1]['page']!=s['pi']+1: problems.append(f'{pid}: Q{s["n"]} page differs from p1_questions')
            kr=key_rows(ms,keys[pid]['pages'],keys[pid]['key'])
            g['k']=kr
            if len(kr)!=40: problems.append(f'{pid}: key rows found {len(kr)} of 40; missing {sorted(set(range(1,41))-set(kr))}')
        G[pid]=g
    return G,problems

if __name__=='__main__':
    only=sys.argv[1:] or None
    G,problems=run(only)
    if not only: json.dump(G,open(OUT+'/geom.json','w'))
    print('pairs',len(G),'| problems',len(problems))
    for x in problems[:60]: print('  ',x)
    nb=sum(len(b) for g in G.values() for b in g['q'].values()); 
    print('QP bands',nb,'| MS bands',sum(len(b) for g in G.values() if 'm' in g for b in g['m'].values()),'| key rows',sum(len(g.get('k',{})) for g in G.values()))
