#!/usr/bin/env python3
"""Exact finite validation of the compact-DAG comparison reduction.

Uses only the Python standard library. The general reduction is proved in
proofs/arguments.md; enumeration here checks the stated algebra on small CNFs.
"""
import argparse
import itertools
import json
import random
import resource
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def clauses(n):
    return [tuple(s*(i+1) for i,s in zip(v,sgn))
            for v in itertools.combinations(range(n),3)
            for sgn in itertools.product((-1,1),repeat=3)]


def formulas():
    pool=clauses(3)
    for mask in range(256):
        yield 3,[c for i,c in enumerate(pool) if mask&(1<<i)]
    rng=random.Random(99017)
    pool=clauses(4)
    for _ in range(256):
        yield 4,sorted(rng.sample(pool,1+rng.randrange(16)))


def evaluate(n,cnf):
    sat=0;equal=0;count=0
    for x in itertools.product((-1,1),repeat=n):
        literal_sums=[sum((1 if a>0 else -1)*x[abs(a)-1] for a in c) for c in cnf]
        is_sat=all(t>=-1 for t in literal_sums)
        u=2*n+sum(abs(v) for v in x)
        v=max([3*n]+[3*n-1-t for t in literal_sums])
        assert u<=v
        assert (u==v)==is_sat
        sat+=is_sat;equal+=u==v;count+=1
    return {'satisfying_assignments':sat,'equality_assignments':equal,'assignments':count}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'results/reduction.json')
    args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(35,35))
    cpu=time.process_time();wall=time.perf_counter()
    rows=[]
    for i,(n,cnf) in enumerate(formulas()):
        rows.append({'id':i,'variables':n,'clauses':cnf,**evaluate(n,cnf)})
    result={'formulas':rows,'summary':{'formulas':len(rows),'assignments':sum(r['assignments'] for r in rows),
             'satisfiable_formulas':sum(r['satisfying_assignments']>0 for r in rows),'mismatches':0},
             'measurement':{'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-wall,
              'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='formulas'},indent=2))


if __name__=='__main__':
    main()
