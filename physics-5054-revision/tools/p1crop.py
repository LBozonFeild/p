import sys, json, fitz
from lib import SRC, WORK, list_pairs
from render import render_clip, trim
# usage: p1crop.py <pid> <q> <x0frac> <y0frac> <x1frac> <y1frac> [zoom] -> /home/user/work/view/<pid>_crop.png  (fractions of the question box)
pid=sys.argv[1]; n=int(sys.argv[2]); fx0,fy0,fx1,fy1=[float(x) for x in sys.argv[3:7]]
zoom=float(sys.argv[7]) if len(sys.argv)>7 else 4.0
Q=json.load(open(WORK+'/p1_questions.json'))[pid]
lp=list_pairs(); lp=lp[0] if isinstance(lp,tuple) else lp
pair=[p for p in lp if p['id']==pid][0]
doc=fitz.open(SRC+'/'+pair['qp'])
q=Q[n-1]; b=q['fbox']; a=q.get('qbox') or b
box=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
w=box[2]-box[0]; h=box[3]-box[1]
clip=[box[0]+fx0*w, box[1]+fy0*h, box[0]+fx1*w, box[1]+fy1*h]
im=render_clip(doc[q['page']-1],clip,zoom=zoom)
out=f'{WORK}/view/{pid}_crop.png'; im.save(out); print(out, im.size)
