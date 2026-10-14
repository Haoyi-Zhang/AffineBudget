"""Benign internal counter-observation controls must survive Python -O."""
import unittest
from unittest.mock import patch

from boundary_check import evaluate as boundary
from reduction_check import evaluate as reduction


class OptimizedGuardTests(unittest.TestCase):
    def test_contradictory_order_control_verdict_is_not_published(self):
        with patch('boundary_check.check', return_value={'order_certified': True, 'global_bound': '0'}):
            with self.assertRaises(AssertionError):
                boundary()

    def test_non_boolean_internal_reduction_point_is_not_reported_as_valid(self):
        # A test-local enumeration double, not a third-party input or SAT exploit.
        with patch('reduction_check.itertools.product', return_value=[(0, 0, 0)]):
            with self.assertRaises(AssertionError):
                reduction(3, [])


if __name__ == '__main__':
    unittest.main()
