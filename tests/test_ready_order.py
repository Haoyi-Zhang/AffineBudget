"""Portable finite ready-set checks; no producer, private tree, or timing job."""
import copy
import json
import unittest
from fractions import Fraction as Q
from pathlib import Path

from simcert.checker import check
from simcert.model import graph_for, prepare, simulate

ROOT = Path(__file__).resolve().parents[1]


def reference_order(incoming):
    """Scan all unplaced vertices for the smallest eligible vertex.

    No ready queue or mutable indegrees. This independently specifies traversal
    ordering, not the model or envelope semantics.
    """
    placed = set()
    answer = []
    while len(placed) < len(incoming):
        eligible = [v for v, edges in incoming.items() if v not in placed
                    and all(u in placed for u, _ in edges)]
        if not eligible:
            raise ValueError("cyclic reference graph")
        v = min(eligible)
        answer.append(v)
        placed.add(v)
    return answer


def constant_job(i, resource, deps=(), k=1):
    return {"id": i, "resource": resource, "deps": list(deps),
            "release": ["0"] * (k + 1), "service": ["1"] + ["0"] * k}


class ReadyOrderTests(unittest.TestCase):
    def assert_reference(self, model, orders=None):
        orders = simulate(model, [0] * len(model["domain"]))["orders"] if orders is None else orders
        domain, topo, incoming, guards, edges = graph_for(model, orders)
        self.assertEqual(topo, reference_order(incoming))
        self.assertEqual(len(topo), 2 * len(model["jobs"]) + 2)
        self.assertEqual(edges, sum(map(len, incoming.values())))
        expected = [{"left": f"a{i}", "right": f"a{j}", "strict": i > j, "jobs": [i, j]}
                    for _, seq in sorted(orders.items()) for i, j in zip(seq, seq[1:])]
        self.assertEqual(guards, expected)
        self.assertEqual(domain, tuple(map(Q, model["domain"])))
        return topo

    def test_all_retained_graphs_and_certificates(self):
        files = sorted((ROOT / "inputs").glob("*.json"))
        self.assertEqual(len(files), 54)
        for path in files:
            with self.subTest(input=path.name):
                model = json.loads(path.read_text())
                self.assert_reference(model)
                group = "structure" if path.stem.startswith("join-") else "models"
                record = json.loads((ROOT / "results" / group / path.name).read_text())
                self.assertEqual(check(model, record["certificate"]), record["verdict"])

    def test_lexical_vertices_not_integer_dispatch_ids(self):
        model = {"domain": ["1"], "jobs": [constant_job(10, "r"), constant_job(2, "r")]}
        self.assertEqual(self.assert_reference(model), ["s", "a10", "a2", "c2", "c10", "m"])
        nominal, fs, guards, stats = prepare(model)
        self.assertEqual(list(fs), ["s", "a10", "a2", "c2", "c10", "m"])
        self.assertEqual(nominal["orders"], {"r": [2, 10]})
        cert = {"radii": ["1"], "orders": nominal["orders"],
                "guards": [{"guard": guards[0], "weights": [["1"]]}], "lower_weights": ["1"]}
        self.assertTrue(check(model, cert)["certified"])
        self.assertEqual(stats, {"vertices": 6, "edges": 7, "max_frontier": 1, "total_forms": 6})

    def test_ready_insertions_negative_ids_and_join(self):
        model = {"domain": ["0"] * 8, "jobs": [constant_job(-3, "z", k=8),
                 constant_job(10, "a", (-3,), 8), constant_job(2, "b", (-3,), 8),
                 constant_job(100, "z", (10, 2), 8)]}
        self.assert_reference(model)

    def test_maximum_job_boundary(self):
        model = {"domain": ["0"], "jobs": [constant_job(i, f"r{i}") for i in range(512)]}
        self.assert_reference(model)
        model["jobs"].append(constant_job(512, "r512"))
        with self.assertRaisesRegex(ValueError, "job count"):
            graph_for(model, {f"r{i}": [i] for i in range(513)})

    def test_resource_cycle_and_incomplete_order_refuse(self):
        model = {"domain": ["1"], "jobs": [constant_job(2, "r"), constant_job(10, "r", (2,))]}
        with self.assertRaisesRegex(ValueError, "cyclic or disconnected"):
            graph_for(model, {"r": [10, 2]})
        for orders in ({"r": [2]}, {"r": [2, 2]}, {"wrong": [2, 10]}, {"r": [2, 99]}):
            with self.subTest(orders=orders), self.assertRaises(ValueError):
                graph_for(model, orders)

    def test_constant_makespan_order_switch_remains_refused(self):
        model = {"domain": ["1"], "jobs": [constant_job(0, "bank"),
                 constant_job(1, "bank"), constant_job(2, "bank")]}
        model["jobs"][0]["service"][0] = "3"
        model["jobs"][1]["release"] = ["1", "0"]
        model["jobs"][2]["release"] = ["1", "1/2"]
        nominal, fs, guards, _ = prepare(model)
        cert = {"radii": ["1"], "orders": nominal["orders"],
                "guards": [{"guard": g, "weights": [["1"]]} for g in guards], "lower_weights": ["1"]}
        verdict = check(model, cert)
        self.assertFalse(verdict["order_certified"])
        self.assertEqual(verdict["global_bound"], "0")
        self.assertEqual(verdict["guard_bounds"], ["-1", "1/2"])
        for x, order in ((-1, [0, 2, 1]), (0, [0, 1, 2]), (1, [0, 1, 2])):
            actual = simulate(model, [x])
            self.assertEqual(actual["makespan"], Q(5))
            self.assertEqual(actual["orders"]["bank"], order)
        smaller = copy.deepcopy(cert)
        smaller["radii"] = ["0"]
        self.assertTrue(check(model, smaller)["certified"])


if __name__ == "__main__":
    unittest.main()
