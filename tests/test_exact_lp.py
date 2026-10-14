"""Bounded exact LP controls and a same-information ordinary LP reference."""
import copy
from fractions import Fraction as Q
import unittest

from simcert.algebra import exact_small_oracle, same_data
from simcert.cases import shared_prefix
from simcert.checker import check
from simcert.exact_lp import (solve_square, solve_comparison, verify_optimum,
                             primal_vertex_reference, make_exact_certificate,
                             direct_primal_verdict, verify_exact_evidence)


class ExactLPTests(unittest.TestCase):
    def test_rational_elimination_and_singular_bases(self):
        self.assertEqual(solve_square([[2, 0], [0, 3]], [1, 1]), (Q(1, 2), Q(1, 3)))
        self.assertIsNone(solve_square([[1, 1], [2, 2]], [0, 0]))
        with self.assertRaises(ValueError):
            solve_square([[1]], [1, 2])

    def test_interior_optimum_and_primal_dual_gap(self):
        p, qs, b = (Q(3, 4), Q(0)), [(Q(0), Q(1)), (Q(0), Q(-1))], [Q(1)]
        proof, _ = solve_comparison(p, qs, b)
        reference, _ = primal_vertex_reference(p, qs, b)
        self.assertEqual(verify_optimum(p, qs, b, proof), Q(3, 4))
        self.assertEqual(proof['point'], ['0'])
        self.assertEqual(proof['value'], reference['value'])
        changed = copy.deepcopy(proof)
        changed['value'] = '0'
        with self.assertRaisesRegex(ValueError, 'gap'):
            verify_optimum(p, qs, b, changed)

    def test_shared_terms_and_nonnegative_coefficients(self):
        p = (Q(3), Q(1), Q(1))
        qs = [(Q(13, 4), Q(2), Q(0)), (Q(13, 4), Q(0), Q(2))]
        proof, _ = solve_comparison(p, qs, [Q(1), Q(1)])
        reference, _ = primal_vertex_reference(p, qs, [Q(1), Q(1)])
        self.assertEqual(proof['value'], '-1/4')
        self.assertEqual(reference['value'], '-1/4')
        self.assertEqual(proof['weights'], ['1/2', '1/2'])

    def test_zero_and_mixed_radius_degeneracy(self):
        p = (Q(4), Q(0), Q(0))
        qs = [(Q(4), Q(1), Q(1)), (Q(4), Q(-1), Q(-1))]
        for b in ([Q(0), Q(0)], [Q(0), Q(1)], [Q(1), Q(0)]):
            proof, _ = solve_comparison(p, qs, b)
            reference, _ = primal_vertex_reference(p, qs, b)
            self.assertEqual(verify_optimum(p, qs, b, proof), Q(0))
            self.assertEqual(reference['value'], proof['value'])

    def test_missing_mass_and_outside_primal_point_refuse(self):
        p, qs, b = (Q(0), Q(0)), [(Q(0), Q(1)), (Q(0), Q(-1))], [Q(1)]
        proof, _ = solve_comparison(p, qs, b)
        for key, altered in (('weights', ['0', '0']), ('point', ['2']), ('weights', [False, '1'])):
            bad = copy.deepcopy(proof)
            bad[key] = altered
            with self.assertRaises(ValueError):
                verify_optimum(p, qs, b, bad)

    def test_caps_refuse_without_partial_optimum(self):
        p, qs, b = (Q(0), Q(3)), [(Q(0), Q(1)), (Q(0), Q(-1))], [Q(1)]
        for solve in (solve_comparison, primal_vertex_reference):
            with self.assertRaises(OverflowError):
                solve(p, qs, b, max_bases=1)
            with self.assertRaises(ValueError):
                solve(p, qs, b, max_bases=True)
        with self.assertRaises(ValueError):
            solve_comparison([0] * 5, [[0] * 5], [1] * 4)
        with self.assertRaises(ValueError):
            solve_comparison(p, qs * 7, b)

    def test_full_contract_same_information_reference(self):
        model = shared_prefix(2, 1)
        cert, evidence = make_exact_certificate(model, ['1', '1'])
        actual = check(model, cert)
        reference, _ = direct_primal_verdict(model, ['1', '1'])
        self.assertTrue(actual['certified'])
        self.assertTrue(same_data({key: actual[key] for key in reference}, reference))
        self.assertGreater(len(evidence['comparison_work']), 0)

    def test_small_arrangement_reference_agrees(self):
        for p in ((Q(0), Q(0)), (Q(1), Q(-1)), (Q(2), Q(1))):
            for qs in ([(Q(0), Q(1)), (Q(0), Q(-1))],
                       [(Q(1), Q(0)), (Q(2), Q(1))]):
                proof, _ = solve_comparison(p, qs, [Q(1)])
                (optimum, _), _ = exact_small_oracle([p], qs, [Q(1)])
                self.assertEqual(verify_optimum(p, qs, [Q(1)], proof), optimum)

    def test_exact_evidence_reconstructs_every_guard_and_sink(self):
        model = shared_prefix(2, 1)
        cert, evidence = make_exact_certificate(model, ['1', '1'])
        self.assertTrue(verify_exact_evidence(model, cert, evidence)['all_comparisons_exact'])
        for kind in ('missing', 'typed_index', 'sink_gap', 'weights'):
            changed = copy.deepcopy(evidence)
            if kind == 'missing':
                changed['guard_optima'].pop()
            elif kind == 'typed_index':
                changed['guard_optima'][0]['guard_index'] = False
            elif kind == 'sink_gap':
                changed['sink_optimum']['value'] = '100'
            else:
                changed['guard_optima'][0]['proof']['weights'] = ['1', '0']
            with self.assertRaises(ValueError):
                verify_exact_evidence(model, cert, changed)


if __name__ == '__main__':
    unittest.main()
