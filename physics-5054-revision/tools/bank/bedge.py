#!/usr/bin/env python3
"""bedge.py out.png page:top|bottom[:item] …  — the cut edge of a picture of the bank, next to the same place of the SOURCE page.
For each argument two strips are drawn: first the bank page (30 pt on each side of the edge of the picture), below it the
source page 30 pt on each side of the cut (the cut is marked by ticks in the margins). Shows whether a cut passes through ink."""
import sys, json
import numpy as np
from PIL import Image, ImageDraw
from bgeom import *
PDF='/home/user/p/physics-5054-revision/question_bank/physics_5054_past_paper_questions_with_ms.pdf'
M=json.load(open(OUT+'/manifest.json')); P=M['pages']; bank=fitz.open(PDF)
Zv=2.6; strips=[]
for a in sys.argv[2:]:
    f=a.split(':'); pn=int(f[0]); side=f[1]; p=P[pn-1]
    its=p['items']
    if len(f)>2: it=its[int(f[2])]
    else: it=its[0] if side=='top' else its[-1]
    fn,spi,x0,y0,x1,y1=it['spec']; r=it['rect']; s=it['scale']
    ye=r[1] if side=='top' else r[3]; ys=y0 if side=='top' else y1
    pg=bank[pn-1]
    pix=pg.get_pixmap(matrix=fitz.Matrix(Zv,Zv),colorspace=fitz.csGRAY,clip=fitz.Rect(0,ye-30,pg.rect.width,ye+30))
    A=Image.frombytes('L',(pix.width,pix.height),pix.samples)
    d=Doc(fn); W,H=d.size(spi)
    c0=max(0,ys-30/s); c1=min(H,ys+30/s)
    B=Image.fromarray(d.gray(spi,Zv*s,clip=(0,c0,W,c1)))
    dr=ImageDraw.Draw(B); yy=int((ys-c0)*Zv*s)
    dr.line((0,yy,14,yy),fill=0,width=1); dr.line((B.width-14,yy,B.width,yy),fill=0,width=1)
    lab=Image.new('L',(A.width,14),255); ImageDraw.Draw(lab).text((3,1),f'bank page {pn} {side} edge (first strip)   |   {fn} source page {spi+1}, cut at y={ys} (second strip, ticks in the margins)',fill=0)
    strips+=[lab,A,B]
Wd=max(s.width for s in strips); sh=Image.new('L',(Wd,sum(s.height+3 for s in strips)),110); y=0
for s in strips: sh.paste(s,(0,y)); y+=s.height+3
if sh.width>1900: sh=sh.resize((1900,int(sh.height*1900/sh.width)),Image.LANCZOS)
sh.save(sys.argv[1]); print(sys.argv[1],sh.size)
