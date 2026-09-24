#!/usr/bin/env python3
"""Export plot data directly from complete raw scientific results."""
import argparse,csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FAMILIES=["shared-prefix","staggered-bank","fork-join","pipeline"]

def export(results,output):
    expected={f"case-{i:03d}.json" for i in range(48)}
    actual={p.name for p in (results/"models").glob("*.json")}
    if actual!=expected:raise ValueError("need exactly 48 main cases, not partial coverage")
    models=[json.loads((results/"models"/p).read_text()) for p in sorted(expected)]
    output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for x,family in enumerate(FAMILIES,1):
        ms=[m for m in models if m["family"]==family]
        if len(ms)!=12:raise ValueError("incomplete family")
        rows.append({"x":x,"interval":sum(m["verdict"]["interval_order_certified"] for m in ms),
          "single":sum(m["verdict"]["single_order_certified"] for m in ms),
          "mixture":sum(m["verdict"]["certified"] for m in ms)})
    with (output/"coverage.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    rows=[]
    for m in range(1,7):
        r=json.loads((results/"structure"/f"join-{m}.json").read_text())
        rows.append({"m":m,"forms":r["verdict"]["stats"]["total_forms"],"patterns":r["selector_patterns"]})
    with (output/"structure.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--results",type=Path,default=ROOT/"results")
    p.add_argument("--output",type=Path,required=True);a=p.parse_args();export(a.results,a.output)
