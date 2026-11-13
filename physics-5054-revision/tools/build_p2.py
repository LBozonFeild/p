# Build Paper 2 digests + figure crops + MS page flags
from lib import *
from parse_p2 import *
from render import *
pairs,excl=list_pairs()
os.makedirs(WORK+'/digest/p2',exist_ok=True)
allres={}
manifest={}
only=sys.argv[1:] 
for p in pairs:
    if p['paper']!=2: continue
    if only and p['id'] not in only: continue
    qs,figs=parse_qp2(p['qp'])
    ms,newfmt=parse_ms2(p['ms'],p['combined'])
    msd={m['n']:m for m in ms}
    # crops
    cdir=f"{WORK}/crops/p2/{p['id']}"; os.makedirs(cdir,exist_ok=True)
    doc=fitz.open(os.path.join(SRC,p['qp']))
    figsize={}
    seen=set()
    for f in figs:
        if f['id'] in seen: continue
        seen.add(f['id'])
        try:
            im=trim(render_clip(doc[f['page']-1],f['box'],zoom=1.25))
            fn=f"{cdir}/f{f['id'].replace('.','_')}.png"; im.save(fn,optimize=True)
            figsize[f['id']]=(im.width,im.height)
        except Exception as e:
            figsize[f['id']]=(0,0)
    # MS pages with real drawings
    mdoc=fitz.open(os.path.join(SRC,p['ms']))
    msfig=[]
    for pi in range(1,len(mdoc)):
        pg=mdoc[pi]
        if pg.rotation: pg.remove_rotation()
        nnon=0
        try:
            for d in pg.get_drawings():
                R=d['rect']
                if R.y1<60 or R.y0>pg.rect.height-40: continue
                for it in d['items']:
                    if it[0]=='l':
                        p1,p2=it[1],it[2]
                        if abs(p1.x-p2.x)>1 and abs(p1.y-p2.y)>1: nnon+=1
                    elif it[0]=='c': nnon+=1
        except Exception: pass
        nim=sum(1 for im in pg.get_image_info() if im['bbox'][3]-im['bbox'][1]>25 and im['bbox'][1]>60)
        if nnon>=3 or nim: msfig.append(pi+1)
    out=[]
    qt=sum(q['marks'] for q in qs)
    out.append(f"#### P2 {p['id']} ({sess_name(p['sess'])}, comp {p['comp']}) QP={p['qp']} MS={p['ms']}{' [combined MS]' if p['combined'] else ''} | {len(qs)} questions, {sum(len(q['leaves']) for q in qs)} leaf parts, QP marks {qt} | MS pages with drawings: {msfig or '-'}")
    blocks=[]
    for q in qs:
        m=msd.get(q['n'])
        lv=' '.join(f"{l[len(str(q['n'])):] or '-'}={k}" for l,k,c in q['leaves'])
        fg=' '.join(f"{fid}({figsize.get(fid,(0,0))[0]}x{figsize.get(fid,(0,0))[1]})" for fid in q['figs'])
        qtext=re.sub(r'\n\[Total:? ?\d+\]','',q['text'])
        qtext=re.sub(r'\n… (\[\d+\])',r' \1',qtext)
        b=f"━━ Q{q['n']} [QP p{q['pages'][0]}-{q['pages'][-1]} | {q['marks']}m | {lv}{' | figs '+fg if fg else ''}]\n{qtext}\n"
        if m: b+=f"── MS Q{q['n']} [MS p{m['pages'][0]}-{m['pages'][-1]}; codes sum {m['marks']}]\n{m['text']}\n"
        else: b+=f"── MS Q{q['n']} NOT FOUND BY PARSER\n"
        blocks.append(b)
    extra=[m for m in ms if m['n'] not in {q['n'] for q in qs}]
    for m in extra: blocks.append(f"── MS Q{m['n']} (no QP question parsed) [MS p{m['pages']}]\n{m['text']}\n")
    # chunking
    chunks=[];cur=out[0]+'\n'
    LIM=19300
    L=lambda x:len(x.encode('utf8'))
    for b in blocks:
        if L(cur)+L(b)>LIM and L(cur)>200:
            chunks.append(cur); cur=f"#### P2 {p['id']} (cont.)\n"
        while L(cur)+L(b)>LIM:   # very long question: split at line boundary
            lines_=b.split('\n'); acc='';k=0
            while k<len(lines_) and L(cur)+L(acc)+L(lines_[k])+1<LIM-60: acc+=lines_[k]+'\n'; k+=1
            cut=len(acc)-1 if acc else len(lines_[0])
            cur+=b[:cut]+'\n'; chunks.append(cur); cur=f"#### P2 {p['id']} (cont. mid-question)\n"; b=b[cut+1:]
        cur+=b
    chunks.append(cur)
    for i,c in enumerate(chunks):
        open(f"{WORK}/digest/p2/{p['id']}.{i+1}.txt",'w').write(c)
    manifest[p['id']]=dict(chunks=len(chunks),chars=sum(L(c) for c in chunks),nq=len(qs),leaves=[[l,k] for q in qs for l,k,c in q['leaves']],qmarks={q['n']:q['marks'] for q in qs},qtotals={q['n']:q['total'] for q in qs},qpages={q['n']:q['pages'] for q in qs},mspages={m['n']:m['pages'] for m in ms},mscodes={m['n']:m['marks'] for m in ms},figs={f['id']:[f['page'],figsize.get(f['id'])] for f in figs},msfigpages=msfig,newfmt=newfmt)
if not only:
    json.dump(manifest,open(WORK+'/p2_manifest.json','w'))
    import collections
    c=collections.Counter(m['chunks'] for m in manifest.values())
    print('papers',len(manifest),'chunks dist',dict(c),'total chars',sum(m['chars'] for m in manifest.values()),'total chunks',sum(m['chunks'] for m in manifest.values()))
    bad=[k for k,m in manifest.items() if any(q not in m['mspages'] for q in m['qmarks'])]
    print('papers with unmatched questions:',bad)
