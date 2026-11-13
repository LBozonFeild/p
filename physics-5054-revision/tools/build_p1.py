# Build Paper 1 digests (keys hidden) + auto-selected figure sheets
from lib import *
from render import *
qsall=json.load(open(WORK+'/p1_questions.json'))
dup=json.load(open(WORK+'/p1_dupmap.json'))
pairs,excl=list_pairs()
IN=re.compile(r'speed|velocit|accelerat|distance|free fall|terminal|weigh|mass\b|densit|force|friction|spring|extension|load|moment|pivot|balanc|centre of (mass|gravity)|stab(le|ility)|momentum|impulse|collision|kinetic|potential energy|work done|power\b|efficien|energy (source|resource)|renewable|wave|frequency|amplitude|ripple|reflect|refract|mirror|lens|image|\bray|critical angle|total internal|optical fibre|prism|spectrum|dispers|electromagnetic|infra-?red|ultra-?violet|x-ray|microwave|radio wave|sound|echo|ultraso|pitch|loud|compression|rarefaction|charge|electrostatic|electric field|conductor|insulator|coulomb|e\.m\.f|potential difference|p\.d\.|voltmeter|ammeter|resistance|resistor|ohm|micrometer|vernier|caliper|measuring cylinder|stopwatch|pendulum|\brule|scalar|vector|resultant|energy',re.I)
OUT=re.compile(r'thermometer|temperature|thermal|\bheat|conduction|convection|evaporat|boil|melt|freez|latent|specific heat|\bgas\b|gases|molecul|brownian|pressure|manometer|barometer|hydraulic|piston|expan(d|sion)|thermocouple|fixed point|kelvin|condens|magnet|compass|solenoid|\bcoil|transformer|generator|motor\b|relay|induc(ed|tion)|fuse|earth(ed| wire)|live wire|neutral|\bplug|kilowatt|kW ?h|thermistor|LDR|light-dependent|potential divider|logic|\bgate|oscilloscope|c\.r\.o|cathode|thermionic|rectif|turns|capacitor|transistor|time-base|circuit-breaker|nucle(us|i|ar|on)|radioactiv|alpha|beta|half-life|isotope|proton|neutron|decay|count rate|geiger|fission|fusion|planet|galax|universe|red-?shift|solar system|light-year|series|parallel',re.I)
def likely_in(q):
    t=q['text']
    a=len(IN.findall(t)); b=len(OUT.findall(t))
    if b==0: return True
    if a==0: return False
    return a>=b
os.makedirs(WORK+'/digest/p1',exist_ok=True); os.makedirs(WORK+'/sheets/p1',exist_ok=True)
man={}
only=sys.argv[1:]
for p in pairs:
    if p['paper']!=1: continue
    if only and p['id'] not in only: continue
    qs=qsall[p['id']]
    doc=fitz.open(os.path.join(SRC,p['qp']))
    lines=[f"#### P1 {p['id']} ({sess_name(p['sess'])}, comp {p['comp']}) QP={p['qp']} — keys hidden; [F]=figure, [F*]=figure crop on sheet, [T]=table/rules only, DUP=identical text to an earlier-verified question"]
    ims=[];labs=[];sel=[]
    for q in qs:
        d=dup.get(f"{p['id']}#{q['n']}")
        if d:
            lines.append(f"Q{q['n']} =DUP of {d[0]} Q{d[1]}: {q['text'][:70]}…")
            continue
        flag=''
        if q['fig']=='F' or (q['fig']=='T' and re.search(r'graph|diagram shows|shown',q['text'],re.I) and not re.search(r'\brow\b|table',q['text'],re.I)):
            if likely_in(q) and q['fbox']:
                flag='[F*]'; sel.append(q['n'])
                try:
                    im=trim(render_clip(doc[q['page']-1],q['fbox'],zoom=1.25))
                    ims.append(im); labs.append(f"{p['id']} Q{q['n']}")
                except Exception as e: flag='[F!]'
            else: flag='[F]'
        elif q['fig']=='T': flag='[T]'
        lines.append(f"Q{q['n']}{flag} {q['text']}")
    sh=sheet(ims,labs,width=780,maxh=1500) if ims else []
    for i,s in enumerate(sh): s.save(f"{WORK}/sheets/p1/{p['id']}_{i+1}.png",optimize=True)
    lines[0]+=f" | sheets: {len(sh)} (Q{','.join(map(str,sel))})"
    txt='\n'.join(lines)+'\n'
    open(f"{WORK}/digest/p1/{p['id']}.txt",'w').write(txt)
    man[p['id']]=dict(chars=len(txt.encode('utf8')),sheets=len(sh),sel=sel,px=sum(s.width*s.height for s in sh))
if not only:
    json.dump(man,open(WORK+'/p1_manifest.json','w'))
    print('papers',len(man),'chars',sum(m['chars'] for m in man.values()),'max',max(m['chars'] for m in man.values()),'sheets',sum(m['sheets'] for m in man.values()),'Mpx',sum(m['px'] for m in man.values())/1e6,'sel',sum(len(m['sel']) for m in man.values()))
    print('over 19.5k:',[k for k,m in man.items() if m['chars']>19500])
