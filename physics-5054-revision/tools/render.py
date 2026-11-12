from lib import *
from PIL import Image, ImageDraw, ImageOps
import io
def render_clip(page, box, zoom=1.39):
    if page.rotation: page.remove_rotation()
    clip=fitz.Rect(*box) & page.rect
    pix=page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),clip=clip,alpha=False,colorspace=fitz.csGRAY)
    im=Image.frombytes('L',(pix.width,pix.height),pix.samples)
    # dark-background PDFs (inverted render): fix
    hist=im.histogram()
    dark=sum(hist[:80]); light=sum(hist[176:])
    if dark>light: im=ImageOps.invert(im)
    return im
def trim(im,thr=150,pad=6):
    bw=im.point(lambda p:255 if p<thr else 0)
    bb=bw.getbbox()
    if not bb: return im
    x0,y0,x1,y1=bb
    return im.crop((max(0,x0-pad),max(0,y0-pad),min(im.width,x1+pad),min(im.height,y1+pad)))
def render_page(page, zoom=1.2):
    return render_clip(page,[0,0,page.rect.width,page.rect.height],zoom)
def sheet(images, labels, width=760, maxh=1500, pad=6):
    """pack crops (with labels) into sheets using shelf packing; returns list of PIL images"""
    items=[]
    for im,lab in zip(images,labels):
        if im.width>width:
            im=im.resize((width,int(im.height*width/im.width)))
        tile=Image.new('L',(im.width,im.height+13),255)
        d=ImageDraw.Draw(tile); d.text((2,0),lab,fill=0)
        tile.paste(im,(0,13))
        d.rectangle([0,0,tile.width-1,tile.height-1],outline=160)
        items.append(tile)
    sheets=[];cur=[];x=0;y=0;rowh=0
    def flush():
        nonlocal cur,x,y,rowh
        if not cur: return
        H=y+rowh
        W=max(px+t.width for t,px,py in cur)
        sh=Image.new('L',(W,H),255)
        for t,px,py in cur: sh.paste(t,(px,py))
        sheets.append(sh); cur=[];x=0;y=0;rowh=0
    for t in items:
        if x>0 and x+t.width>width:
            y+=rowh+pad; x=0; rowh=0
        if y>0 and y+t.height>maxh:
            flush()
        if t.height>maxh:
            t=t.resize((int(t.width*maxh/t.height),maxh))
        cur.append((t,x,y)); x+=t.width+pad; rowh=max(rowh,t.height)
    flush()
    return sheets
