import sys,re
# usage: p1fix.py <pid> "<n> <ans> <sec> <text>" ...   replaces (or adds) question lines, optional "#+ text" appends to the header note
FD='/home/user/p/physics-5054-revision/findings/p1/'
pid=sys.argv[1]; fn=FD+pid+'.txt'
L=open(fn).read().rstrip('\n').split('\n')
for new in sys.argv[2:]:
    if new.startswith('#+'):
        L[0]=L[0]+new[2:]; continue
    n=new.split()[0]; done=False
    for i,l in enumerate(L):
        if re.match(r'^%s\s'%n,l): L[i]=new; done=True
    if not done: L.append(new)
head=[l for l in L if l.startswith('#')]; body=[l for l in L if not l.startswith('#')]
body.sort(key=lambda l:int(l.split()[0]))
open(fn,'w').write('\n'.join(head+body)+'\n')
