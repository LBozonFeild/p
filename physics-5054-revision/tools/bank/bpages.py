#!/usr/bin/env python3
"""bpages.py out.png zoom page[,page…] [crop=y0-y1]  — pages of the finished bank PDF side by side (visual inspection)."""
import sys, fitz
from PIL import Image
PDF='/home/user/p/physics-5054-revision/question_bank/physics_5054_past_paper_questions_with_ms.pdf'
out=sys.argv[1]; z=float(sys.argv[2]); pages=[int(x) for x in sys.argv[3].split(',')]
crop=None
for a in sys.argv[4:]:
    if a.startswith('crop='): crop=[float(v) for v in a[5:].split('-')]
d=fitz.open(PDF); ims=[]
for pn in pages:
    pg=d[pn-1]; clip=None
    if crop: clip=fitz.Rect(0,crop[0],pg.rect.width,crop[1])
    pix=pg.get_pixmap(matrix=fitz.Matrix(z,z),colorspace=fitz.csGRAY,clip=clip)
    ims.append(Image.frombytes('L',(pix.width,pix.height),pix.samples))
W=1750; x=y=0; rowh=0; pos=[]
for im in ims:
    if x+im.width>W and x>0: x=0; y+=rowh+6; rowh=0
    pos.append((x,y)); x+=im.width+6; rowh=max(rowh,im.height)
sh=Image.new('L',(min(W,max(px+im.width for im,(px,py) in zip(ims,pos))),y+rowh),110)
for im,(px,py) in zip(ims,pos): sh.paste(im,(px,py))
sh.save(out); print(out,sh.size)
