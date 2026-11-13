#!/usr/bin/env python3
"""bdebug2.py out.png zoom pair:kind:page …  — single pages with the stored geometry (geom.json) drawn on them."""
import sys
from bgeom import *
from PIL import Image, ImageDraw
G=json.load(open(OUT+'/geom.json'))
out=sys.argv[1]; z=float(sys.argv[2]); ims=[]
for a in sys.argv[3:]:
    pid,kind,pn=a.split(':'); pi=int(pn)-1; g=G[pid]; doc=Doc(g[kind])
    bands=g['q'] if kind=='qp' else g.get('m',{})
    im=Image.fromarray(doc.gray(pi,z)).convert('RGB'); d=ImageDraw.Draw(im)
    col=[(220,0,0),(0,90,220),(0,150,0),(200,120,0),(150,0,180)]
    for n,bs in bands.items():
        for b in bs:
            if b[0]!=pi: continue
            c=col[int(n)%len(col)]
            d.rectangle([1,b[1]*z,im.width-2,b[2]*z],outline=c,width=1)
            d.text((4,b[1]*z+1),f'Q{n} {b[3]}/{b[4]}',fill=c)
    if kind=='ms' and g['paper']==1:
        for n,k in g['k'].items():
            if k[0]==pi: d.rectangle([k[1]*z,k[2]*z,k[3]*z,k[4]*z],outline=col[int(n)%5],width=1)
    d.text((im.width-150,2),f'{pid} {kind} p{pn}',fill=(0,0,0))
    ims.append(im)
W=1700; x=y=0; rowh=0; pos=[]
for im in ims:
    if x+im.width>W and x>0: x=0; y+=rowh+4; rowh=0
    pos.append((x,y)); x+=im.width+4; rowh=max(rowh,im.height)
sh=Image.new('RGB',(W,y+rowh),(150,150,150))
for im,(px,py) in zip(ims,pos): sh.paste(im,(px,py))
sh.save(out); print(out,sh.size)
