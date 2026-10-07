"""A deterministic, eager FCFS, nonpreemptive finite job model."""
from fractions import Fraction as Q
from heapq import heapify, heappop, heappush
from .algebra import rational, form, value, upper, add, reduce_forms

MAX_JOBS=512

def validate(model):
    domain=tuple(rational(x) for x in model["domain"])
    if not domain or len(domain)>8 or any(x<0 for x in domain):
        raise ValueError("invalid uncertainty domain")
    k=len(domain); jobs=model["jobs"]
    if not jobs or len(jobs)>MAX_JOBS:
        raise ValueError("job count outside budget")
    ids=[j["id"] for j in jobs]
    if any(type(i) is not int for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError("job IDs must be unique integers")
    seen=set()
    for j in jobs:
        if not isinstance(j["resource"],str) or not j["resource"]:
            raise ValueError("bad resource")
        ds=j["deps"]
        if len(ds)!=len(set(ds)) or not set(ds)<=seen:
            raise ValueError("jobs must be in dependency-topological order")
        rel=form(j["release"],k);srv=form(j["service"],k)
        if -upper(tuple(-x for x in rel),domain)<0:
            raise ValueError("release must be nonnegative throughout domain")
        if -upper(tuple(-x for x in srv),domain)<=0:
            raise ValueError("job service must be strictly positive throughout domain")
        seen.add(j["id"])
    return domain

def simulate(model,x):
    domain=validate(model);x=tuple(rational(a) for a in x)
    if len(x)!=len(domain) or any(abs(a)>b for a,b in zip(x,domain)):
        raise ValueError("point outside model domain")
    k=len(x);pending={j["id"]:j for j in model["jobs"]}
    releases={i:value(form(j["release"],k),x) for i,j in pending.items()}
    service={i:value(form(j["service"],k),x) for i,j in pending.items()}
    running={};done={};arrivals={};orders={};t=Q(0)
    while pending or running:
        # Complete every positive-service job ending now before dispatch.
        finished=sorted((i,r,end) for r,(i,end) in running.items() if end<=t)
        for i,r,end in finished:done[i]=end;del running[r]
        by_resource={}
        for i,j in pending.items():
            if set(j["deps"])<=done.keys():
                a=max([releases[i]]+[done[d] for d in j["deps"]])
                arrivals[i]=a
                if a<=t and j["resource"] not in running:
                    by_resource.setdefault(j["resource"],[]).append((a,i))
        for r,ready in sorted(by_resource.items()):
            _,i=min(ready);running[r]=(i,t+service[i]);orders.setdefault(r,[]).append(i)
            del pending[i]
        if not pending and not running:break
        next_times=[end for i,end in running.values()]
        for i,j in pending.items():
            if j["resource"] not in running and set(j["deps"])<=done.keys():
                a=max([releases[i]]+[done[d] for d in j["deps"]])
                if a>t:next_times.append(a)
        if not next_times:raise ValueError("deadlock")
        t=min(next_times)
    return {"orders":orders,"finish":done,"arrival":arrivals,"makespan":max(done.values())}

def graph_for(model,orders):
    domain=validate(model);k=len(domain);z=(Q(0),)*(k+1)
    jobs={j["id"]:j for j in model["jobs"]};previous={}
    if set(orders)!=set(j["resource"] for j in jobs.values()):
        raise ValueError("resource set mismatch")
    flat=[]
    for resource,seq in orders.items():
        last=None
        for i in seq:
            if i not in jobs or jobs[i]["resource"]!=resource:raise ValueError("bad resource order")
            flat.append(i)
            if last is not None:previous[i]=last
            last=i
    if len(flat)!=len(jobs) or set(flat)!=set(jobs):raise ValueError("incomplete resource order")
    edges=[];nodes={"s","m"}
    for i,j in jobs.items():
        a=f"a{i}";c=f"c{i}";nodes.update((a,c))
        edges.append(("s",a,form(j["release"],k)))
        for d in j["deps"]:edges.append((f"c{d}",a,z))
        srv=form(j["service"],k);edges.append((a,c,srv))
        if i in previous:edges.append((f"c{previous[i]}",c,srv))
        edges.append((c,"m",z))
    incoming={v:[] for v in nodes};outgoing={v:[] for v in nodes}
    for u,v,w in edges:incoming[v].append((u,w));outgoing[u].append(v)
    degree={v:len(incoming[v]) for v in nodes};todo=[v for v in nodes if not degree[v]];topo=[]
    heapify(todo)
    while todo:
        u=heappop(todo);topo.append(u)
        for v in outgoing[u]:
            degree[v]-=1
            if not degree[v]:heappush(todo,v)
    if len(topo)!=len(nodes) or topo[0]!="s":raise ValueError("candidate graph cyclic or disconnected")
    guards=[]
    for r,seq in sorted(orders.items()):
        for i,j in zip(seq,seq[1:]):
            guards.append({"left":f"a{i}","right":f"a{j}","strict":i>j,"jobs":[i,j]})
    return domain,topo,incoming,guards,len(edges)

def prepare(model):
    k=len(validate(model));nom=simulate(model,[0]*k)
    domain,topo,incoming,guards,nedges=graph_for(model,nom["orders"])
    fs={"s":((Q(0),)*(k+1),)}
    for v in topo[1:]:
        fs[v]=reduce_forms((add(p,w) for u,w in incoming[v] for p in fs[u]),domain)
    return nom,fs,guards,{"vertices":len(topo),"edges":nedges,"max_frontier":max(map(len,fs.values())),"total_forms":sum(map(len,fs.values()))}
