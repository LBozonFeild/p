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
 F9 no page of the report PDFs is blank; all pages have the page number line"""
import sys, os, re, json, hashlib, collections
import fitz
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import breports
QB=breports.QB; BANK=breports.BANK; STEM=breports.STEM; OUT=breports.OUT
res=[]
def chk(name,ok,detail):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name+' | '+detail)
def squeeze(t): return re.sub(r'\s+','',t)
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
    print('RESULT:','all passed' if all(res) else 'FAILED')
    return all(res)
if __name__=='__main__':
    sys.exit(0 if main() else 1)
