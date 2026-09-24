#!/usr/bin/env python3
"""Benign exact control: changing resource order with invariant makespan."""
import argparse,json,resource,time
from pathlib import Path
from simcert.model import prepare,simulate
from simcert.checker import check
ROOT=Path(__file__).resolve().parent

def evaluate():
    model={"domain":["1"],"jobs":[
      {"id":0,"resource":"bank","deps":[],"release":["0","0"],"service":["3","0"]},
      {"id":1,"resource":"bank","deps":[],"release":["1","0"],"service":["1","0"]},
      {"id":2,"resource":"bank","deps":[],"release":["1","1/2"],"service":["1","0"]}]}
    nominal,fs,guards,_=prepare(model)
    assert all(len(fs[g["left"]])==len(fs[g["right"]])==1 for g in guards) and len(fs["m"])==1
    cert={"radii":["1"],"orders":nominal["orders"],"guards":[{"guard":g,"weights":[["1"]]} for g in guards],"lower_weights":["1"]}
    verdict=check(model,cert);rows=[]
    assert not verdict["order_certified"] and verdict["global_bound"]=="0"
    for x in [-1,0,1]:
        actual=simulate(model,[x]);assert actual["makespan"]==5
        assert actual["orders"]["bank"]==([0,2,1] if x<0 else [0,1,2])
        rows.append({"point":x,"orders":actual["orders"],"makespan":str(actual["makespan"])})
    return {"model":model,"certificate":cert,"verdict":verdict,"samples":rows,
            "interpretation":"guard completeness is about order, not all true makespan error bounds"}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=ROOT/"results/boundary-control.json");a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(35,35))
    cpu=time.process_time();wall=time.perf_counter();r=evaluate()
    r["measurement"]={"cpu_seconds":time.process_time()-cpu,"wall_seconds":time.perf_counter()-wall,"peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,"workers":1}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps(r["verdict"],indent=2))
