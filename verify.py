#!/usr/bin/env python3
"""Offline verification of the shipped mathematical data; no SciPy required."""
import os
os.environ.update(OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1")
import json,resource,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if __name__=="__main__":
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(35,35))
    wall=time.perf_counter();cpu=time.process_time()
    from input_audit import audit as audit_inputs
    input_report=audit_inputs()
    tests=unittest.defaultTestLoader.discover(str(ROOT/"tests"))
    result=unittest.TextTestRunner(verbosity=2).run(tests)
    report={"tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"cpu_seconds":time.process_time()-cpu,"wall_seconds":time.perf_counter()-wall,"peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,"workers":1,"input_reproducibility":input_report,"scope":"finite exact tests; not mechanized general proofs"}
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
