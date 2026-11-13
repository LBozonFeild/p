import warnings; warnings.filterwarnings('ignore')
import fitz, re, os, json, sys
SRC='/home/user/p/physics-5054'
WORK='/home/user/work'
SYM={0xb4:'×',0xb7:'•',0xb0:'°',0xae:'→',0x57:'Ω',0x44:'Δ',0x6c:'λ',0x71:'θ',0x6d:'μ',0x72:'ρ',0xb1:'±',0xb8:'÷',0xa3:'≤',0xb3:'≥',0xb5:'∝',0xbb:'≈',0xd6:'√',0x70:'π',0x61:'α',0x62:'β',0x67:'γ',0x2d:'−',0xac:'←',0xad:'↑',0xaf:'↓',0xde:'⇒',0x3d:'=',0x2b:'+',0xa2:"′",0xb2:'″',0xb9:'≠',0xba:'≡',0xa5:'∞',0x5c:'∴',0x7e:'~',0x66:'φ',0x77:'ω',0x73:'σ',0x74:'τ',0x65:'ε',0x68:'η',0x6b:'κ',0x6e:'ν',0x64:'δ',0x53:'Σ',0x46:'Φ',0x4c:'Λ',0x51:'Θ',0x50:'Π',0xd7:'·',0xbc:'…',0xbe:'—',0x20:' ',0xa0:' ',0xab:'↔',0xdb:'⇔',0xdc:'⇐',0xe0:'◊',0xd0:'∠',0x40:'≅',0x5e:'⊥',0xbd:'|',0x2f:'/',0x28:'(',0x29:')',0x25:'%',0x2a:'*',0x3c:'<',0x3e:'>',0x2c:',',0x2e:'.',0x30:'0',0x31:'1',0x32:'2',0x33:'3',0x34:'4',0x35:'5',0x36:'6',0x37:'7',0x38:'8',0x39:'9',0x56:'ς',0x76:'ϖ',0x6a:'ϕ',0x4a:'ϑ',0x63:'χ',0x79:'ψ',0x78:'ξ',0x7a:'ζ',0x69:'ι',0x6f:'ο',0x75:'υ',0x47:'Γ',0x59:'Ψ',0x58:'Ξ',0x55:'Υ',0x41:'Α',0x42:'Β',0x45:'Ε',0x5a:'Ζ',0x48:'Η',0x49:'Ι',0x4b:'Κ',0x4d:'Μ',0x4e:'Ν',0x4f:'Ο',0x52:'Ρ',0x54:'Τ',0x43:'Χ',0xb6:'∂',0xc5:'⊕',0xc4:'⊗',0xa7:'♣',0xb7:'•'}
WING={0xfc:'✓',0xfb:'✗',0xfe:'☑',0xa8:'□',0x6f:'□',0x71:'□',0xe0:'→',0xdf:'←',0xe1:'↑',0xe2:'↓',0x6c:'●',0x6e:'■',0xa7:'▪',0x77:'◆',0x9f:'•',0xf0:'⇨',0xd8:'➢'}
def fix(t,font=''):
    out=[]
    for c in t:
        o=ord(c)
        if 0xF000<=o<=0xF0FF:
            k=o-0xF000
            if 'ingding' in font: out.append(WING.get(k,'¤'))
            else: out.append(SYM.get(k,'¤'))
        elif o<32 and c not in '\t\n': continue
        elif o in (0x2009,0x200a,0x2002,0x2003,0xa0,0x202f,0x2008,0x2005,0x2006,0x2004): out.append(' ')
        else: out.append(c)
    return ''.join(out)
GARB=set('ÕõÅąĕĥĊĬĂåĪíÏĠÈüúþĀûùÛĄàÙÞÝôßéÚĩēçĆöĒÎěĢ')
def is_garbage(t):
    t=t.strip()
    if not t: return True
    n=sum(1 for c in t if c in GARB)
    return n>=3 and n>0.3*len(t)
