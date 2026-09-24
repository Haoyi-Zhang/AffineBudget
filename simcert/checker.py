"""Exact certificate checker. This module never imports the LP producer."""
from fractions import Fraction as Q
from .algebra import rational, mixture_bound, upper, interval_bound,single_path_bound
from .model import prepare,validate

def check(model,cert,goal=None):
    domain=validate(model);b=tuple(rational(x) for x in cert["radii"])
    if len(b)!=len(domain) or any(x<0 or x>y for x,y in zip(b,domain)):
        raise ValueError("certificate outside declared domain")
    nom,fs,guards,stats=prepare(model)
    if nom["orders"]!=cert["orders"]:raise ValueError("nominal order mismatch")
    if len(cert["guards"])!=len(guards):raise ValueError("missing or extra guard")
    bounds=[];interval=[];single=[];stable=True
    for g,rec in zip(guards,cert["guards"]):
        if g!=rec["guard"]:raise ValueError("wrong guard")
        ps=fs[g["left"]];qs=fs[g["right"]]
        if len(rec["weights"])!=len(ps):raise ValueError("incomplete left envelope coverage")
        u=max(mixture_bound(p,qs,w,b) for p,w in zip(ps,rec["weights"]))
        bounds.append(u);interval.append(interval_bound(ps,qs,b));single.append(single_path_bound(ps,qs,b))
        stable=stable and (u<0 if g["strict"] else u<=0)
    c0=nom["makespan"];p=(c0,)+(Q(0),)*len(b)
    lower=mixture_bound(p,fs["m"],cert["lower_weights"],b)
    higher=max(upper(f,b)-c0 for f in fs["m"])
    bound=max(Q(0),lower,higher)
    if goal is not None and rational(goal)<0:raise ValueError("negative goal")
    fits=goal is None or bound<=rational(goal)
    ok=lambda us:all(u<0 if g["strict"] else u<=0 for u,g in zip(us,guards))
    return {"certified":bool(stable and fits),"order_certified":bool(stable),"global_bound":str(bound),
            "upward_bound":str(higher),"downward_bound":str(lower),"nominal_makespan":str(c0),
            "guard_bounds":list(map(str,bounds)),"interval_order_certified":ok(interval),
            "single_order_certified":ok(single),"interval_bounds":list(map(str,interval)),
            "single_bounds":list(map(str,single)),"stats":stats}
