from lib import *
pairs,excl=list_pairs()
def hdr(fn,maxpages=2):
    doc=fitz.open(os.path.join(SRC,fn))
    t=''
    for i in range(min(maxpages,len(doc))):
        t+='\n'.join(r['text'] for r in page_rows(doc[i]))+'\n'
    comps=set(re.findall(r'5054\s*/\s*0?(\d{1,2})\b',t))
    sess=re.findall(r'(May/June|October/November|JUNE|NOVEMBER|June|November)\s+(20\d\d)',t)
    return comps,set((('s' if a.lower().startswith(('may','june')) else 'w')+b[2:]) for a,b in sess),len(doc)
out={}
issues=[]
for p in pairs:
    qc,qs,qn=hdr(p['qp'])
    mc,ms,mn=hdr(p['ms'],maxpages=4 if p['combined'] else 2)
    comp=p['comp'].lstrip('0')
    ok_q=(comp in qc) and (p['sess'] in qs)
    ok_m=(comp in mc or (p['combined'])) and (p['sess'] in ms)
    out[p['id']]=dict(qp_comp=sorted(qc),qp_sess=sorted(qs),ms_comp=sorted(mc),ms_sess=sorted(ms),qp_pages=qn,ms_pages=mn,ok=ok_q and ok_m)
    if not (ok_q and ok_m): issues.append((p['id'],sorted(qc),sorted(qs),sorted(mc),sorted(ms)))
json.dump(out,open(WORK+'/header_check.json','w'),indent=0)
print('pairs',len(pairs),'header issues',len(issues))
for i in issues: print(i)
