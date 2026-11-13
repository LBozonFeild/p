from lib import *
def parse_key(msfile, combined=False):
    doc=fitz.open(os.path.join(SRC,msfile))
    key={}; pages_used=[]; hdr=''
    for pi,page in enumerate(doc):
        rows=page_rows(page)
        txt='\n'.join(r['text'] for r in rows)
        if pi==0: hdr=txt
        if combined:
            # only the page(s) of Paper 1 in combined scheme: detect page with many (num letter) pairs
            pass
        found={}
        for r in rows:
            for m in re.finditer(r'(?<![\d.])(\d{1,2})\s+([ABCD])(?![A-Za-z])',r['text']):
                n=int(m.group(1))
                if 1<=n<=40: found.setdefault(n,m.group(2))
        if len(found)>=10:
            pages_used.append(pi+1)
            for n,l in found.items(): key.setdefault(n,l)
    return key,pages_used,hdr
if __name__=='__main__':
    pairs,excl=list_pairs()
    out={}
    bad=0
    for p in pairs:
        if p['paper']!=1: continue
        key,pages,hdr=parse_key(p['ms'],p['combined'])
        ok=len(key)==40
        out[p['id']]=dict(key=''.join(key.get(i,'?') for i in range(1,41)),pages=pages)
        if not ok:
            bad+=1; print('BAD',p['id'],len(key),sorted(set(range(1,41))-set(key)))
    json.dump(out,open(WORK+'/keys_p1.json','w'),indent=0)
    print('parsed',len(out),'bad',bad)
    for k in list(out)[:3]+list(out)[-3:]: print(k,out[k])
