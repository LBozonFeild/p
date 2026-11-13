#!/usr/bin/env python3
"""bview.py out.png zoom file:page[:y0-y1] …  — source pages (colour inversion undone, rotation removed) side by side; optional y-range crop."""
import sys
from bgeom import *
from PIL import Image, ImageDraw
out=sys.argv[1]; z=float(sys.argv[2]); ims=[]
for a in sys.argv[3:]:
    parts=a.split(':'); fn=parts[0]; pn=int(parts[1]); d=Doc(fn)
    W,H=d.size(pn-1); clip=None
    if len(parts)>2:
        y0,y1=[float(v) for v in parts[2].split('-')]; clip=(0,y0,W,y1)
    im=Image.fromarray(d.gray(pn-1,z,clip)).convert('L')
    ImageDraw.Draw(im).text((3,1),f'{fn} p{pn} {parts[2] if len(parts)>2 else ""}',fill=120)
    ims.append(im)
W=1700; x=y=0; rowh=0; pos=[]
for im in ims:
    if x+im.width>W and x>0: x=0; y+=rowh+6; rowh=0
    pos.append((x,y)); x+=im.width+6; rowh=max(rowh,im.height)
sh=Image.new('L',(W,y+rowh),150)
for im,(px,py) in zip(ims,pos): sh.paste(im,(px,py))
sh.save(out); print(out,sh.size)
