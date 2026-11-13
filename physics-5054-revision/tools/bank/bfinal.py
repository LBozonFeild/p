#!/usr/bin/env python3
"""bfinal.py — last check of the deliverables as they are on disk in ../../question_bank/ (run after breports.py).

Nothing is taken from the scratch directory except the build manifest (for the expected page of every record) and the
hash that bverify.py recorded. Every file is reopened from disk.
 F1 the seven files exist; no other file is in the folder
 F2 bank PDF: opens, is not encrypted, has the page count of the manifest, is below 100 MB, hash = the hash bverify.py checked
 F3 bank PDF: bookmarks = 5 + 27 + number of records; every record bookmark points to the page the tracker names
 F4 tracker.txt: field count of every line, unique record IDs, number of INCLUDED lines = number of records of the bank
 F5 tracker.txt against the bank PDF: on the first bank page of every included record, the footer carries its record ID and
    the page text names its question paper file; on the last page it names its mark scheme file
 F6 tracker.txt: bank page ranges of consecutive records neither overlap nor leave a gap (subsection title pages between
    subsections excepted); the last record ends on the last page
 F7 the PDF copies carry the same text as the .txt files (audit, exclusions: all characters in order; tracker: every
    record ID)
 F8 audit: the result line says that everything passed and no line starts with [FAIL]; the counts printed in the audit
    equal the counts of the tracker file and of the PDF
 F9 no page of the report PDFs is blank; all pages have the page number line
 F10 order of the included records, from the fields of the tracker alone: subsections in syllabus order; inside a
     subsection newest first (year descending, October/November before May/June), then variant, paper, question number
 F11 Paper 1 records: the page of the bank carries exactly one text line 'Answer: X', X is the letter the tracker names,
     and the page holds one picture only (the question; the answer is text, not a picture)
 F12 white on black: every 20th page of the bank, all pages of its first and last record and every page of the three
     PDF copies (tracker, exclusions, audit) are rendered at 108 dpi; the corners of the page are black, less than 40 %
     of the page is bright, and there is print (a pixel of grey 160 or more)
 F13 every text the bank and the PDF copies add (bars, headers, answer lines, footers, table cells) is visible: on every
     page of the four PDFs each text span is rendered and must be light print on a dark ground (brightest pixel of the
     span at least 60 grey levels above its background, background below 100 of 255)"""
import sys, os, re, json, hashlib, collections
import fitz
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import breports
QB=breports.QB; BANK=breports.BANK; STEM=breports.STEM; OUT=breports.OUT
res=[]
def chk(name,ok,detail):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name+' | '+detail)
def squeeze(t): return re.sub(r'\s+','',t)
def invisible(pg,z=2.0):
    """text spans of the page that are not light print on a dark ground in the rendering -> (bad spans, spans checked,
    lowest contrast). Spans without a letter or digit (bullets, dashes) are skipped."""
    import numpy as np
    pix=pg.get_pixmap(matrix=fitz.Matrix(z,z),colorspace=fitz.csGRAY,alpha=False)
    a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width); bad=[]; n=0; lo=255
    for b in pg.get_text('dict')['blocks']:
        if b.get('type')!=0: continue
        for l in b['lines']:
            for sp in l['spans']:
                t=sp['text']
                if not any(c.isalnum() for c in t): continue
                x0,y0,x1,y1=sp['bbox']; r=a[max(0,int(y0*z)):int(y1*z)+1,max(0,int(x0*z)):int(x1*z)+1]
                n+=1
                if r.size==0: bad.append((t[:30],'outside the page')); continue
                med=int(np.median(r)); mx=int(r.max()); lo=min(lo,mx-med)
                if med>100 or mx-med<60: bad.append((t[:30],med,mx))
    return bad,n,lo
