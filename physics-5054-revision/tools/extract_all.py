import fitz, os, re, sys, json
SRC='/home/user/p/physics-5054'
OUT='/home/user/work/txt'
rows=[]
for fn in sorted(os.listdir(SRC)):
    m=re.match(r'5054_([sw]\d\d)_(qp|ms)(?:_(.+))?\.pdf$',fn)
    if not m: continue
    sess,kind,comp=m.group(1),m.group(2),m.group(3) or ''
    # only paper 1/2 (and combined ms)
    if comp and not comp[0] in '12': continue
    path=os.path.join(SRC,fn)
    try:
        doc=fitz.open(path)
    except Exception as e:
        rows.append(dict(fn=fn,error=str(e))); continue
    texts=[]; nimg=0; chars=[]
    for pg in doc:
        t=pg.get_text('text')
        texts.append(t); chars.append(len(t.strip()))
        nimg+=len(pg.get_images(full=True))
    with open(os.path.join(OUT,fn[:-4]+'.txt'),'w') as f:
        for i,t in enumerate(texts):
            f.write(f'\n=====PAGE {i+1}=====\n'); f.write(t)
    rows.append(dict(fn=fn,sess=sess,kind=kind,comp=comp,pages=len(doc),chars=sum(chars),minpage=min(chars) if chars else 0,emptypages=sum(1 for c in chars if c<50),nimg=nimg,size=os.path.getsize(path)))
json.dump(rows,open('/home/user/work/inventory_raw.json','w'),indent=1)
for r in rows:
    if 'error' in r: print('ERROR',r); continue
    print(f"{r['fn']:32s} pages={r['pages']:3d} chars={r['chars']:7d} emptypages={r['emptypages']:2d} imgs={r['nimg']:3d} size={r['size']//1024}k")
