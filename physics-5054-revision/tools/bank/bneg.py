#!/usr/bin/env python3
"""bneg.py OLD.pdf [NEW.pdf] — compare two builds of the bank, read back from the two PDFs (independent of the build
manifest and of the other checks).

Written for the change from the black-on-white bank (commit f410326) to the white-on-black bank: it shows that the
change of colours and of order touched neither a crop nor a header.
 1 Pictures. Every picture stored in NEW is read back, its grey values are inverted, and the result must be, pixel for
   pixel, a picture stored in OLD. The pictures of OLD without a counterpart in NEW are counted (expected: only the
   strips of the Paper 1 answer key, which NEW shows as text).
 2 Text. The bank adds text to its pages (header, source bars, footer, answer line); the pictures hold none. The text of
   the pages of every record is compared, record by record and page by page, after the record number and the page
   number have been removed (they change with the order). Expected: Paper 2 records identical; Paper 1 records with
   the label 'QUESTION and ANSWER' for 'QUESTION and MARK SCHEME' and the new line 'Answer: X', nothing else.
   The front pages and the title pages are not compared.
 3 Pictures of each record. For every record, the pictures on its pages, page by page and from top to bottom, must be
   the pictures the record had in OLD (inverted), except that a Paper 1 record has lost its last picture, the key row.

  OLD   an earlier build, e.g.
        git show f410326:physics-5054-revision/question_bank/physics_5054_past_paper_questions_with_ms.pdf > old.pdf
  NEW   default: the bank in ../../question_bank/
  --same  the two builds have the same colours and the same Paper 1 layout: pictures and texts must be identical
Exit code 0 if nothing unexpected was found."""
import sys, os, re, hashlib, collections
import fitz, numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
NEW=os.path.normpath(os.path.join(HERE,'..','..','question_bank','physics_5054_past_paper_questions_with_ms.pdf'))
RID=re.compile(r'record (\d[\d.]*\|[sw]\d\d\|P[12]\|V\d\|Q\d+)')
def pictures(doc,invert):
    """{xref: (width, height, sha1 of the grey values)} of every picture object used on a page."""
    seen={}
    for pg in doc:
        for img in pg.get_images(full=True):
            x=img[0]
            if x in seen: continue
            pix=fitz.Pixmap(doc,x)
            if pix.n!=1: pix=fitz.Pixmap(fitz.csGRAY,pix)
            a=np.frombuffer(pix.samples,dtype=np.uint8)
            if invert: a=a^255
            seen[x]=(pix.width,pix.height,hashlib.sha1(a.tobytes()).hexdigest())
    return seen
def texts(doc,pics):
    """{record ID: [lines of page 1, lines of page 2, ...]} without the counters; number of pages without a record;
    {record ID: [picture hashes of page 1 from top to bottom, ...]}."""
    rec=collections.OrderedDict(); other=0; rp=collections.OrderedDict()
    for pg in doc:
        t=pg.get_text(); m=RID.search(t)
        t=re.sub(r'record \d+ of \d+','record # of #',t); t=re.sub(r'Page \d+ of \d+','Page # of #',t)
        if not m: other+=1; continue
        rec.setdefault(m.group(1),[]).append([l.strip() for l in t.split('\n') if l.strip()])
        info=sorted(pg.get_image_info(xrefs=True),key=lambda d:(round(d['bbox'][1],1),round(d['bbox'][0],1)))
        rp.setdefault(m.group(1),[]).append([pics[d['xref']][2] for d in info])
    return rec,other,rp
