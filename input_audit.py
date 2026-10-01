#!/usr/bin/env python3
"""Canonical temporary-directory regeneration and byte-level input audit."""
from __future__ import annotations
import copy,json,tempfile
from pathlib import Path
from campaign import save
from compare_results import compare_input_bytes
from simcert.cases import suite,orthant_family

ROOT=Path(__file__).resolve().parent

def generated_models():
    models={m["case_id"]:m for m in suite()}
    models.update({f"join-{m}":orthant_family(m) for m in range(1,7)})
    return models

def audit():
    models=generated_models();names=sorted(case_id+".json" for case_id in models)
    source_before={name:(ROOT/"inputs"/name).read_bytes() for name in names}
    with tempfile.TemporaryDirectory(prefix="simcert-input-audit-") as temporary:
        destination=Path(temporary)
        for case_id,model in models.items():save(destination/(case_id+".json"),model)
        matched=compare_input_bytes(ROOT/"inputs",destination,names)
        mutation=copy.deepcopy(models["case-000"])
        mutation["jobs"][0]["service"][1]="1/1000"
        save(destination/"case-000.json",mutation)
        mutation_detected=False
        try:compare_input_bytes(ROOT/"inputs",destination,names)
        except AssertionError as exc:
            mutation_detected="case-000.json" in str(exc)
    source_after={name:(ROOT/"inputs"/name).read_bytes() for name in names}
    report={
      "generated_inputs":len(names),
      "byte_equal_inputs":matched,
      "temporary_directory_generation":True,
      "coefficient_mutation_detected":mutation_detected,
      "source_inputs_unchanged":source_before==source_after,
      "serialization":"json.dumps(indent=2, sort_keys=True) plus one LF",
      "scope":"canonical generated-input identity and source-tree immutability; not scientific theorem validation"
    }
    if matched!=len(names) or not mutation_detected or not report["source_inputs_unchanged"]:
        raise AssertionError(report)
    return report

if __name__=="__main__":
    print(json.dumps(audit(),indent=2,sort_keys=True))
