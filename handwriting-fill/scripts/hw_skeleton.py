'''Turn filled glyph bitmaps into pen paths (thinning + tracing). usage: hw_skeleton.py glyphs_dump.json out_skel.json'''
import json,math,sys
M=json.load(open(sys.argv[1]))
em=M['em']; ox=M['ox']; base=M['baseRow']
def N8(p):
    x,y=p; return [(x,y-1),(x+1,y-1),(x+1,y),(x+1,y+1),(x,y+1),(x-1,y+1),(x-1,y),(x-1,y-1)]
def thin(P):
    P=set(P); changed=True
    while changed:
        changed=False
        for step in (0,1):
            rem=[]
            for p in P:
                n=[q in P for q in N8(p)]
                B=sum(n)
                if B<2 or B>6: continue
                A=sum((not n[i]) and n[(i+1)%8] for i in range(8))
                if A!=1: continue
                if step==0:
                    if (n[0] and n[2] and n[4]) or (n[2] and n[4] and n[6]): continue
                else:
                    if (n[0] and n[2] and n[6]) or (n[0] and n[4] and n[6]): continue
                rem.append(p)
            if rem: changed=True; P.difference_update(rem)
    return P
def trace(P):
    nb=lambda p:[q for q in N8(p) if q in P]
    unv=set(P); out=[]
    while unv:
        ends=[p for p in unv if len(nb(p))<=1]
        if not ends: ends=[p for p in unv if sum(1 for q in nb(p) if q in unv)<=1]
        start=min(ends or unv,key=lambda p:(p[1]+p[0]*0.3))
        path=[start]; unv.discard(start)
        vis=[q for q in nb(start) if q not in unv]
        attached=bool(vis)
        if vis: path.insert(0,vis[0])
        cur=start
        while True:
            c=[q for q in nb(cur) if q in unv]
            if not c: break
            if len(path)>=4:
                ref=path[-4]; dx,dy=cur[0]-ref[0],cur[1]-ref[1]; L=math.hypot(dx,dy) or 1
                nxt=max(c,key=lambda q:((q[0]-cur[0])*dx+(q[1]-cur[1])*dy)/L/math.hypot(q[0]-cur[0],q[1]-cur[1]))
            else:
                nxt=min(c,key=lambda q:abs(q[0]-cur[0])+abs(q[1]-cur[1]))
            path.append(nxt); unv.discard(nxt); cur=nxt
        vis=[q for q in nb(cur) if q not in unv and q not in path[-5:]]
        if vis: path.append(vis[0]); attached=True
        out.append((path,attached))
    return out
def smooth(path,win=4,step=5):
    n=len(path)
    if n<3: return [tuple(map(float,p)) for p in path]
    sm=[]
    for i in range(n):
        a=max(0,i-win); b=min(n,i+win+1)
        k=min(i-a,b-1-i)          # shrink the window near the ends so end points stay put
        seg=path[i-k:i+k+1]
        sm.append((sum(p[0] for p in seg)/len(seg),sum(p[1] for p in seg)/len(seg)))
    res=[sm[0]]; acc=0
    for i in range(1,n):
        acc+=math.hypot(sm[i][0]-sm[i-1][0],sm[i][1]-sm[i-1][1])
        if acc>=step: res.append(sm[i]); acc=0
    if res[-1]!=sm[-1]: res.append(sm[-1])
    return res
G={}
for ch,g in M['glyphs'].items():
    P=thin([tuple(p) for p in g['fg']])
    strokes=[]
    for path,att in trace(P):
        if att and len(path)<12: continue        # drop short spurs left at junctions
        pts=smooth(path)
        strokes.append([[(x-ox)/em,(base-y)/em] for x,y in pts])   # em units, y up
    G[ch]={'adv':g['adv'],'strokes':strokes}
json.dump(G,open(sys.argv[2],'w'),ensure_ascii=False)
print('pen paths built for',len(G),'characters')