def main():
    args=[a for a in sys.argv[1:] if not a.startswith('--')]; same='--same' in sys.argv
    if not args: raise SystemExit(__doc__)
    old=args[0]; new=args[1] if len(args)>1 else NEW
    do=fitz.open(old); dn=fitz.open(new)
    sha=lambda p: hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
    # ---- 1 pictures
    o=pictures(do,False); n=pictures(dn,not same)
    oc=collections.Counter(o.values()); nc=collections.Counter(n.values())
    print(f'OLD {os.path.basename(old)} sha256 {sha(old)}: {len(do):,} pages, {len(o):,} picture objects, {len(oc):,} distinct pictures')
    print(f'NEW {os.path.basename(new)} sha256 {sha(new)}: {len(dn):,} pages, {len(n):,} picture objects, {len(nc):,} distinct pictures')
    missing=[k for k in nc if k not in oc]; gone=[k for k in oc if k not in nc]
    what='identical to' if same else 'the exact negative of'
    print(f'1 pictures of NEW that are {what} a picture of OLD: {len(nc)-len(missing):,} of {len(nc):,}; without a counterpart: {len(missing)}'+(f' {missing[:5]}' if missing else ''))
    hs=sorted(k[1] for k in gone)
    print(f'  pictures of OLD without a counterpart in NEW: {len(gone):,} distinct'+(f', {hs[0]} to {hs[-1]} pixels high (median {hs[len(hs)//2]})' if gone else '')+f'; picture objects: {len(o):,} - {len(n):,} = {len(o)-len(n):,}')
    # ---- 2 text of the record pages
    to,xo,po=texts(do,o); tn,xn,pn=texts(dn,n)
    print(f'2 records: OLD {len(to):,}, NEW {len(tn):,}, same record IDs: {set(to)==set(tn)}; pages without a record (front and title pages, not compared): OLD {xo}, NEW {xn}')
    kinds=collections.Counter(); unexpected=[]
    for rid,b in tn.items():
        a=to.get(rid); paper=rid.split('|')[2]
        if a==b: kinds[paper,'identical']+=1; continue
        if a is None: unexpected.append((rid,'not in OLD')); continue
        A=[l for pg in a for l in pg]; B=[l for pg in b for l in pg]
        only_old=[l for l in A if l not in B]; only_new=[l for l in B if l not in A]
        exp=(not same and paper=='P1' and len(a)==len(b) and only_old==['QUESTION and MARK SCHEME'] and len(only_new)==2
             and only_new[0]=='QUESTION and ANSWER' and re.fullmatch(r'Answer: [A-D]',only_new[1]) is not None
             and [l for l in A if l not in only_old]==[l for l in B if l not in only_new])
        if exp: kinds[paper,"'QUESTION and ANSWER' for 'QUESTION and MARK SCHEME', new line 'Answer: X', nothing else"]+=1
        else: unexpected.append((rid,only_old[:4],only_new[:4]))
    for (paper,k),c in sorted(kinds.items()): print(f"  {'Paper 1' if paper=='P1' else 'Paper 2'}: {c:,} records {k}")
    print(f'  records with any other difference: {len(unexpected)}'+(f' {unexpected[:5]}' if unexpected else ''))
    # ---- 3 the pictures of each record
    badp=[]; cnt=collections.Counter()
    for rid,b in pn.items():
        a=po.get(rid); paper=rid.split('|')[2]
        if a is None: badp.append(rid); continue
        if not same and paper=='P1':
            a=[list(x) for x in a]
            if a and a[-1]: a[-1]=a[-1][:-1]          # the key row, the last picture of the record in OLD
        if a==b: cnt[paper]+=1
        else: badp.append(rid)
    print(f"3 records whose pages hold the pictures they held in OLD, in the same order ({'identical' if same else 'inverted; Paper 1 without the key row'}): Paper 1 {cnt['P1']:,}, Paper 2 {cnt['P2']:,}; other: {len(badp)}"+(f' {badp[:5]}' if badp else ''))
    ok=not missing and not unexpected and not badp and set(to)==set(tn)
    print('RESULT:','nothing unexpected' if ok else 'DIFFERENCES FOUND')
    return ok
if __name__=='__main__':
    sys.exit(0 if main() else 1)
