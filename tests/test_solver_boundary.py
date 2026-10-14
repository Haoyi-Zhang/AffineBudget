"""Owned dependency and optimized-mode controls, not an external solver test."""
import builtins
import unittest
from unittest.mock import patch

from simcert.producer import optimize_mixture, make_certificate
from simcert.checker import check
from fractions import Fraction as Q


class SolverBoundaryTests(unittest.TestCase):
    def numerical_import_forbidden(self, name, *args, **kwargs):
        if name.split('.')[0] in ('numpy', 'scipy'):
            raise AssertionError('unneeded numerical dependency imported')
        return self.original_import(name, *args, **kwargs)

    def test_single_right_form_uses_its_unique_exact_weight(self):
        self.original_import = builtins.__import__
        with patch('builtins.__import__', side_effect=self.numerical_import_forbidden):
            self.assertEqual(optimize_mixture((Q(3), Q(1)), [(Q(4), Q(2))], [Q(1)]), [Q(1)])

    def test_constant_model_native_production_needs_no_solver(self):
        model = {'domain': ['1'], 'jobs': [{'id': 0, 'resource': 'r', 'deps': [],
                  'release': ['0', '0'], 'service': ['1', '0']}]}
        self.original_import = builtins.__import__
        with patch('builtins.__import__', side_effect=self.numerical_import_forbidden):
            cert = make_certificate(model, ['1'])
        self.assertTrue(check(model, cert, '0')['certified'])
        self.assertEqual(cert['lower_weights'], ['1'])


if __name__ == '__main__':
    unittest.main()
