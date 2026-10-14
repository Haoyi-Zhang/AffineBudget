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

def export_exact_catalog(results,output):
    """Inert data export; no producer or optimization call."""
    rows=[json.loads(line) for line in (results/"catalog.jsonl").read_text(encoding="utf-8").splitlines()]
    rows=[row for row in rows if row["case_id"]=="case-043"]
    indices=[tuple(row["catalog_point"]["indices"]) for row in rows]
    import itertools
    expected=list(itertools.product(range(4),repeat=3))
    if indices!=expected or any(type(i) is not int for entry in indices for i in entry):
        raise ValueError("need the complete original 64-point pipeline catalog")
    output.mkdir(parents=True,exist_ok=True)
    path=output/"exact-catalog.csv"
    with path.open("x",encoding="utf-8",newline="") as f:
        fields=("first_index","second_index","third_index","feasible","bound")
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");writer.writeheader()
        for row,index in zip(rows,indices):
            verdict=row["reconstruction"]["verdict"]
            if type(verdict["certified"]) is not bool:
                raise ValueError("mistyped exact catalog verdict")
            writer.writerow(dict(zip(fields[:3],index),feasible=int(verdict["certified"]),bound=verdict["global_bound"]))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--results",type=Path,default=ROOT/"results")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--exact-catalog",action="store_true")
    a=p.parse_args()
    export_exact_catalog(a.results,a.output) if a.exact_catalog else export(a.results,a.output)
