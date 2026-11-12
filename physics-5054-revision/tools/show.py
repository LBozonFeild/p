import sys
# usage: show.py p2 <id> <chunk> | show.py p1 <id>
kind=sys.argv[1]
if kind=='p2':
    t=open(f"/home/user/work/digest/p2/{sys.argv[2]}.{sys.argv[3]}.txt").read()
else:
    t=open(f"/home/user/work/digest/p1/{sys.argv[2]}.txt").read()
if len(sys.argv)>4 and kind=='p2':
    i=t.find('━━ Q'+sys.argv[4]+' ')
    t=t[i:]
sys.stdout.write(t)
