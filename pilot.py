#!/usr/bin/env python3
"""Reproduce the measured discriminating pilot; numerical producer required."""
import os,sys,json,time,resource
os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
resource.setrlimit(resource.RLIMIT_CPU,(35,35))
from simcert.cases import shared_prefix,unstable,staged
from simcert.producer import make_certificate
from simcert.checker import check
from simcert.model import simulate
from simcert.algebra import *
t=time.perf_counter();c=time.process_time();rows=[]
for m in [shared_prefix(2,1),staged('fork-join',4,0),unstable()]:
 cert=make_certificate(m,[1]*len(m['domain']));v=check(m,cert)
 rows.append({'family':m['family'],'jobs':len(m['jobs']),'verdict':v,'nominal':str(simulate(m,[0]*len(m['domain']))['makespan']),'negative_corner':str(simulate(m,[-1]*len(m['domain']))['makespan'])})
ps=[(Q(0),Q(0))];qs=[(Q(1,4),Q(1)),(Q(1,4),Q(-1))]
from simcert.producer import optimize_mixture
w=optimize_mixture(ps[0],qs,[Q(1)])
assert mixture_bound(ps[0],qs,w,[Q(1)])==exact_small_oracle(ps,qs,[Q(1)])[0][0]
record={'phase':'pilot','workers':1,'wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-c,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'rows':rows,'mixture_oracle':str(mixture_bound(ps[0],qs,w,[Q(1)]))}
print(json.dumps(record,indent=2))
from pathlib import Path
if len(sys.argv)!=2:
    raise SystemExit("Usage: python pilot.py OUTPUT_JSON")
p=Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(json.dumps(record,indent=2)+'\n')
