"""Deterministic synthetic input generation; not hardware workloads."""
from fractions import Fraction as Q

def af(c,*a):return list(map(str,(Q(c),)+tuple(map(Q,a))))

def make_job(i,r,deps,c,coeff,k=2,release=None):
    return {"id":i,"resource":r,"deps":list(deps),"release":release or af(0,*([0]*k)),"service":af(c,*coeff)}

def shared_prefix(clients=2,seed=0):
    # Two contenders per bank. Opponent readiness is a max of two correlated
    # paths. The shared uncertain prefix must cancel from the comparison.
    pairs=max(1,clients//2);K=(0,2,8)[seed%3]
    jobs=[make_job(0,"prefix",[],10,[0,K])]
    for h in range(pairs):
        q=len(jobs);L=2+(h%3);delta=Q(1,4)
        jobs += [make_job(q,f"prepA{h}",[0],L,[0,0]),
                 make_job(q+1,f"prepB{h}",[0],L+delta,[1,0]),
                 make_job(q+2,f"prepC{h}",[0],L+delta,[-1,0]),
                 make_job(q+3,f"bank{h}",[q],1,[0,0]),
                 make_job(q+4,f"bank{h}",[q+1,q+2],1,[0,0])]
    return {"family":"shared-prefix","clients":clients,"seed":seed,"domain":["1","1"],"jobs":jobs}

def staged(family,clients=4,seed=0):
    jobs=[];last=[None]*clients;barrier=None
    stages=2+(seed%2)
    k=2 if family!="pipeline" else 3
    def coeff(a,b,c=0):return [a,b] if k==2 else [a,b,c]
    for stage in range(stages):
        endings=[]
        for i in range(clients):
            deps=[] if last[i] is None else [last[i]]
            if family=="fork-join" and barrier is not None:deps=[barrier]
            jid=len(jobs);sign=1 if (i+stage+seed)%2 else -1
            release=af(Q(i*(1+seed%3),2) if stage==0 else 0,*([0]*k))
            jobs.append(make_job(jid,f"core{i}",deps,4+i%3,coeff(Q(sign,2),0),k,release))
            jid=len(jobs)
            resource=f"bank{i%2}" if family!="pipeline" else f"channel{(i+stage)%2}"
            jobs.append(make_job(jid,resource,[jid-1],2+(i+seed)%3,coeff(0,Q(sign,4),Q(1,4)),k))
            jid=len(jobs)
            jobs.append(make_job(jid,f"core{i}",[jid-1],2+stage,coeff(Q(-sign,4),0,Q(sign,4)),k))
            last[i]=jid;endings.append(jid)
        if family=="fork-join":
            barrier=len(jobs);jobs.append(make_job(barrier,f"barrier{stage}",endings,1,coeff(0,0),k))
    return {"family":family,"clients":clients,"seed":seed,"domain":["1"]*k,"jobs":jobs}

def unstable(M=100,epsilon=Q(1,100)):
    e=Q(epsilon)
    jobs=[make_job(0,"bank",[],M,[0],1,af(1,0)),
          make_job(1,"bank",[],1,[0],1,af(1+e,2*e)),
          make_job(2,"tail",[1],M,[0],1)]
    return {"family":"order-change-control","domain":["1"],"jobs":jobs}

def suite():
    out=[]
    for family in ["shared-prefix","staggered-bank","fork-join","pipeline"]:
        for clients in [2,4,8,16]:
            for seed in [0,1,2]:
                m=shared_prefix(clients,seed) if family=="shared-prefix" else staged(family,clients,seed)
                m["case_id"]=f"case-{len(out):03d}";out.append(m)
    return out


def orthant_family(m):
    """Independent max-selector switches, with invariant resource orders."""
    if not 1 <= m <= 8: raise ValueError("dimension outside implementation budget")
    zero=[0]*m
    jobs=[make_job(0,"prefix",[],5,zero,m)]
    for h in range(m):
        j=1+5*h; plus=[0]*m;minus=[0]*m;plus[h]=1;minus[h]=-1
        jobs.extend([make_job(j,f"a-pre{h}",[0],2,zero,m),
            make_job(j+1,f"b-plus{h}",[0],Q(9,4),plus,m),
            make_job(j+2,f"b-minus{h}",[0],Q(9,4),minus,m),
            make_job(j+3,f"bank{h}",[j],1,zero,m),
            make_job(j+4,f"bank{h}",[j+1,j+2],1,zero,m)])
    return {"case_id":f"join-{m}","family":"independent-joins","domain":["1"]*m,"jobs":jobs}
