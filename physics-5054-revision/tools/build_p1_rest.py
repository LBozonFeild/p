# Build "rest" sheets for Paper 1: every figure question NOT on the main (likely in-scope) sheets, so that all 40 MCQs can be checked visually.
from lib import *
from render import *
import fitz
qsall=json.load(open(WORK+'/p1_questions.json'))
pairs,excl=list_pairs()
os.makedirs(WORK+'/sheets/p1rest',exist_ok=True)
man={}
only=sys.argv[1:]
for p in pairs:
    if p['paper']!=1: continue
    if only and p['id'] not in only: continue
    pid=p['id']
    dig=open(f"{WORK}/digest/p1/{pid}.txt").read().split('\n')
    rest=[int(m.group(1)) for l in dig for m in [re.match(r'^Q(\d+)\[F\] ',l)] if m]
    if pid.startswith('s26'): rest=[]   # watermark makes every question look like a figure; handled by hand
    qs=qsall[pid]; doc=fitz.open(os.path.join(SRC,p['qp']))
    ims=[];labs=[]
    for n in rest:
        q=qs[n-1]; b=q['fbox'] or q['qbox']; a=q.get('qbox') or b
        box=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
        try:
            im=trim(render_clip(doc[q['page']-1],box,zoom=1.0)); ims.append(im); labs.append(f"{pid} Q{n}")
        except Exception as e: print('ERR',pid,n,e)
    sh=sheet(ims,labs,width=1100,maxh=1500) if ims else []
    for i,s in enumerate(sh): s.save(f"{WORK}/sheets/p1rest/{pid}_{i+1}.png",optimize=True)
    man[pid]=dict(q=rest,sheets=len(sh),sizes=[s.size for s in sh])
if not only: json.dump(man,open(WORK+'/p1_rest.json','w'))
print(' '.join(f"{k}:{v['sheets']}({len(v['q'])})" for k,v in man.items()))
