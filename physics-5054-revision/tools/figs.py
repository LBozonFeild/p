# usage: figs.py <pid> <figid|msN|qpN> ...   -> /home/user/work/view/<pid>.png (one packed sheet; more sheets get _2 ...)
from lib import *
from render import *
from PIL import Image
pid=sys.argv[1]; args=sys.argv[2:]
pairs,_=list_pairs(); P={p['id']:p for p in pairs}[pid]
ims=[];labs=[]
for a in args:
    if a.startswith('ms') or a.startswith('qp'):
        doc=fitz.open(os.path.join(SRC,P['ms' if a.startswith('ms') else 'qp']))
        spec=a[2:]; half=None
        if spec[-1] in 'tb': half=spec[-1]; spec=spec[:-1]
        pg=doc[int(spec)-1]
        if pg.rotation: pg.remove_rotation()
        box=[0,30,pg.rect.width,pg.rect.height-30]
        if half=='t': box[3]=pg.rect.height/2+10
        if half=='b': box[1]=pg.rect.height/2-10
        im=trim(render_clip(pg,box,zoom=1.15))
    else:
        fn=f"{WORK}/crops/p2/{pid}/f{a.replace('.','_')}.png"
        im=Image.open(fn).convert('L')
    ims.append(im); labs.append(f"{pid} {a}")
os.makedirs(WORK+'/view',exist_ok=True)
sh=sheet(ims,labs,width=1000,maxh=1500)
for i,s in enumerate(sh):
    fn=f"{WORK}/view/{pid}{'' if i==0 else '_'+str(i+1)}.png"; s.save(fn); print(fn,s.size)
