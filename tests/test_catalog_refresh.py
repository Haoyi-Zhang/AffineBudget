"""Portable finite checks; no numerical solver, timing job or private paths."""
import copy
import itertools
import json
import os
from fractions import Fraction as Q
from pathlib import Path
import tempfile
import unittest

from simcert.catalog_refresh import (CASE_IDS, catalog, compare_catalog, frozen_row,
                                    nominal_onehot, refreshed_row, selected)
from simcert.checker import check

ROOT = Path(__file__).resolve().parents[1]


def nominal_reference(model):
    """Literal earliest-start scan; no event heap, envelope or project evaluator."""
    pending = {j["id"]: j for j in model["jobs"]}
    finish, free, orders = {}, {}, {}
    while pending:
        candidates = []
        for i, job in pending.items():
            if all(p in finish for p in job["deps"]):
                arrival = max([Q(job["release"][0])] + [finish[p] for p in job["deps"]])
                start = max(arrival, free.get(job["resource"], Q(0)))
                candidates.append((start, arrival, i))
        if not candidates:
            raise ValueError("reference dependency cycle")
        start, _, i = min(candidates)
        job = pending.pop(i)
        finish[i] = start + Q(job["service"][0])
        free[job["resource"]] = finish[i]
        orders.setdefault(job["resource"], []).append(i)
    return max(finish.values()), orders


def constant_case(domain=("1",)):
    k = len(domain)
    model = {"case_id": "constant", "domain": list(domain),
             "jobs": [{"id": 0, "resource": "r", "deps": [],
                       "release": ["0"] * (k + 1), "service": ["1"] + ["0"] * k}]}
    cert = {"radii": list(domain), "orders": {"r": [0]}, "guards": [], "lower_weights": ["1"]}
    return model, cert


def constant_retained():
    model, cert = constant_case()
    rows = [{"indices": [i], "radii": [r], "score": i, "feasible": True, "bound": "0"}
            for i, r in enumerate(("0", "1/4", "1/2", "1"))]
    retained = {"case_id": "constant", "target": "1", "objective": "sum((dimension+1)*level_index)",
                "restriction": "frozen maximum-domain witnesses and finite catalog only",
                "selected": rows[-1], "candidates": rows}
    return model, cert, retained


