"""Untrusted floating-point LP search; exact checking is separate."""
import warnings
from fractions import Fraction as Q
from .algebra import rational, mixture_bound, upper
from .model import prepare,validate

def optimize_mixture(p,qs,b):
    # The LP may propose a poor rational witness; it cannot certify it.
    import numpy as np
    from scipy.optimize import linprog
    n=len(qs);k=len(b)
    if n==1:return [Q(1)]
    c=[-float(q[0]) for q in qs]+[float(x) for x in b]
    A=[];rhs=[]
    for i in range(k):
        row=[-float(q[i+1]) for q in qs]+[0.0]*k;row[n+i]=-1.0
        A.append(row);rhs.append(-float(p[i+1]))
        row=[float(q[i+1]) for q in qs]+[0.0]*k;row[n+i]=-1.0
        A.append(row);rhs.append(float(p[i+1]))
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore",message="Unrecognized options detected")
        sol=linprog(c,A_ub=np.array(A),b_ub=rhs,A_eq=[[1.0]*n+[0.0]*k],b_eq=[1.0],
                    bounds=[(0,None)]*(n+k),method="highs-ds",options={"threads":1,"parallel":False})
    if not sol.success:raise RuntimeError("LP search failed: "+sol.message)
    w=[Q(max(0.0,float(v))).limit_denominator(1000000) for v in sol.x[:n]]
    total=sum(w,Q(0))
    if not total:raise RuntimeError("zero reconstructed mass")
    return [v/total for v in w]

def make_certificate(model,b):
    b=tuple(rational(x) for x in b);domain=validate(model)
    if len(b)!=len(domain) or any(x<0 or x>y for x,y in zip(b,domain)):
        raise ValueError("invalid radii")
    nom,fs,guards,stats=prepare(model)
    records=[]
    for g in guards:
        ps=fs[g["left"]];qs=fs[g["right"]]
        weights=[optimize_mixture(p,qs,b) for p in ps]
        records.append({"guard":g,"weights":[list(map(str,w)) for w in weights]})
    p=(nom["makespan"],)+(Q(0),)*len(b)
    lower=optimize_mixture(p,fs["m"],b)
    return {"radii":list(map(str,b)),"orders":nom["orders"],"guards":records,"lower_weights":list(map(str,lower))}