def page_colours(pg,z=1.5):
    """(share of bright pixels, list of what is wrong) of a page that should be white on black.
    Rendered at 108 dpi: at half size the thin strokes of the typewriter font of the audit and exclusions PDFs do not
    reach grey 160, and a page of print would be taken for a page without print."""
    import numpy as np
    pix=pg.get_pixmap(matrix=fitz.Matrix(z,z),colorspace=fitz.csGRAY,alpha=False)
    a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width)
    corners=[a[1:7,1:7],a[1:7,-7:-1],a[-7:-1,1:7],a[-7:-1,-7:-1]]
    bright=float((a>128).mean()); why=[]
    if bright>0.40: why.append('light page')
    if any(int(c.max())>80 for c in corners): why.append('corner not black')
    if int(a.max())<160: why.append('no print')
    return bright,why
def main():
    files=[BANK]+[STEM+k+e for k in ('tracker','exclusions','audit') for e in ('.txt','.pdf')]
    have=sorted(os.listdir(QB))
    chk('F1 files',sorted(files)==have,f'{len(have)} files: '+', '.join(f'{f} ({os.path.getsize(os.path.join(QB,f)):,} bytes)' for f in have))
    M=json.load(open(OUT+'/manifest.json')); V=json.load(open(OUT+'/verify.json'))
    pdf=os.path.join(QB,BANK); doc=fitz.open(pdf); N=len(doc); size=os.path.getsize(pdf)
    sha=hashlib.sha256(open(pdf,'rb').read()).hexdigest()
    chk('F2 bank PDF',N==M['n_pages'] and not doc.is_encrypted and size<100*1024*1024 and sha==V['info'].get('pdf_sha256') and V.get('ok'),
        f"{N:,} pages, {size:,} bytes ({size/1048576:.1f} MiB), sha256 {sha[:16]}... {'= hash checked by bverify.py, which passed' if sha==V['info'].get('pdf_sha256') and V.get('ok') else 'NOT the file that passed bverify.py'}")
    # ---- tracker.txt
    lines=open(os.path.join(QB,STEM+'tracker.txt'),encoding='utf-8').read().split('\n')
    rows=[l.split('\t') for l in lines if l and not l.startswith('#') and not l.startswith('record_id')]
    nf=len(breports.FIELDS); badf=[r for r in rows if len(r)!=nf]
    hdr=[l for l in lines if l.startswith('record_id')]
    inc=[r for r in rows if r[-1]=='INCLUDED']; exc=[r for r in rows if r[-1].startswith('EXCLUDED')]
    ids=[r[0] for r in rows]
    chk('F4 tracker.txt structure',not badf and len(set(ids))==len(ids) and len(inc)==M['n_entries'] and len(inc)+len(exc)==len(rows) and all(h.split('\t')==[n for n,_ in breports.FIELDS] for h in hdr),
        f'{len(rows):,} rows of {nf} fields: {len(inc):,} INCLUDED, {len(exc):,} EXCLUDED; {len(set(ids)):,} distinct record IDs; {len(hdr)} header lines')
    # ---- bookmarks
    toc=doc.get_toc(); l3=[t for t in toc if t[0]==3]; l2=[t for t in toc if t[0]==2]; l1=[t for t in toc if t[0]==1]
    first={r[0]:int(r[1].split('-')[0]) for r in inc}; last={r[0]:int(r[1].split('-')[-1]) for r in inc}
    okb=len(l1)==5 and len(l2)==27 and len(l3)==len(inc) and [t[2] for t in l3]==[first[r[0]] for r in inc]
    chk('F3 bookmarks',okb,f'{len(l1)} + {len(l2)} + {len(l3):,} bookmarks; record bookmarks in tracker order, each on the first page the tracker names: {okb}')
    # ---- tracker against the PDF
    bad=[]
    for r in inc:
        rid=r[0]; t1=doc[first[rid]-1].get_text(); t2=doc[last[rid]-1].get_text()
        rx=re.compile(re.escape('record '+rid)+r'(?!\d)')
        if not rx.search(t1) or r[10] not in t1 or r[12] not in t2 or f'Page {first[rid]} of {N}' not in t1: bad.append(rid)
        if not rx.search(t2): bad.append(rid)
    chk('F5 tracker.txt against the pages of the bank',not bad,f'{len(inc):,} records: record ID and question paper file on the first page, record ID and mark scheme file on the last page; {len(bad)} wrong'+(f' {bad[:5]}' if bad else ''))
    gaps=[]; prev=None
    for r in inc:
        a,b=first[r[0]],last[r[0]]
        if prev is not None and a!=prev+1:
            # a subsection title page may lie between two records
            if not (a==prev+2 and 'Each entry: the whole question' in doc[prev].get_text()): gaps.append((r[0],prev,a))
        if b<a: gaps.append((r[0],a,b))
        prev=b
    chk('F6 bank page ranges',not gaps and prev==N and first[inc[0][0]]==4,f'first record on page {first[inc[0][0]]}, last record ends on page {prev} of {N}; {len(gaps)} gaps or overlaps')
    # ---- order of the records, from the tracker fields alone (record_id, bank_pages, year, session, paper, variant, question, chapter, subsection, ...)
    subs=[]
    for r in inc:
        if r[8] not in subs: subs.append(r[8])
    num=lambda sub: tuple(int(x) for x in sub.split()[0].split('.'))
    SESS={'October/November':0,'May/June':1}
    keys=[(subs.index(r[8]),-int(r[2]),SESS[r[3]],int(r[5]),int(r[4]),int(r[6])) for r in inc]
    oko=all(a<b for a,b in zip(keys,keys[1:])) and [num(x) for x in subs]==sorted(num(x) for x in subs)
    years=[int(r[2]) for r in inc if r[8]==subs[0]]
    chk('F10 order of the records',oko,f"{len(subs)} subsections in syllabus order; inside each, newest first (year descending, October/November before May/June), then variant, paper, question number: {'yes' if oko else 'NO'}; first record {inc[0][0]}, last record {inc[-1][0]}; years of the first subsection run from {years[0]} to {years[-1]}")
    # ---- answers of Paper 1: text on the page = letter named in the tracker; one picture on the page
    bada=[]; na=0; letters=collections.Counter()
    for r in inc:
        if r[4]!='1': continue
        na+=1
        m=re.search(r'shown as text: Answer ([A-D])$',r[13]); pg=doc[last[r[0]]-1]
        found=re.findall(r'^Answer: ([A-D])$',pg.get_text(),re.M)
        if not m or found!=[m.group(1)] or first[r[0]]!=last[r[0]] or len(pg.get_images())!=1: bada.append((r[0],found,len(pg.get_images())))
        else: letters[found[0]]+=1
    chk('F11 answers of Paper 1 as text',not bada and na>0,f"{na:,} Paper 1 records: one line 'Answer: X' on the page, X = the letter in the tracker, one picture on the page (the question); {len(bada)} wrong"+(f' {bada[:5]}' if bada else '')+f"; letters {dict(sorted(letters.items()))}")
    # ---- white on black
    import numpy as np
    sample=sorted(set(list(range(0,N,20))+[N-1]+list(range(first[inc[0][0]]-1,last[inc[0][0]]))+list(range(first[inc[-1][0]]-1,last[inc[-1][0]]))))
    badc=[]; mx=0.0; nrep=0
    def darkpage(d,i,tag):
        nonlocal mx
        bright,why=page_colours(d[i]); mx=max(mx,bright)
        if why: badc.append((tag,i+1,round(bright,3),'/'.join(why)))
    for i in sample: darkpage(doc,i,'bank')
    for k in ('tracker','exclusions','audit'):
        d=fitz.open(os.path.join(QB,STEM+k+'.pdf'))
        for i in range(len(d)): darkpage(d,i,k); nrep+=1
    chk('F12 white on black',not badc,f"{len(sample)} pages of the bank and all {nrep} pages of the tracker, exclusions and audit PDFs rendered at 108 dpi: corners black, white print present and less than 40 % bright on every one (brightest {mx*100:.0f} %); {len(badc)} pages fail"+(f' {badc[:8]}' if badc else ''))
    # ---- PDF copies
    det=[];ok7=True;ok9=True;np_={}
    for k in ('audit','exclusions'):
        txt=open(os.path.join(QB,STEM+k+'.txt'),encoding='utf-8').read()
        d=fitz.open(os.path.join(QB,STEM+k+'.pdf')); np_[k]=len(d); body=[]
        title=f'Physics 5054 question bank - {k}'
        for i,pg in enumerate(d):
            t=pg.get_text()
            for foot in (f'Page {i+1} of {len(d)}',title):       # the footer line of the page: last occurrence only
                j=t.rfind(foot)
                if j<0: ok9=False
                else: t=t[:j]+t[j+len(foot):]
            if len(t.strip())<40: ok9=False
            body.append(t)
        got=squeeze(''.join(body))
        want=squeeze(breports.san(txt))
        same=got==want; ok7=ok7 and same
        det.append(f"{k}: {len(d)} pages, {len(want):,} characters {'identical' if same else 'DIFFERENT'}")
        if not same:
            j=next((i for i,(x,y) in enumerate(zip(got,want)) if x!=y),min(len(got),len(want)))
            det.append(f'   first difference at character {j}: pdf "{got[max(0,j-30):j+30]}" txt "{want[max(0,j-30):j+30]}"')
    d=fitz.open(os.path.join(QB,STEM+'tracker.pdf')); np_['tracker']=len(d); tt=[]; n_inc=0
    for i,pg in enumerate(d):
        t=pg.get_text()
        if f'Page {i+1} of {len(d)}' not in t or len(t.strip())<40: ok9=False
        # a status cell of an included record is a text line that reads INCLUDED and nothing else (the introduction on
        # page 1 uses the word inside a sentence)
        n_inc+=sum(1 for l in t.split('\n') if l.strip()=='INCLUDED')
        tt.append(t)
    tt=squeeze(''.join(tt)); miss=[i for i in ids if squeeze(breports.san(i)) not in tt]
    ok7=ok7 and not miss and n_inc==len(inc)
    det.append(f"tracker: {len(d)} pages, {len(ids)-len(miss):,} of {len(ids):,} record IDs found, {n_inc:,} cells 'INCLUDED'")
    chk('F7 PDF copies carry the text of the .txt files',ok7,'; '.join(det))
    chk('F9 report PDFs: no blank page, page number line on every page',ok9,', '.join(f'{k} {v} pages' for k,v in np_.items()))
    # ---- audit
    a=open(os.path.join(QB,STEM+'audit.txt'),encoding='utf-8').read()
    fails=[l for l in a.split('\n') if l.startswith('[FAIL]')]; passes=[l for l in a.split('\n') if l.startswith('[PASS]')]
    m1=re.search(r'records \(one question in one subsection\)\s+([\d,]+)',a); m2=re.search(r'\n  pages\s+([\d,]+)',a); m3=re.search(r'sha256 of the bank PDF: (\w+)',a)
    okc=bool(m1 and m2 and m3) and int(m1.group(1).replace(',',''))==len(inc) and int(m2.group(1).replace(',',''))==N and m3.group(1)==sha
    chk('F8 audit',not fails and 'RESULT: ALL AUTOMATED CHECKS PASSED' in a and okc and len(passes)>=30,
        f"{len(passes)} lines [PASS], {len(fails)} lines [FAIL]; records {m1.group(1) if m1 else '?'}, pages {m2.group(1) if m2 else '?'}, hash {'equal' if m3 and m3.group(1)==sha else 'DIFFERENT'}")
    # ---- every text span visible (all pages of the four PDFs)
    badv=[]; nsp=0; lo=255; npg=0; ans_seen=0
    for tag,dd in [('bank',doc)]+[(k,fitz.open(os.path.join(QB,STEM+k+'.pdf'))) for k in ('tracker','exclusions','audit')]:
        for i in range(len(dd)):
            bad,n,l=invisible(dd[i]); nsp+=n; lo=min(lo,l); npg+=1
            if n==0: badv.append((tag,i+1,'no text span'))
            if bad: badv.append((tag,i+1,bad[:3]))
    chk('F13 every added text is visible',not badv and nsp>0,f"{npg:,} pages of the four PDFs rendered, {nsp:,} text spans: each is light print on a dark ground (lowest contrast {lo} of 255 grey levels); {len(badv)} pages with an invisible or dark text"+(f' {badv[:5]}' if badv else ''))
    print('RESULT:','all passed' if all(res) else 'FAILED')
    return all(res)
if __name__=='__main__':
    sys.exit(0 if main() else 1)
