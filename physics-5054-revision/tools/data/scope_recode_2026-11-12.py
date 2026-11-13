# RECORD ONLY — already applied on 2026-11-12 (the asserts on the old codes make a second run fail).
# One-off scope correction (2026-11-12): series/parallel circuit rules (syllabus 4.3.2/4.3.3), fusion in the Sun (5/6).
import re,sys,io
FD='/home/user/p/physics-5054-revision/findings'
M='4.2.4+X4.3'
P2=[  # (pid,label,old,new)
 *[(a,b,'4.2.4',M) for a,b in [x.split('|') for x in '''s26_22|6cii w25_21|6bi w25_21|6cii s24_22|6dii s24_21|5c w23_21|6bi s23_22|6aii s23_21|3a w22_21|9bi s22_22|5bii
 s22_21|6bi s22_21|6bii w21_21|6bii s21_22|8a w20_21|10cii s20_22|8ciii w19_22|6aii s19_22|6b s19_21|8ai w18_21|7biii s18_22|10e s17_22|10bi s16_22|9bii s16_21|8b
 w15_21|8ai s15_22|10biii w14_22|7bi w14_21|11eii s14_21|7bii w13_21|11ai w13_21|11bii s13_22|6biii w12_22|11ai w12_21|8aii s12_22|8biii s12_22|8biv s11_21|10biv
 s10_22|11cii s10_21|7ai w09_2|11ai s09_2|9bi s09_2|9bii s09_2|9ci w07_2|10civ s07_2|7c s06_2|11cii s04_2|6bii
 s23_22|6b s20_21|8ci w05_2|11bi w05_2|11bii w09_2|11bii'''.split()]],
 ('s18_22','10bii','4.2.4+4.2.3','4.2.4+4.2.3+X4.3'),
 ('s12_21','7c','4.2.3','4.2.3+X4.3'),
 ('s07_2','7ai','4.2.4','X4.3'),('s07_2','7aii','4.2.4','X4.3'),('w06_2','8bi','4.2.4','X4.3'),
]
P2TEXT={  # diode lines: new code and full text (were short out-of-scope notes)
 ('s16_22','8d','X4.3'):('4.2.4+X4.3','action of a diode: passes current (charge) in one direction only, or has a high resistance (acts as an insulator) for current in the other direction / when reverse biased [B1]'),
 ('s20_22','10di','X4.3'):('4.2.4+X4.3','action of a diode: passes current in only one direction (with an alternating supply there is current for only half of each cycle; the current is direct) [B1]'),
 ('s21_21','7biv','X4.3'):('4.2.4+X4.3','diode reversed: no current (no ammeter reading) because the reversed diode does not conduct / has a very high resistance / blocks the current (a reference to its current-voltage graph is accepted) [B1]'),
}
P1=[  # (pid,n,old,new)
 ('w25_12',34,M,'X4.3'),('w20_11',35,M,'X4.3'),('w18_11',30,M,'X4.3'),('w17_12',29,M,'X4.3'),('s16_12',29,M,'X4.3'),('s06_1',32,M,'X4.3'),
 ('w22_11',30,'4.2.4',M),('s19_12',33,'4.2.4',M),('s15_12',34,'4.2.4',M),
 ('w20_12',30,'4.2.2','4.2.2+X4.3'),('s15_12',33,'4.2.2+X4.3','X4.3'),('s05_1',28,'4.2.2+X4.3','X4.3'),
 ('s15_12',35,'4.2.3+X4.3','X4.3'),('s12_12',30,'4.2.3+X4.3','X4.3'),('s13_12',34,'4.2.3+X4.3','X4.3'),
 *[(a,int(b),'1.7.3+X5','X5') for a,b in [x.split('|') for x in 's20_12|18 w19_12|15 s16_12|8 s13_11|10 s11_12|11 w08_1|11 s06_1|12'.split()]],
]
dry=len(sys.argv)>1 and sys.argv[1]=='dry'
n=0
def edit(fn,fun):
    L=open(fn,encoding='utf-8').read().split('\n'); hit=[]
    for i,ln in enumerate(L):
        r=fun(ln)
        if r is not None: hit.append(i); L[i]=r
    assert len(hit)==1,(fn,hit)
    if not dry: open(fn,'w',encoding='utf-8').write('\n'.join(L))
for pid,lab,old,new in P2:
    def f(ln,lab=lab,old=old,new=new):
        p=ln.split('|',2)
        if len(p)==3 and p[0].strip()==lab:
            assert p[1].strip()==old,(pid,lab,p[1])
            return f'{p[0]}| {new} |{p[2]}'
    edit(f'{FD}/p2/{pid}.txt',f); n+=1
for (pid,lab,old),(new,text) in P2TEXT.items():
    def f(ln,lab=lab,old=old,new=new,text=text):
        p=ln.split('|',2)
        if len(p)==3 and p[0].strip()==lab:
            assert p[1].strip()==old,(pid,lab,p[1])
            return f'{p[0]}| {new} | {text}'
    edit(f'{FD}/p2/{pid}.txt',f); n+=1
for pid,q,old,new in P1:
    def f(ln,q=q,old=old,new=new):
        m=re.match(r'^(\d{1,2})(\s+[ABCD]\s+)(\S+)(.*)$',ln)
        if m and int(m.group(1))==q:
            assert m.group(3)==old,(pid,q,m.group(3))
            return m.group(1)+m.group(2)+new+m.group(4)
    edit(f'{FD}/p1/{pid}.txt',f); n+=1
print('edits',n,'dry' if dry else 'written')
