"""Portable reconciliation of the separate numerical arm; no LP or resource import."""
from __future__ import annotations
import json
from pathlib import Path
from .algebra import rational
from .catalog_refresh import CASE_IDS, catalog, frozen_row, selected
from .checker import check


def call_kinds(rows):
    kinds = []
    for row in rows:
        for attempt in row["refreshed"]["attempts"]:
            kinds.append(attempt["policy"])
            if "certificate" in attempt:
                kinds.append("exact-checker")
    return kinds


def reconcile_record(model, certificate, retained, comparison):
    target = rational(retained["target"])
    if target != 1 or comparison["target"] != "1":
        raise ValueError("target changed")
    points = catalog(model)
    frozen = [frozen_row(model, certificate, point, target) for point in points]
    expected = {"case_id": model["case_id"], "target": "1",
                "objective": "sum((dimension+1)*level_index)",
                "restriction": "frozen maximum-domain witnesses and finite catalog only",
                "selected": selected(frozen), "candidates": frozen}
    if expected != retained:
        raise ValueError("frozen reconciliation failed; no resealing")
    rows = comparison["rows"]
    if len(rows) != len(points) or [r["frozen"] for r in rows] != frozen:
        raise ValueError("missing, duplicate or changed frozen rows")
    fresh, errors, checked = [], 0, len(frozen)
    for point, row in zip(points, rows):
        new = row["refreshed"]
        if {k: new[k] for k in ("indices", "radii", "score")} != point:
            raise ValueError("fresh point coverage changed")
        attempts = new["attempts"]
        if not 1 <= len(attempts) <= 2 or attempts[0]["policy"] != "existing-numerical-producer":
            raise ValueError("unexpected proposal policy/count")
        if len(attempts) == 2:
            if (any(rational(r) for r in point["radii"])
                    or attempts[0]["status"] == "certified"
                    or attempts[1]["policy"] != "zero-only-nominal-onehot"):
                raise ValueError("invalid nominal fallback")
        for attempt in attempts:
            status = attempt["status"]
            if status == "producer_error":
                if (set(attempt) != {"policy", "status", "error_type", "error"}
                        or not attempt.get("error_type")):
                    raise ValueError("invalid producer error record")
                errors += 1
                continue
            if "certificate" not in attempt:
                raise ValueError("missing proposed certificate")
            fields = ({"policy", "status", "certificate", "error_type", "error"}
                      if status == "checker_error" else {"policy", "status", "certificate", "verdict"})
            if set(attempt) != fields:
                raise ValueError("unexpected attempt fields")
            checked += 1
            try:
                verdict = check(model, attempt["certificate"], target)
                if (tuple(map(rational, attempt["certificate"]["radii"]))
                        != tuple(map(rational, point["radii"]))):
                    raise ValueError("proposal radii differ from catalog point")
            except Exception as exc:
                if (status != "checker_error" or attempt.get("error_type") != type(exc).__name__
                        or attempt.get("error") != str(exc)):
                    raise ValueError("unreconciled checker error") from exc
                errors += 1
            else:
                if (status != ("certified" if verdict["certified"] else "refused")
                        or attempt.get("verdict") != verdict):
                    raise ValueError("fresh full verdict mismatch")
        chosen = attempts[0]
        if len(attempts) == 2 and attempts[1]["status"] == "certified":
            chosen = attempts[1]
        verdict = chosen.get("verdict")
        expected_new = dict(point, feasible=chosen["status"] == "certified",
                            bound=verdict["global_bound"] if verdict else None,
                            status=chosen["status"], attempts=attempts)
        if new != expected_new:
            raise ValueError("fresh row selection/bound changed")
        fresh.append(new)
    totals = {"case_id": model["case_id"], "target": "1", "points": len(points),
              "frozen_selected": selected(frozen), "refreshed_selected": selected(fresh),
              "newly_certified": sum(not a["feasible"] and b["feasible"] for a, b in zip(frozen, fresh)),
              "lost_certifications": sum(a["feasible"] and not b["feasible"] for a, b in zip(frozen, fresh)),
              "numerical_or_checker_errors": errors, "complete_catalog_visited": True,
              "frozen_rechecked": False}
    if any(comparison.get(key) != value for key, value in totals.items()):
        raise ValueError("changed comparison totals/selection")
    kinds = call_kinds(rows)
    if len(kinds) > 2 * len(points) + 2:
        raise ValueError("numerical call budget exceeded")
    return {"case_id": model["case_id"], "points": len(points),
            "exact_checker_calls": checked, "numerical_calls": len(kinds),
            "errors_retained": errors, "full_verdicts_reconciled": True}


def reconcile_files(folder, comparison):
    rows = comparison["rows"]
    point_paths = sorted(folder.glob("point-*.json"))
    if ([p.name for p in point_paths] != ["point-%03d.json" % i for i in range(len(rows))]
            or [json.loads(p.read_text()) for p in point_paths] != rows):
        raise ValueError("partial or changed point records")
    event_paths = sorted(folder.glob("call-*.json"))
    kinds = call_kinds(rows)
    expected_events = [{"index": i, "kind": kind} for i, kind in enumerate(kinds)]
    if ([p.name for p in event_paths] != ["call-%03d.json" % i for i in range(len(kinds))]
            or [json.loads(p.read_text()) for p in event_paths] != expected_events):
        raise ValueError("partial or changed call records")
    return len(kinds)


def reconcile_directory(root, output):
    root, output = Path(root), Path(output)
    numerical = json.loads((output / "summary.json").read_text())
    if [r["case_id"] for r in numerical["outcomes"]] != list(CASE_IDS):
        raise ValueError("changed numerical cohort")
    records = []
    families = ("shared-prefix", "staggered-bank", "fork-join", "pipeline")
    for case, family, outcome in zip(CASE_IDS, families, numerical["outcomes"]):
        folder = output / case
        model = json.loads((root / "inputs" / (case + ".json")).read_text())
        if (model.get("case_id"), model.get("family"), model.get("clients"), model.get("seed")) != (case, family, 8, 1):
            raise ValueError("changed structural cohort")
        certificate = json.loads((root / "results/models" / (case + ".json")).read_text())["certificate"]
        retained = json.loads((root / "results/allocation" / (case + ".json")).read_text())
        comparison = json.loads((folder / "comparison.json").read_text())
        recorded_calls = reconcile_files(folder, comparison)
        expected_outcome = {"case_id": case, "status": "completed", "returncode": 0,
                            "expected_points": len(catalog(model)), "retained_point_records": len(comparison["rows"]),
                            "comparison_present": True, "recorded_calls": recorded_calls}
        if outcome != expected_outcome:
            raise ValueError("failed or changed numerical outcome")
        records.append(reconcile_record(model, certificate, retained, comparison))
    checks = sum(r["exact_checker_calls"] for r in records)
    calls = sum(r["numerical_calls"] for r in records)
    if ([r["points"] for r in records] != [16, 16, 16, 64] or checks > 256 or calls > 256
            or sum(r["errors_retained"] for r in records)
            or numerical.get("numerical_arm_complete_without_errors") is not True
            or numerical.get("expected_points") != 112
            or numerical.get("recorded_calls") != calls):
        raise ValueError("incomplete, failed or over-budget numerical arm")
    return {"scientific_fields_reconciled": True, "points": 112,
            "exact_checker_calls": checks, "numerical_construct_check_calls": calls,
            "records": records,
            "scope": "same finite catalog only; no continuous optimum, hardware or timing claim"}
