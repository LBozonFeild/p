#!/usr/bin/env python3
"""bdebug.py <pair> qp|ms [zoom] [pages a-b] — pages of a source PDF with the crop bands drawn on them (visual check of the geometry)."""
import sys,os
from bgeom import *
from PIL import Image, ImageDraw
def overlay(pid,kind,z=0.42,prange=None,G=None):
    if G is None:
        G,pr=run([pid])
    g=G[pid]; doc=Doc(g[kind])
    bands=g['q'] if kind=='qp' else (g.get('m') or {})
    ims=[]
    pages=range(doc.n) if kind=='ms' else range(1,doc.n)
    if kind=='ms' and g['paper']==2: pages=g['ms_use']
    for pi in pages:
        if prange and not (prange[0]<=pi+1<=prange[1]): continue
        a=doc.gray(pi,z); im=Image.fromarray(a).convert('RGB'); d=ImageDraw.Draw(im)
        col=[(220,0,0),(0,90,220),(0,150,0),(200,120,0),(150,0,180)]
        for n,bs in bands.items():
            for b in bs:
                if b[0]!=pi: continue
                c=col[int(n)%len(col)]
                d.rectangle([2,b[1]*z,im.width-3,b[2]*z],outline=c,width=2)
                d.text((6,b[1]*z+1),f'Q{n} {b[3]}/{b[4]}',fill=c)
        if kind=='ms' and g['paper']==1:
            for n,k in g['k'].items():
                if k[0]!=pi: continue
                d.rectangle([k[1]*z,k[2]*z,k[3]*z,k[4]*z],outline=(220,0,0),width=1)
        d.text((im.width-70,2),f'p{pi+1}',fill=(0,0,0))
        ims.append(im)
    W=1700; x=y=0; rowh=0; pos=[]
    for im in ims:
        if x+im.width>W and x>0: x=0; y+=rowh+4; rowh=0
        pos.append((x,y)); x+=im.width+4; rowh=max(rowh,im.height)
    sh=Image.new('RGB',(W,y+rowh),(150,150,150))
    for im,(px,py) in zip(ims,pos): sh.paste(im,(px,py))
    return sh
if __name__=='__main__':
    pid,kind=sys.argv[1],sys.argv[2]
    z=float(sys.argv[3]) if len(sys.argv)>3 else 0.42
    pr=tuple(int(v) for v in sys.argv[4].split('-')) if len(sys.argv)>4 else None
    sh=overlay(pid,kind,z,pr)
    fn=f'{OUT}/dbg_{pid}_{kind}.png'; sh.save(fn); print(fn,sh.size)
