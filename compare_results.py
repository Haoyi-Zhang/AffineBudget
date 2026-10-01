#!/usr/bin/env python3
"""Scientific reconciliation of a complete fresh run, excluding elapsed times.

Exact bounds and verdicts must match. Solver weights may differ only if the
checker still validates their recorded outcomes. No tolerance is used.
"""
import argparse,json
from pathlib import Path
from simcert.checker import check
from simcert.algebra import rational,mixture_bound,exact_small_oracle
ROOT=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def require(condition,why):
    if not condition:raise AssertionError(why)
def compare_input_bytes(reference_inputs,fresh_inputs,names):
    require({p.name for p in fresh_inputs.glob("*.json")}==set(names),
            f"incomplete fresh inputs: {fresh_inputs}")
    for name in names:
        require((reference_inputs/name).read_bytes()==(fresh_inputs/name).read_bytes(),
                f"generated input byte difference: {name}")
    return len(names)
def compare(reference,fresh):
    counts={}
    input_names=[f"case-{i:03d}.json" for i in range(48)]+[f"join-{i}.json" for i in range(1,7)]
    counts["inputs"]=compare_input_bytes(ROOT/"inputs",fresh/"inputs",input_names)
    groups={"models":[f"case-{i:03d}.json" for i in range(48)],
      "oracles":[f"oracle-{i:04d}.json" for i in range(2089)],
      "allocation":[f"case-{i:03d}.json" for i in (7,19,31,43)],
      "structure":[f"join-{i}.json" for i in range(1,7)]}
    for group,names in groups.items():
        for root in (reference,fresh):
            require({p.name for p in (root/group).glob("*.json")}==set(names),f"incomplete {group}: {root}")
        for name in names:
            old=load(reference/group/name);new=load(fresh/group/name)
            if group=="models":
                model=load(fresh/"inputs"/name)
                require(check(model,new["certificate"])==new["verdict"],f"unvalidated fresh certificate {name}")
                fields=("case_id","family","clients","seed","jobs","verdict","samples")
            elif group=="oracles":
                ps=[tuple(map(rational,p)) for p in new["left"]]
                qs=[tuple(map(rational,q)) for q in new["right"]]
                b=tuple(map(rational,new["radii"]))
                bound=max(mixture_bound(p,qs,w,b) for p,w in zip(ps,new["weights"]))
                require(len(new["weights"])==len(ps),f"incomplete fresh oracle {name}")
                require(bound==rational(new["bound"]),f"invalid fresh oracle witness {name}")
                require(exact_small_oracle(ps,qs,b)[0][0]==rational(new["oracle"]),f"invalid fresh oracle value {name}")
                fields=("id","left","right","radii","bound","oracle","point","vertices","equal")
            elif group=="structure":
                model=load(fresh/"inputs"/name)
                require(check(model,new["certificate"])==new["verdict"],f"unvalidated fresh structural certificate {name}")
                fields=("m","jobs","selector_patterns","verdict","samples")
            else:fields=tuple(old)
            for field in fields:require(old[field]==new[field],f"scientific difference: {group}/{name}:{field}")
        counts[group]=len(names)
    for file,fields in [("pilot.json",("rows","mixture_oracle")),
                        ("summary.json",("families","models","oracles","oracle_equal","oracle_unsound","dynamic_points"))]:
        old=load(reference/file);new=load(fresh/file)
        for field in fields:require(old[field]==new[field],f"scientific difference: {file}:{field}")
    old=load(reference/"reduction.json");new=load(fresh/"reduction.json")
    for field in old:
        if field not in ("measurement",):require(old[field]==new[field],f"reduction difference: {field}")
    counts["reduction_formulas"]=len(old["formulas"])
    from boundary_check import evaluate
    old=load(reference/"boundary-control.json");new=load(fresh/"boundary-control.json")
    for field,value in evaluate().items():
        require(old[field]==new[field]==value,f"boundary control difference: {field}")
    counts["changed_order_constant_makespan_control"]=1
    return {"scientific_fields_equal":True,"counts":counts,"tolerance":0,
      "not_compared":"solver weight vectors and measurement times; fresh inputs compared byte for byte and fresh witnesses checked against them"}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("fresh",type=Path)
    p.add_argument("--reference",type=Path,default=ROOT/"results");a=p.parse_args()
    print(json.dumps(compare(a.reference,a.fresh),indent=2))
