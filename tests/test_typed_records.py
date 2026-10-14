"""Owned metadata/type controls. No solver, external process or target access."""
import copy
import unittest

from simcert.checker import check
from simcert.model import graph_for, validate
from simcert.catalog_refresh import compare_catalog
from simcert.catalog_reconcile import reconcile_record


def constant_case(two=False):
    jobs = [{"id": 0, "resource": "r", "deps": [],
             "release": ["0", "0"], "service": ["1", "0"]}]
    if two:
        jobs.append({"id": 1, "resource": "r", "deps": [0],
                     "release": ["0", "0"], "service": ["1", "0"]})
    model = {"case_id": "owned-type-control", "domain": ["1"], "jobs": jobs}
    guard = {"left": "a0", "right": "a1", "strict": False, "jobs": [0, 1]}
    certificate = {"radii": ["1"], "orders": {"r": [0, 1] if two else [0]},
                   "guards": [{"guard": guard, "weights": [["1"]]}] if two else [],
                   "lower_weights": ["1"]}
    return model, certificate


def reconciled_constant():
    model, certificate = constant_case()
    rows = [{"indices": [i], "radii": [r], "score": i, "feasible": True, "bound": "0"}
            for i, r in enumerate(("0", "1/4", "1/2", "1"))]
    retained = {"case_id": model["case_id"], "target": "1",
                "objective": "sum((dimension+1)*level_index)",
                "restriction": "frozen maximum-domain witnesses and finite catalog only",
                "selected": rows[-1], "candidates": rows}
    def propose(_model, radii):
        cert = copy.deepcopy(certificate)
        cert["radii"] = list(radii)
        return cert
    comparison = compare_catalog(model, certificate, retained, propose, recheck_frozen=False)
    return model, certificate, retained, comparison


class TypedRecordTests(unittest.TestCase):
    def test_legitimate_integer_records_still_pass(self):
        for two in (False, True):
            model, cert = constant_case(two)
            self.assertTrue(check(model, cert)["certified"])
        self.assertTrue(reconcile_record(*reconciled_constant())["full_verdicts_reconciled"])

    def test_dependency_bool_id_is_rejected_before_evaluation(self):
        model, _ = constant_case(True)
        model["jobs"][1]["deps"] = [False]
        with self.assertRaises(ValueError):
            validate(model)

    def test_dependency_float_id_is_rejected_before_evaluation(self):
        model, _ = constant_case(True)
        model["jobs"][1]["deps"] = [0.0]
        with self.assertRaises(ValueError):
            validate(model)

    def test_certificate_bool_order_id_is_rejected(self):
        model, cert = constant_case()
        cert["orders"]["r"] = [False]
        with self.assertRaises(ValueError):
            check(model, cert)

    def test_certificate_float_order_id_is_rejected(self):
        model, cert = constant_case()
        cert["orders"]["r"] = [0.0]
        with self.assertRaises(ValueError):
            check(model, cert)

    def test_guard_bool_job_id_is_rejected(self):
        model, cert = constant_case(True)
        cert["guards"][0]["guard"]["jobs"][0] = False
        with self.assertRaises(ValueError):
            check(model, cert)

    def test_guard_float_strictness_is_rejected(self):
        model, cert = constant_case(True)
        cert["guards"][0]["guard"]["strict"] = 0.0
        with self.assertRaises(ValueError):
            check(model, cert)

    def test_direct_graph_order_bool_id_is_rejected_as_admission(self):
        model, _ = constant_case()
        with self.assertRaises(ValueError):
            graph_for(model, {"r": [False]})

    def test_refreshed_index_bool_substitution_is_rejected(self):
        args = list(reconciled_constant())
        args[-1]["rows"][0]["refreshed"]["indices"][0] = False
        with self.assertRaises(ValueError):
            reconcile_record(*args)

    def test_refreshed_verdict_float_statistic_is_rejected(self):
        args = list(reconciled_constant())
        stats = args[-1]["rows"][0]["refreshed"]["attempts"][0]["verdict"]["stats"]
        stats["vertices"] = float(stats["vertices"])
        with self.assertRaises(ValueError):
            reconcile_record(*args)


if __name__ == "__main__":
    unittest.main()
