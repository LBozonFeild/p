import sys, json, fitz
from lib import SRC, WORK, list_pairs
from render import render_clip, trim, sheet
# usage: p1zoom.py <pid> <q,q,...> [zoom]  -> /home/user/work/view/<pid>_p1.png
pid=sys.argv[1]; qs=[int(x) for x in sys.argv[2].split(',')]
zoom=float(sys.argv[3]) if len(sys.argv)>3 else 2.0
Q=json.load(open(WORK+'/p1_questions.json'))[pid]
lp=list_pairs(); lp=lp[0] if isinstance(lp,tuple) else lp; pair=[p for p in lp if p['id']==pid][0]
doc=fitz.open(SRC+'/'+pair['qp'])
ims=[];labs=[]
for n in qs:
    q=Q[n-1]
    b=q['fbox']; a=q.get('qbox') or b; box=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
    im=trim(render_clip(doc[q['page']-1],box,zoom=zoom))
    ims.append(im);labs.append(f'{pid} Q{n}')
sh=sheet(ims,labs,width=1100,maxh=1900)
out=f'{WORK}/view/{pid}_p1.png'
sh[0].save(out)
print(out, sh[0].size, 'sheets', len(sh))
for i,s in enumerate(sh[1:],2):
    s.save(f'{WORK}/view/{pid}_p1_{i}.png'); print(f'{WORK}/view/{pid}_p1_{i}.png', s.size)
