# usage: next.py <pid> [chunk]  -> prints digest chunk; for chunk 1 renders auto-selected in-scope figure sheet(s)
from lib import *
from render import *
from PIL import Image
import io, contextlib
pid=sys.argv[1]; ch=int(sys.argv[2]) if len(sys.argv)>2 else 1
IN=re.compile(r'speed|velocit|accelerat|distance|free fall|terminal|weigh|\bmass\b|densit|force|friction|spring|extension|load|moment|pivot|balanc|centre of (mass|gravity)|stab(le|ility)|momentum|impulse|collision|kinetic|potential energy|work done|power\b|efficien|energy (source|resource)|renewable|wave|frequency|amplitude|ripple|reflect|refract|mirror|lens|image|\bray|critical angle|total internal|optical fibre|prism|spectrum|dispers|electromagnetic|infra-?red|ultra-?violet|x-ray|microwave|radio wave|sound|echo|ultraso|pitch|loud|compression|rarefaction|charge|electrostatic|electric field|conductor|insulator|coulomb|e\.m\.f|potential difference|p\.d\.|voltmeter|ammeter|resistance|resistor|ohm|micrometer|vernier|caliper|measuring cylinder|stopwatch|pendulum|\brule|scalar|vector|resultant|energy',re.I)
OUT=re.compile(r'thermometer|temperature|thermal|\bheat|conduction|convection|evaporat|boil|melt|freez|latent|specific heat|\bgas\b|gases|molecul|brownian|pressure|manometer|barometer|hydraulic|piston|thermocouple|kelvin|condens|magnet|compass|solenoid|\bcoil|transformer|generator|motor\b|relay|induc(ed|tion)|fuse|earth(ed| wire)|live wire|neutral|\bplug|kilowatt|kW ?h|thermistor|LDR|light-dependent|potential divider|logic|\bgate|oscilloscope|c\.r\.o|cathode|thermionic|rectif|turns|capacitor|transistor|time-base|nucle(us|i|ar|on)|radioactiv|alpha|beta|half-life|isotope|proton|neutron|decay|count rate|geiger|fission|fusion|planet|galax|universe|red-?shift|solar system|light-year|orbit|\bstar\b',re.I)
t=open(f"{WORK}/digest/p2/{pid}.{ch}.txt").read()
sys.stdout.write(t)
if ch==1:
    full=''.join(open(f"{WORK}/digest/p2/{pid}.{i}.txt").read() for i in range(1,5) if os.path.exists(f"{WORK}/digest/p2/{pid}.{i}.txt"))
    sel=[];skip=[]
    for blk in full.split('━━ Q')[1:]:
        qtext=blk.split('── MS Q')[0]
        m=re.search(r'figs ([^\]]+)\]',qtext.split('\n')[0])
        if not m: continue
        fids=[x.split('(')[0] for x in m.group(1).split()]
        a=len(IN.findall(qtext)); b=len(OUT.findall(qtext))
        if a>=b*1.2 or b==0: sel+=fids
        else: skip+=fids
    ims=[];labs=[]
    for a in sel:
        fn=f"{WORK}/crops/p2/{pid}/f{a.replace('.','_')}.png"
        if not os.path.exists(fn): continue
        im=Image.open(fn).convert('L')
        im=im.resize((int(im.width*0.85),int(im.height*0.85)))
        ims.append(im); labs.append(f"{pid} {a}")
    os.makedirs(WORK+'/view',exist_ok=True)
    for f in os.listdir(WORK+'/view'):
        if f.startswith(pid+'_a'): os.remove(WORK+'/view/'+f)
    sh=sheet(ims,labs,width=1000,maxh=1400) if ims else []
    out=[]
    for i,s in enumerate(sh):
        fn=f"{WORK}/view/{pid}_a{i+1}.png"; s.save(fn); out.append(f"{fn} {s.size}")
    print(f"\n[auto fig sheets: {'; '.join(out) or 'none'} | shown: {' '.join(sel)} | not shown: {' '.join(skip)}]")