def page_rows(page, keep_rot=False):
    """Return visual rows: list of dict(y0,y1,x0,x1,size,text,spans) sorted top->bottom."""
    if page.rotation:
        page.remove_rotation()
    d=page.get_text('dict')
    spans=[]
    for b in d['blocks']:
        if b['type']!=0: continue
        for l in b['lines']:
            dx,dy=l['dir']
            if abs(dx-1)>0.02 and not keep_rot: continue
            for s in l['spans']:
                t=fix(s['text'],s['font'])
                if not t.strip(): continue
                if is_garbage(t): continue
                x0,y0,x1,y1=s['bbox']
                spans.append(dict(x0=x0,y0=y0,x1=x1,y1=y1,size=s['size'],bold=('Bold' in s['font'] or 'bold' in s['font'] or bool(s['flags']&16)),ital=('Italic' in s['font'] or 'Oblique' in s['font'] or bool(s['flags']&2)),text=t,font=s['font']))
    spans.sort(key=lambda s:(-round(s['size'],1),s['y0'],s['x0']))
    rows=[]
    for s in spans:
        cy=(s['y0']+s['y1'])/2
        best=None;bd=1e9
        for r in rows:
            if r['y0']-0.5<=cy<=r['y1']+0.5:
                dd=abs(cy-(r['y0']+r['y1'])/2)
                if dd<bd: bd=dd;best=r
        if best is None:
            rows.append(dict(y0=s['y0'],y1=s['y1'],size=s['size'],spans=[s]))
        else:
            best['spans'].append(s)
    for r in rows:
        r['spans'].sort(key=lambda s:s['x0'])
        rc=(r['y0']+r['y1'])/2
        parts=[];prev=None
        for s in r['spans']:
            t=s['text']
            sc=(s['y0']+s['y1'])/2
            if s['size']<0.82*r['size'] and prev is not None and s['x0']-prev['x1']<3:
                if sc<rc-1.0: t='^'+t.strip()
                elif sc>rc+1.0: t='_'+t.strip()
            if prev is not None:
                gap=s['x0']-prev['x1']
                if gap>18: parts.append('   ')
                elif gap>1.0 and not parts[-1].endswith(' ') and not t.startswith(' ') and not t.startswith('^') and not t.startswith('_'): parts.append(' ')
            parts.append(t)
            prev=s
        txt=''.join(parts)
        txt=re.sub(r'[ \t]{4,}','   ',txt).rstrip()
        r['text']=txt
        r['x0']=r['spans'][0]['x0']; r['x1']=max(s['x1'] for s in r['spans'])
        r['bold0']=r['spans'][0]['bold']
    rows.sort(key=lambda r:(r['y0'],r['x0']))
    return rows
def sess_key(s):
    return (int(s[1:]), 0 if s[0]=='s' else 1)
def sess_name(s):
    y=2000+int(s[1:])
    return ('May/June ' if s[0]=='s' else 'Oct/Nov ')+str(y)
def list_pairs():
    """Return list of dict(sess,comp,paper,qp,ms,ms_combined) for P1/P2, plus exclusions."""
    files=sorted(os.listdir(SRC))
    qps={};mss={};others=[]
    for fn in files:
        m=re.match(r'5054_([sw]\d\d)_(qp|ms)(?:_(.+))?\.pdf$',fn)
        if not m: continue
        sess,kind,comp=m.group(1),m.group(2),m.group(3) or ''
        if kind=='qp': qps[(sess,comp)]=fn
        else: mss[(sess,comp)]=fn
    pairs=[];excl=[]
    for (sess,comp),fn in sorted(qps.items(),key=lambda kv:(sess_key(kv[0][0]),kv[0][1])):
        if not comp or comp[0] not in '12':
            continue
        if not re.fullmatch(r'[12]\d?',comp):
            excl.append(dict(file=fn,reason='non-standard duplicate/annotated copy of a question paper (scanned "solved" copy); not a distinct paper'))
            continue
        ms=mss.get((sess,comp)); comb=False
        if ms is None and (sess,'') in mss:
            ms=mss[(sess,'')]; comb=True
        if ms is None:
            excl.append(dict(file=fn,reason='no corresponding mark scheme file in repository'))
            continue
        pairs.append(dict(sess=sess,comp=comp,paper=int(comp[0]),qp=fn,ms=ms,combined=comb,id=f'{sess}_{comp}'))
    return pairs,excl