class RefreshCatalogTests(unittest.TestCase):
    def test_all_112_frozen_rows_and_original_tie_break(self):
        total = 0
        for case in CASE_IDS:
            model = json.loads((ROOT / "inputs" / (case + ".json")).read_text())
            cert = json.loads((ROOT / "results/models" / (case + ".json")).read_text())["certificate"]
            old = json.loads((ROOT / "results/allocation" / (case + ".json")).read_text())
            # Declarative index-grid reference; keeps original indices after filtering.
            levels = ["0", "1/4", "1/2", "1"]
            expected = [{"indices": list(index), "radii": [levels[i] for i in index],
                         "score": sum(h * i for h, i in enumerate(index, 1))}
                        for index in itertools.product(range(4), repeat=len(model["domain"]))
                        if all(Q(levels[i]) <= Q(d) for i, d in zip(index, model["domain"]))]
            self.assertEqual(catalog(model), expected)
            rows = [frozen_row(model, cert, point, old["target"]) for point in expected]
            self.assertEqual(rows, old["candidates"])
            feasible = [row for row in rows if row["feasible"]]
            reference = sorted(feasible, key=lambda r: (r["score"], r["indices"]))[-1] if feasible else None
            self.assertEqual(selected(rows), reference)
            self.assertEqual(reference, old["selected"])
            total += len(rows)
        self.assertEqual(total, 112)

    def test_four_zero_certificates_and_independent_nominal_schedule(self):
        for case in CASE_IDS:
            model = json.loads((ROOT / "inputs" / (case + ".json")).read_text())
            snapshot = copy.deepcopy(model)
            cert = nominal_onehot(model, ["0"] * len(model["domain"]))
            verdict = check(model, cert, "1")
            c0, orders = nominal_reference(model)
            self.assertTrue(verdict["certified"])
            self.assertEqual(verdict["global_bound"], "0")
            self.assertEqual(verdict["nominal_makespan"], str(c0))
            self.assertEqual(cert["orders"], orders)
            self.assertEqual(model, snapshot)

    def test_fallback_is_zero_only_and_guard_coverage_is_not_bypassed(self):
        model = {"domain": ["1"], "jobs": [
            {"id": 1, "resource": "r", "deps": [], "release": ["2", "0"], "service": ["1", "0"]},
            {"id": 2, "resource": "r", "deps": [], "release": ["3/2", "1/2"], "service": ["1", "0"]}]}
        cert = nominal_onehot(model, ["0"])
        self.assertTrue(cert["guards"][0]["guard"]["strict"])
        self.assertTrue(check(model, cert, "1")["certified"])
        for radii in (["1/4"], ["-1"], [], ["0", "0"]):
            with self.assertRaises(ValueError):
                nominal_onehot(model, radii)
        cert["guards"][0]["guard"]["strict"] = False
        with self.assertRaisesRegex(ValueError, "wrong guard"):
            check(model, cert, "1")

    def test_order_refusal_survives_constant_makespan(self):
        model = {"domain": ["1"], "jobs": [
            {"id": 0, "resource": "r", "deps": [], "release": ["0", "0"], "service": ["3", "0"]},
            {"id": 1, "resource": "r", "deps": [], "release": ["1", "0"], "service": ["1", "0"]},
            {"id": 2, "resource": "r", "deps": [], "release": ["1", "1/2"], "service": ["1", "0"]}]}
        cert = nominal_onehot(model, ["0"])
        cert["radii"] = ["1"]
        row = refreshed_row(model, {"indices": [3], "radii": ["1"], "score": 3},
                            "1", lambda m, b: copy.deepcopy(cert))
        self.assertFalse(row["feasible"])
        self.assertEqual(row["status"], "refused")
        self.assertEqual(row["bound"], "0")
        self.assertFalse(row["attempts"][0]["verdict"]["order_certified"])
        self.assertEqual(len(row["attempts"]), 1)

    def test_error_retained_when_zero_fallback_accepts(self):
        model = json.loads((ROOT / "inputs/case-043.json").read_text())
        def unavailable(m, b):
            raise RuntimeError("test-local numerical proposal failure")
        row = refreshed_row(model, catalog(model)[0], "1", unavailable)
        self.assertTrue(row["feasible"])
        self.assertEqual(row["bound"], "0")
        self.assertEqual([a["status"] for a in row["attempts"]], ["producer_error", "certified"])
        self.assertEqual(row["attempts"][1]["policy"], "zero-only-nominal-onehot")

    def test_fresh_loss_is_not_hidden_by_frozen_union(self):
        model, cert = constant_case()
        rows = [{"indices": [i], "radii": [r], "score": i, "feasible": True, "bound": "0"}
                for i, r in enumerate(("0", "1/4", "1/2", "1"))]
        retained = {"case_id": "constant", "target": "1", "objective": "sum((dimension+1)*level_index)",
                    "restriction": "frozen maximum-domain witnesses and finite catalog only",
                    "selected": rows[-1], "candidates": rows}
        def propose(m, b):
            c = copy.deepcopy(cert)
            c["radii"] = list(b)
            if b == ["1"]:
                c["lower_weights"] = ["0"]
            return c
        result = compare_catalog(model, cert, retained, propose)
        self.assertEqual(result["lost_certifications"], 1)
        self.assertEqual(result["numerical_or_checker_errors"], 1)
        self.assertEqual(result["frozen_selected"]["indices"], [3])
        self.assertEqual(result["refreshed_selected"]["indices"], [2])
        self.assertEqual(result["rows"][-1]["refreshed"]["status"], "checker_error")

    def test_domain_filter_caps_and_no_resealing(self):
        for domain, count, last in ((["0"], 1, [0]), (["1/2"], 3, [2]),
                                    (["0", "1/2", "1"], 12, [0, 2, 3])):
            model, cert = constant_case(domain)
            points = catalog(model)
            self.assertEqual(len(points), count)
            self.assertEqual(points[-1]["indices"], last)
        with self.assertRaises(ValueError):
            catalog(constant_case(["1"] * 4)[0])
        model, cert = constant_case()
        with self.assertRaisesRegex(ValueError, "no resealing"):
            compare_catalog(model, cert, {"target": "1"})
        with self.assertRaisesRegex(ValueError, "target one"):
            compare_catalog(model, cert, {"target": "2"})

    def test_output_is_exclusive_and_unsupported_caps_are_explicit(self):
        from refresh_allocation import exclusive, caps
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "receipt.json"
            exclusive(path, {"negative": "retained"})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                exclusive(path, {"negative": "erased"})
            self.assertEqual(path.read_bytes(), before)
        if os.name != "posix":
            with self.assertRaisesRegex(SystemExit, "no uncapped fallback"):
                caps()

    def test_delivered_zero_records_are_current_exact_artifacts(self):
        data = json.loads((ROOT / "results/refreshed-zero/zero-certificates.json").read_text())
        summary = json.loads((ROOT / "results/refreshed-zero/summary.json").read_text())
        self.assertEqual(data["case_ids"], list(CASE_IDS))
        self.assertEqual(data["target"], "1")
        self.assertEqual([r["case_id"] for r in data["records"]], list(CASE_IDS))
        self.assertEqual(summary["case_ids"], list(CASE_IDS))
        self.assertEqual(summary["target"], "1")
        self.assertFalse(summary["numerical_refreshed_catalog_executed"])
        self.assertEqual(summary["nonzero_refreshed_points_executed"], 0)
        self.assertEqual(summary["frozen_rows_rechecked"], 112)
        self.assertEqual(summary["zero_certificates_rechecked"], 4)
        self.assertEqual([r["case_id"] for r in summary["records"]], list(CASE_IDS))
        for record, row in zip(data["records"], summary["records"]):
            model = json.loads((ROOT / "inputs" / (record["case_id"] + ".json")).read_text())
            old = json.loads((ROOT / "results/allocation" / (record["case_id"] + ".json")).read_text())
            certificate = nominal_onehot(model, ["0"] * len(model["domain"]))
            self.assertEqual(certificate, record["certificate"])
            self.assertEqual(check(model, certificate, "1"), record["verdict"])
            nominal, orders = nominal_reference(model)
            self.assertEqual(record["reference_nominal_makespan"], str(nominal))
            self.assertEqual(record["reference_orders"], orders)
            self.assertEqual(row["frozen_points"], len(old["candidates"]))
            self.assertEqual(row["frozen_feasible"], sum(r["feasible"] for r in old["candidates"]))
            self.assertEqual(row["frozen_selected"], old["selected"])
            self.assertEqual(row["frozen_zero_bound"], old["candidates"][0]["bound"])
            self.assertEqual(row["nominal_onehot_certified"], record["verdict"]["certified"])
            self.assertEqual(row["nominal_onehot_bound"], record["verdict"]["global_bound"])
            self.assertEqual(row["independent_nominal_makespan"], str(nominal))
            self.assertEqual(row["nominal_guard_records"], len(certificate["guards"]))

    def test_predeclared_structural_cohort_cannot_be_reselected(self):
        from refresh_allocation import cohort_counts
        models = [json.loads((ROOT / "inputs" / (case + ".json")).read_text()) for case in CASE_IDS]
        self.assertEqual(list(cohort_counts(models).values()), [16, 16, 16, 64])
        for change in ("seed", "clients", "family", "case_id"):
            altered = copy.deepcopy(models)
            altered[0][change] = "different"
            with self.assertRaisesRegex(ValueError, "structural selection"):
                cohort_counts(altered)
        with self.assertRaises(ValueError):
            cohort_counts(models[:-1])

    def test_native_call_accounting_and_portable_full_verdict_consumer(self):
        from simcert.catalog_reconcile import call_kinds, reconcile_record
        model, cert, retained = constant_retained()
        calls = []
        def propose(m, b):
            current = copy.deepcopy(cert)
            current["radii"] = list(b)
            return current
        result = compare_catalog(model, cert, retained, propose, recheck_frozen=False,
                                 call_event=calls.append)
        self.assertFalse(result["frozen_rechecked"])
        self.assertEqual(calls, ["existing-numerical-producer", "exact-checker"] * 4)
        self.assertEqual(calls, call_kinds(result["rows"]))
        receipt = reconcile_record(model, cert, retained, result)
        self.assertEqual(receipt["exact_checker_calls"], 8)
        self.assertEqual(receipt["numerical_calls"], 8)
        self.assertEqual(receipt["errors_retained"], 0)
        for field in ("verdict", "selected", "coverage"):
            changed = copy.deepcopy(result)
            if field == "verdict":
                changed["rows"][-1]["refreshed"]["attempts"][0]["verdict"]["global_bound"] = "1"
            elif field == "selected":
                changed["refreshed_selected"] = None
            else:
                changed["rows"].pop()
            with self.assertRaises(ValueError):
                reconcile_record(model, cert, retained, changed)
        # A valid certificate for a smaller box cannot certify this requested point.
        smaller = copy.deepcopy(cert)
        smaller["radii"] = ["0"]
        wrong = refreshed_row(model, catalog(model)[1], "1", lambda m, b: copy.deepcopy(smaller))
        self.assertEqual(wrong["status"], "checker_error")
        self.assertEqual(wrong["attempts"][0]["error"], "proposal radii differ from catalog point")

    def test_exclusive_per_call_budget_stops_before_next_operation(self):
        from refresh_allocation import count_call
        counts = {"existing-numerical-producer": 0, "zero-only-nominal-onehot": 0, "exact-checker": 0}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            count_call(folder, counts, 2, "existing-numerical-producer")
            count_call(folder, counts, 2, "exact-checker")
            with self.assertRaisesRegex(RuntimeError, "budget exhausted"):
                count_call(folder, counts, 2, "existing-numerical-producer")
            self.assertEqual(sum(counts.values()), 2)
            self.assertEqual([p.name for p in sorted(folder.glob("call-*.json"))],
                             ["call-000.json", "call-001.json"])
            self.assertEqual(json.loads((folder / "call-001.json").read_text()),
                             {"index": 1, "kind": "exact-checker"})
        self.assertEqual(sum(2 * n + 2 for n in (16, 16, 16, 64)), 232)

    def test_public_point_and_call_files_reject_partial_receipts(self):
        from refresh_allocation import exclusive
        from simcert.catalog_reconcile import call_kinds, reconcile_files
        model, cert, retained = constant_retained()
        def propose(m, b):
            current = copy.deepcopy(cert)
            current["radii"] = list(b)
            return current
        result = compare_catalog(model, cert, retained, propose, recheck_frozen=False)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for i, row in enumerate(result["rows"]):
                exclusive(folder / ("point-%03d.json" % i), row)
            for i, kind in enumerate(call_kinds(result["rows"])):
                exclusive(folder / ("call-%03d.json" % i), {"index": i, "kind": kind})
            self.assertEqual(reconcile_files(folder, result), 8)
            # Separate fresh fixtures, no deletion or overwrite of an existing receipt.
            with tempfile.TemporaryDirectory() as partial:
                incomplete = Path(partial)
                for i, row in enumerate(result["rows"][:-1]):
                    exclusive(incomplete / ("point-%03d.json" % i), row)
                with self.assertRaisesRegex(ValueError, "point records"):
                    reconcile_files(incomplete, result)
            with tempfile.TemporaryDirectory() as partial:
                incomplete = Path(partial)
                for i, row in enumerate(result["rows"]):
                    exclusive(incomplete / ("point-%03d.json" % i), row)
                for i, kind in enumerate(call_kinds(result["rows"])[:-1]):
                    exclusive(incomplete / ("call-%03d.json" % i), {"index": i, "kind": kind})
                with self.assertRaisesRegex(ValueError, "call records"):
                    reconcile_files(incomplete, result)


if __name__ == "__main__":
    unittest.main()
