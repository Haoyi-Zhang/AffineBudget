#!/usr/bin/env python3
"""Optional refreshed-catalog supplement; fresh directories and original caps."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
from simcert.catalog_refresh import CASE_IDS, catalog, compare_catalog


def cohort_counts(models):
    families = ("shared-prefix", "staggered-bank", "fork-join", "pipeline")
    if len(models) != 4:
        raise ValueError("supplement requires the four predeclared models")
    counts = {}
    for model, case, family in zip(models, CASE_IDS, families):
        if (model.get("case_id"), model.get("family"), model.get("clients"), model.get("seed")) != (case, family, 8, 1):
            raise ValueError("predeclared structural selection changed")
        counts[case] = len(catalog(model))
    if list(counts.values()) != [16, 16, 16, 64] or sum(counts.values()) != 112:
        raise ValueError("predeclared catalog coverage changed")
    return counts


def exclusive(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def caps():
    if os.name != "posix":
        raise SystemExit("Numerical supplement requires POSIX resource caps; no uncapped fallback.")
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (35, 35))


def count_call(output, counts, limit, kind):
    if sum(counts.values()) >= limit:
        raise RuntimeError("construct/check call budget exhausted")
    if kind not in counts:
        raise ValueError("unknown call kind")
    index = sum(counts.values())
    exclusive(output / ("call-%03d.json" % index), {"index": index, "kind": kind})
    counts[kind] += 1


def worker(case_id, output):
    # Numerical arm only; portable reconciliation rechecks both arms separately.
    model = json.loads((ROOT / "inputs" / (case_id + ".json")).read_text())
    cert = json.loads((ROOT / "results/models" / (case_id + ".json")).read_text())["certificate"]
    old = json.loads((ROOT / "results/allocation" / (case_id + ".json")).read_text())
    counter = 0
    counts = {"existing-numerical-producer": 0, "zero-only-nominal-onehot": 0, "exact-checker": 0}
    limit = 2 * len(catalog(model)) + 2

    def retain(row):
        nonlocal counter
        exclusive(output / ("point-%03d.json" % counter), row)
        counter += 1

    result = compare_catalog(model, cert, old, record=retain, recheck_frozen=False,
                             call_event=lambda kind: count_call(output, counts, limit, kind))
    exclusive(output / "comparison.json", result)
    return 1 if result["numerical_or_checker_errors"] else 0


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path)
    action.add_argument("--reconcile", type=Path)
    parser.add_argument("--worker-case", choices=CASE_IDS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reconcile:
        if args.worker_case:
            raise SystemExit("Reconciliation is not a numerical worker.")
        args.reconcile = args.reconcile.resolve()
        if args.reconcile.is_relative_to(ROOT):
            raise SystemExit("Use the external numerical-arm destination, not retained artifacts.")
        from simcert.catalog_reconcile import reconcile_directory
        result = reconcile_directory(ROOT, args.reconcile)
        exclusive(args.reconcile / "reconciliation.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    caps()
    os.environ.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
                      MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise SystemExit("Use a fresh destination outside the artifact.")
    if args.worker_case:
        return worker(args.worker_case, output)
    if output.exists():
        raise SystemExit("Existing output preserved; use a new directory.")
    # Inputs/selection/catalog are checked before any numerical calls.
    counts = cohort_counts([json.loads((ROOT / "inputs" / (case + ".json")).read_text())
                            for case in CASE_IDS])
    output.mkdir(parents=True)
    exclusive(output / "plan.json", {"case_ids": list(CASE_IDS), "counts": counts,
              "target": "1", "max_points": 256, "worker_count": 1,
              "maximum_proposal_attempts": 116, "maximum_exact_checker_calls": 116,
              "maximum_construct_check_calls": 232,
              "portable_reconciliation_required": True,
              "address_space_bytes": 3 * 1024**3, "child_cpu_seconds": 35,
              "child_wall_watchdog_seconds": 45,
              "scope": "supplement, not the original four-phase campaign; no timing metrics"})
    outcomes = []
    for case in CASE_IDS:
        folder = output / case
        folder.mkdir()
        command = [sys.executable, "-B", str(Path(__file__).resolve()),
                   "--worker-case", case, "--output", str(folder)]
        exclusive(folder / "command.json", command)
        try:
            result = subprocess.run(command, cwd=ROOT, env=os.environ, capture_output=True,
                                    text=True, timeout=45, check=False)
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or "", exc.stderr or ""
            status, code = "wall_timeout", None
        else:
            stdout, stderr = result.stdout, result.stderr
            code = result.returncode
            status = "completed" if code == 0 else "child_failed"
        for name, stream in (("stdout.txt", stdout), ("stderr.txt", stderr)):
            if isinstance(stream, bytes):
                stream = stream.decode("utf-8", errors="replace")
            with (folder / name).open("x", encoding="utf-8") as handle:
                handle.write(stream)
        rows = sorted(folder.glob("point-*.json"))
        calls = sorted(folder.glob("call-*.json"))
        complete = (folder / "comparison.json").is_file()
        outcome = {"case_id": case, "status": status, "returncode": code,
                   "expected_points": counts[case], "retained_point_records": len(rows),
                   "comparison_present": complete, "recorded_calls": len(calls)}
        outcomes.append(outcome)
        print(json.dumps(outcome), flush=True)
    successful = all(r["status"] == "completed" and r["comparison_present"]
                     and r["retained_point_records"] == r["expected_points"] for r in outcomes)
    recorded_calls = sum(r["recorded_calls"] for r in outcomes)
    successful = successful and recorded_calls <= 232
    exclusive(output / "summary.json", {"numerical_arm_complete_without_errors": successful,
              "recorded_calls": recorded_calls,
              "expected_points": 112, "outcomes": outcomes,
              "scope": "exact finite witness comparison only; failures retained; no timing/continuous optimum"})
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
