#!/usr/bin/env python3
"""Sequential bounded-phase reproduction. No network or parallel workers."""
import argparse,json,os,resource,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument("output",type=Path)
p.add_argument("phase",choices=["models","oracles","allocation","verify"]);args=p.parse_args()
out=args.output.resolve();phase=args.phase
if phase=="models":
    if out.exists():raise SystemExit("Output already exists; start models in a new directory")
    out.mkdir(parents=True)
elif not out.is_dir():raise SystemExit("Run the models phase first")
previous={"oracles":"models","allocation":"oracles","verify":"allocation"}
if phase in previous and not (out/("phase-"+previous[phase]+".json")).is_file():
    raise SystemExit("Complete the previous phase first")
if (out/("phase-"+phase+".json")).exists():raise SystemExit("Phase already complete")
os.environ.update(OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",NUMEXPR_NUM_THREADS="1")
start=time.perf_counter();before=resource.getrusage(resource.RUSAGE_CHILDREN);own=time.process_time();steps=0
raw=out/"raw-output"/(phase+"-"+str(time.time_ns()))
raw.mkdir(parents=True)

def run(arguments,receipt=None):
    global steps
    print("RUN", " ".join(arguments),flush=True)
    prefix=raw/(f"step-{steps:02d}")
    command=[sys.executable,"-B"]+arguments
    prefix.with_suffix(".command.json").write_text(json.dumps(command)+"\n",encoding="utf-8")
    def retain(stdout,stderr):
        for suffix,stream in ((".stdout.txt",stdout),(".stderr.txt",stderr)):
            if isinstance(stream,bytes):stream=stream.decode("utf-8",errors="replace")
            prefix.with_suffix(suffix).write_text(stream or "",encoding="utf-8")
    try:
        r=subprocess.run(command,cwd=ROOT,env=os.environ,check=False,
              capture_output=True,text=True,timeout=45)
    except subprocess.TimeoutExpired as exc:
        retain(exc.stdout,exc.stderr)
        raise
    retain(r.stdout,r.stderr)
    if r.returncode:
        print(r.stdout[-1000:],end="",flush=True)
        print(r.stderr[-2000:],end="",file=sys.stderr,flush=True)
    r.check_returncode()
    if receipt:(out/receipt).write_text(r.stdout)
    steps+=1;print(r.stdout[-1000:],end="",flush=True)

if phase=="models":
    run(["pilot.py",str(out/"pilot.json")])
    for i in range(0,48,12):run(["campaign.py","models","--start",str(i),"--stop",str(i+12),"--output",str(out)])
elif phase=="oracles":
    for i in range(0,2089,256):run(["campaign.py","oracles","--start",str(i),"--stop",str(min(i+256,2089)),"--output",str(out)])
elif phase=="allocation":
    for i in (7,19,31,43):run(["campaign.py","allocate","--start",str(i),"--stop",str(i+1),"--output",str(out)])
    run(["campaign.py","structure","--start","1","--stop","7","--output",str(out)])
    run(["reduction_check.py","--output",str(out/"reduction.json")])
    run(["-S","boundary_check.py","--output",str(out/"boundary-control.json")])
else:
    run(["campaign.py","summarize","--output",str(out)])
    run(["-S","export_figures.py","--results",str(out),"--output",str(out/"figure-data")])
    run(["-S","compare_results.py",str(out)],"reconciliation.json")
    run(["-S","verify.py"],"verification.json")

end=resource.getrusage(resource.RUSAGE_CHILDREN)
r={"phase":phase,"complete":True,"steps":steps,"child_failures":0,"workers":1,
   "wall_seconds":time.perf_counter()-start,
   "aggregate_cpu_seconds":end.ru_utime+end.ru_stime-before.ru_utime-before.ru_stime+time.process_time()-own,
   "peak_child_rss_kib":end.ru_maxrss}
(out/("phase-"+phase+".json")).write_text(json.dumps(r,indent=2)+"\n")
if phase=="verify":
    phases=[json.loads((out/("phase-"+q+".json")).read_text()) for q in ("models","oracles","allocation","verify")]
    r={"complete":True,"phases":phases,"steps":sum(q["steps"] for q in phases),"child_failures":0,"workers":1,
       "wall_seconds":sum(q["wall_seconds"] for q in phases),
       "aggregate_cpu_seconds":sum(q["aggregate_cpu_seconds"] for q in phases),
       "peak_child_rss_kib":max(q["peak_child_rss_kib"] for q in phases),
       "reconciliation":json.loads((out/"reconciliation.json").read_text()),
       "verification":json.loads((out/"verification.json").read_text()),
       "scope":"clean generation and scientific reconciliation; not independent review or mechanized proof"}
    (out/"reproduction.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r,indent=2))
