#!/usr/bin/env python3
"""Resumable one-worker experiments, exact checking and deterministic outputs."""
import os
os.environ.update(OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",NUMEXPR_NUM_THREADS="1")
import argparse,copy,csv,itertools,json,random,resource,time
from pathlib import Path
from fractions import Fraction as Q
from simcert.algebra import *
from simcert.model import prepare,simulate
from simcert.producer import make_certificate,optimize_mixture
from simcert.checker import check
from simcert.cases import suite,unstable,orthant_family

ROOT=Path(__file__).resolve().parent

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    temporary.replace(path)

def case_run(model):
    begin=time.perf_counter();cpu=time.process_time()
    cert=make_certificate(model,[1]*len(model["domain"]));produced=time.perf_counter()
    verdict=check(model,cert);checked=time.perf_counter()
    nom=simulate(model,[0]*len(model["domain"]));samples=[]
    for point in itertools.product([-1,0,1],repeat=len(model["domain"])):
        out=simulate(model,point);same=out["orders"]==nom["orders"]
        err=abs(out["makespan"]-nom["makespan"])
        if verdict["certified"] and (not same or err>Q(verdict["global_bound"])):
            raise AssertionError("false certified dynamic execution")
        samples.append({"point":list(point),"same_order":same,"makespan":str(out["makespan"]),"absolute_error":str(err)})
    return {"case_id":model["case_id"],"family":model["family"],"clients":model["clients"],"seed":model["seed"],"jobs":len(model["jobs"]),"certificate":cert,"verdict":verdict,"samples":samples,
       "measurement":{"producer_wall_seconds":produced-begin,"checker_wall_seconds":checked-produced,"wall_seconds":time.perf_counter()-begin,"cpu_seconds":time.process_time()-cpu,"peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,"workers":1}}

def oracle_inputs():
    pool=[(Q(c),Q(a)) for c in range(3) for a in [-1,0,1]]
    polys=[(x,) for x in pool]+list(itertools.combinations(pool,2))
    out=[(p,q,(Q(1),)) for p in polys for q in polys]
    rng=random.Random(73019)
    for i in range(64):
        mk=lambda:tuple(tuple(map(Q,[rng.randrange(7),rng.randrange(-2,3),rng.randrange(-2,3)])) for j in range(1+rng.randrange(4)))
        out.append((mk(),mk(),(Q(1),Q(1))))
    return out

def oracle_run(index,item):
    ps,qs,b=item;w=[optimize_mixture(p,qs,b) for p in ps]
    bound=max(mixture_bound(p,qs,z,b) for p,z in zip(ps,w))
    (exact,point),nv=exact_small_oracle(ps,qs,b)
    if bound<exact:raise AssertionError("unsound mixture bound")
    return {"id":index,"left":[list(map(str,p)) for p in ps],"right":[list(map(str,q)) for q in qs],"radii":list(map(str,b)),"weights":[list(map(str,z)) for z in w],"bound":str(bound),"oracle":str(exact),"point":list(map(str,point)),"vertices":nv,"equal":bound==exact}

def allocate(model,certificate,target=Q(1)):
    levels=[Q(0),Q(1,4),Q(1,2),Q(1)];k=len(model["domain"]);rows=[]
    for indices in itertools.product(range(4),repeat=k):
        c=copy.deepcopy(certificate);c["radii"]=[str(levels[i]) for i in indices]
        verdict=check(model,c,target);score=sum((j+1)*i for j,i in enumerate(indices))
        rows.append({"indices":list(indices),"radii":c["radii"],"score":score,"feasible":verdict["certified"],"bound":verdict["global_bound"]})
    feasible=[r for r in rows if r["feasible"]]
    best=max(feasible,key=lambda r:(r["score"],tuple(r["indices"]))) if feasible else None
    return {"case_id":model["case_id"],"target":str(target),"objective":"sum((dimension+1)*level_index)","restriction":"frozen maximum-domain witnesses and finite catalog only","selected":best,"candidates":rows}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("mode",choices=["models","oracles","allocate","structure","summarize"])
    parser.add_argument("--start",type=int,default=0);parser.add_argument("--stop",type=int,default=48)
    parser.add_argument("--output",type=Path,default=ROOT/"results");args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(35,35))
    start=time.process_time();wall=time.perf_counter();out=args.output
    if args.mode=="models":
        for m in suite()[args.start:args.stop]:
            save(out/"inputs"/(m["case_id"]+".json"),m)
            result=case_run(m);save(out/"models"/(m["case_id"]+".json"),result)
            print(m["case_id"],result["verdict"]["certified"],result["verdict"]["stats"],flush=True)
    elif args.mode=="oracles":
        items=oracle_inputs()
        for i in range(args.start,min(args.stop,len(items))):save(out/"oracles"/(f"oracle-{i:04d}.json"),oracle_run(i,items[i]))
        print("oracles",args.start,min(args.stop,len(items)),flush=True)
    elif args.mode=="structure":
        for m in range(max(1,args.start),min(7,args.stop)):
            model=orthant_family(m);cert=make_certificate(model,[1]*m);v=check(model,cert)
            assert v["certified"] and Q(v["global_bound"])==Q(1,4)
            nom=simulate(model,[0]*m);rows=[]
            for point in itertools.product([-1,1],repeat=m):
                actual=simulate(model,point)
                assert actual["orders"]==nom["orders"] and actual["makespan"]==Q(37,4)
                rows.append({"point":list(point),"makespan":str(actual["makespan"]),"same_order":True})
            save(out/"inputs"/(model["case_id"]+".json"),model)
            save(out/"structure"/(model["case_id"]+".json"),{"m":m,"jobs":len(model["jobs"]),"selector_patterns":len(rows),"certificate":cert,"verdict":v,"samples":rows})
            print("independent joins",m,v["stats"],flush=True)
    elif args.mode=="allocate":
        for m in suite()[args.start:args.stop]:
            result=json.loads((out/"models"/(m["case_id"]+".json")).read_text())
            save(out/"allocation"/(m["case_id"]+".json"),allocate(m,result["certificate"]))
    else:
        models=[json.loads(p.read_text()) for p in sorted((out/"models").glob("*.json"))]
        oracles=[json.loads(p.read_text()) for p in sorted((out/"oracles").glob("*.json"))]
        rows=[]
        for family in sorted(set(m["family"] for m in models)):
            ms=[m for m in models if m["family"]==family]
            rows.append({"family":family,"cases":len(ms),"mixture":sum(m["verdict"]["certified"] for m in ms),"single":sum(m["verdict"]["single_order_certified"] for m in ms),"interval":sum(m["verdict"]["interval_order_certified"] for m in ms),"sample_changed_cases":sum(any(not x["same_order"] for x in m["samples"]) for m in ms),"max_jobs":max(m["jobs"] for m in ms),"max_frontier":max(m["verdict"]["stats"]["max_frontier"] for m in ms)})
        summary={"families":rows,"models":len(models),"oracles":len(oracles),"oracle_equal":sum(o["equal"] for o in oracles),"oracle_unsound":sum(Q(o["bound"])<Q(o["oracle"]) for o in oracles),"dynamic_points":sum(len(m["samples"]) for m in models),"model_cpu_seconds":sum(m["measurement"]["cpu_seconds"] for m in models),"max_rss_kib":max([m["measurement"]["peak_rss_kib"] for m in models] or [0])}
        save(out/"summary.json",summary)
        with (out/"coverage.csv").open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        print(json.dumps(summary,indent=2))
    save(out/"accounting"/(f"{args.mode}-{args.start}-{args.stop}.json"),{"mode":args.mode,"start":args.start,"stop":args.stop,"cpu_seconds":time.process_time()-start,"wall_seconds":time.perf_counter()-wall,"peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,"workers":1})

if __name__=="__main__":main()
