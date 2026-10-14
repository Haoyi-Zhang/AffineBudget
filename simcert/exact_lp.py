"""Bounded rational LP production and ordinary primal-vertex reference.

Standard active-constraint linear algebra, not a new optimizer or duality.
Both arms use identical complete envelopes. Search limits refuse, never truncate.
No NumPy/SciPy, external process, or cached historical optimum is used.
"""
from fractions import Fraction as Q
from itertools import combinations
from math import comb
import time

from .algebra import form, rational, value, envelope, mixture_bound, upper, sub, same_data
from .model import prepare, validate

MAX_DIMENSION = 3
MAX_RIGHT_FORMS = 12
MAX_BASES = 4096


def solve_square(matrix, rhs):
    """Exact Gauss-Jordan solve; singular bases return None, not an optimum."""
    n = len(rhs)
    if len(matrix) != n or any(len(row) != n for row in matrix):
        raise ValueError('square system required')
    a = [[rational(x) for x in row] + [rational(rhs[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = next((row for row in range(col, n) if a[row][col]), None)
        if pivot is None:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        divisor = a[col][col]
        a[col] = [x / divisor for x in a[col]]
        for row in range(n):
            if row != col and a[row][col]:
                multiple = a[row][col]
                a[row] = [x - multiple * y for x, y in zip(a[row], a[col])]
    return tuple(row[-1] for row in a)


def problem(p, qs, b):
    b = tuple(rational(x) for x in b)
    k = len(b)
    if not 1 <= k <= MAX_DIMENSION or any(x < 0 for x in b):
        raise ValueError('exact LP requires a nonnegative one-to-three-dimensional box')
    if not 1 <= len(qs) <= MAX_RIGHT_FORMS:
        raise ValueError('exact LP right frontier outside bounded interface')
    p = form(p, k)
    qs = tuple(form(q, k) for q in qs)
    rows = [q[1:] + (Q(-1),) for q in qs]
    rhs = [-q[0] for q in qs]
    for h, radius in enumerate(b):
        row = [Q(0)] * (k + 1)
        row[h] = Q(1)
        rows.extend((tuple(row), tuple(-x for x in row)))
        rhs.extend((radius, radius))
    return p, qs, b, tuple(rows), tuple(rhs), p[1:] + (Q(-1),)


def product_sum(row, point):
    return sum((a * x for a, x in zip(row, point)), Q(0))


def verify_optimum(p, qs, b, proof):
    """Feasible primal point plus equal exact mixture bound proves optimality.

    This consumer runs no basis search and does not trust a solver success flag.
    Rational input/witness budgets and every simplex constraint remain active.
    """
    p, qs, b, _, _, _ = problem(p, qs, b)
    point = tuple(rational(x) for x in proof['point'])
    if len(point) != len(b) or any(abs(x) > r for x, r in zip(point, b)):
        raise ValueError('primal point outside requested box')
    z = rational(proof['right_value'])
    if z < envelope(qs, point):
        raise ValueError('primal envelope inequality fails')
    primal = value(p, point) - z
    dual = mixture_bound(p, qs, proof['weights'], b)
    if primal != dual or rational(proof['value']) != dual:
        raise ValueError('nonzero primal-dual gap or changed optimum value')
    return dual


def unit_result(p, qs, b):
    residual = sub(p, qs[0])
    point = tuple(r if a > 0 else -r if a < 0 else Q(0)
                  for a, r in zip(residual[1:], b))
    optimum = upper(residual, b)
    proof = {'point': list(map(str, point)), 'right_value': str(value(qs[0], point)),
             'weights': ['1'], 'value': str(optimum)}
    verify_optimum(p, qs, b, proof)
    return proof


def solve_comparison(p, qs, b, max_bases=MAX_BASES):
    """Stop only on a feasible primal basis with a nonnegative dual solution."""
    p, qs, b, rows, rhs, objective = problem(p, qs, b)
    if type(max_bases) is not int or not 1 <= max_bases <= MAX_BASES:
        raise ValueError('invalid exact LP basis budget')
    stats = {'basis_trials': 0, 'basis_space': comb(len(rows), len(objective)),
             'singular_bases': 0, 'infeasible_bases': 0, 'nonoptimal_feasible_bases': 0,
             'unit_right_fast_path': len(qs) == 1}
    if len(qs) == 1:
        return unit_result(p, qs, b), stats
    for basis in combinations(range(len(rows)), len(objective)):
        if stats['basis_trials'] >= max_bases:
            raise OverflowError('exact LP basis budget exhausted; no certificate')
        stats['basis_trials'] += 1
        matrix = [rows[i] for i in basis]
        point_z = solve_square(matrix, [rhs[i] for i in basis])
        if point_z is None:
            stats['singular_bases'] += 1
            continue
        if any(product_sum(row, point_z) > bound for row, bound in zip(rows, rhs)):
            stats['infeasible_bases'] += 1
            continue
        multipliers = solve_square(list(zip(*matrix)), objective)
        if multipliers is None or any(y < 0 for y in multipliers):
            stats['nonoptimal_feasible_bases'] += 1
            continue
        weights = [Q(0)] * len(qs)
        for index, y in zip(basis, multipliers):
            if index < len(qs):
                weights[index] += y
        point, z = point_z[:-1], point_z[-1]
        proof = {'point': list(map(str, point)), 'right_value': str(z),
                 'weights': list(map(str, weights)), 'value': str(value(p, point) - z),
                 'active_constraints': list(basis), 'active_multipliers': list(map(str, multipliers))}
        verify_optimum(p, qs, b, proof)
        return proof, stats
    raise RuntimeError('no certified optimum found; not an infeasibility verdict')


def primal_vertex_reference(p, qs, b, max_bases=MAX_BASES):
    """Ordinary exhaustive primal-vertex LP on the same data and guarantee.

    This deliberately simple bounded reference is not HiGHS or a competitive
    optimized LP library. It shares rational elimination with the producer.
    """
    p, qs, b, rows, rhs, objective = problem(p, qs, b)
    if type(max_bases) is not int or not 1 <= max_bases <= MAX_BASES:
        raise ValueError('invalid primal reference basis budget')
    stats = {'basis_trials': 0, 'basis_space': comb(len(rows), len(objective)),
             'unit_right_fast_path': len(qs) == 1}
    if len(qs) == 1:
        result = unit_result(p, qs, b)
        return {key: result[key] for key in ('point', 'right_value', 'value')}, stats
    best = None
    for basis in combinations(range(len(rows)), len(objective)):
        if stats['basis_trials'] >= max_bases:
            raise OverflowError('primal reference basis budget exhausted; no verdict')
        stats['basis_trials'] += 1
        point_z = solve_square([rows[i] for i in basis], [rhs[i] for i in basis])
        if point_z is None or any(product_sum(row, point_z) > bound for row, bound in zip(rows, rhs)):
            continue
        objective_value = p[0] + product_sum(objective, point_z)
        if best is None or objective_value > best[0]:
            best = (objective_value, point_z)
    if best is None:
        raise RuntimeError('primal reference has no feasible vertex')
    optimum, point_z = best
    return {'point': list(map(str, point_z[:-1])), 'right_value': str(point_z[-1]),
            'value': str(optimum)}, stats


def make_exact_certificate(model, radii):
    domain = validate(model)
    b = tuple(rational(x) for x in radii)
    if len(b) != len(domain) or not 1 <= len(b) <= MAX_DIMENSION or any(x < 0 or x > d for x, d in zip(b, domain)):
        raise ValueError('exact certificate box outside bounded interface')
    started, cpu = time.perf_counter(), time.process_time()
    nominal, forms, guards, graph_stats = prepare(model)
    prepared, prepared_cpu = time.perf_counter(), time.process_time()
    if graph_stats['max_frontier'] > MAX_RIGHT_FORMS:
        raise OverflowError('exact certificate frontier limit; no truncation')
    records, optima, work = [], [], []
    for index, guard in enumerate(guards):
        weights = []
        for left_index, p in enumerate(forms[guard['left']]):
            proof, stats = solve_comparison(p, forms[guard['right']], b)
            weights.append(proof['weights'])
            optima.append({'guard_index': index, 'left_form_index': left_index, 'proof': proof})
            work.append(stats)
        records.append({'guard': guard, 'weights': weights})
    p = (nominal['makespan'],) + (Q(0),) * len(b)
    lower, stats = solve_comparison(p, forms['m'], b)
    work.append(stats)
    cert = {'radii': list(map(str, b)), 'orders': nominal['orders'], 'guards': records,
            'lower_weights': lower['weights']}
    return cert, {'guard_optima': optima, 'sink_optimum': lower, 'comparison_work': work,
                  'graph_stats': graph_stats,
                  'preparation_wall_seconds': prepared - started,
                  'preparation_cpu_seconds': prepared_cpu - cpu,
                  'solve_wall_seconds': time.perf_counter() - prepared,
                  'solve_cpu_seconds': time.process_time() - prepared_cpu}


def direct_primal_verdict(model, radii, goal=None):
    """Full same-information order and two-sided error reference, not one guard."""
    domain = validate(model)
    b = tuple(rational(x) for x in radii)
    if len(b) != len(domain) or not 1 <= len(b) <= MAX_DIMENSION or any(x < 0 or x > d for x, d in zip(b, domain)):
        raise ValueError('reference box outside domain')
    if goal is not None and rational(goal) < 0:
        raise ValueError('negative goal')
    started, cpu = time.perf_counter(), time.process_time()
    nominal, forms, guards, graph_stats = prepare(model)
    prepared, prepared_cpu = time.perf_counter(), time.process_time()
    if graph_stats['max_frontier'] > MAX_RIGHT_FORMS:
        raise OverflowError('primal reference frontier limit; no truncation')
    bounds, witnesses, work = [], [], []
    for guard_index, guard in enumerate(guards):
        values = []
        for left_index, p in enumerate(forms[guard['left']]):
            point, stats = primal_vertex_reference(p, forms[guard['right']], b)
            values.append(rational(point['value']))
            witnesses.append({'guard_index': guard_index, 'left_form_index': left_index, 'primal': point})
            work.append(stats)
        bounds.append(max(values))
    p = (nominal['makespan'],) + (Q(0),) * len(b)
    sink, stats = primal_vertex_reference(p, forms['m'], b)
    work.append(stats)
    upward = max(upper(f, b) - nominal['makespan'] for f in forms['m'])
    downward = rational(sink['value'])
    bound = max(Q(0), upward, downward)
    stable = all(u < 0 if g['strict'] else u <= 0 for u, g in zip(bounds, guards))
    verdict = {'certified': stable and (goal is None or bound <= rational(goal)),
               'order_certified': stable, 'global_bound': str(bound),
               'upward_bound': str(upward), 'downward_bound': str(downward),
               'nominal_makespan': str(nominal['makespan']), 'guard_bounds': list(map(str, bounds)),
               'stats': graph_stats}
    return verdict, {'guard_vertices': witnesses, 'sink_vertex': sink, 'comparison_work': work,
                     'preparation_wall_seconds': prepared - started,
                     'preparation_cpu_seconds': prepared_cpu - cpu,
                     'solve_wall_seconds': time.perf_counter() - prepared,
                     'solve_cpu_seconds': time.process_time() - prepared_cpu}


def verify_exact_evidence(model, cert, evidence, goal=None):
    """Read-only reconstruction of all optimality claims, without any LP search."""
    from .checker import check
    verdict = check(model, cert, goal)
    nominal, forms, guards, stats = prepare(model)
    if not same_data(stats, evidence['graph_stats']):
        raise ValueError('changed exact evidence graph statistics')
    b = tuple(rational(x) for x in cert['radii'])
    expected = [(i, j) for i, g in enumerate(guards) for j in range(len(forms[g['left']]))]
    actual = [(row['guard_index'], row['left_form_index']) for row in evidence['guard_optima']]
    if not same_data(expected, actual):
        raise ValueError('incomplete or mistyped exact optimum coverage')
    values = [[] for _ in guards]
    for row in evidence['guard_optima']:
        i, j = row['guard_index'], row['left_form_index']
        g, proof = guards[i], row['proof']
        if not same_data(proof['weights'], cert['guards'][i]['weights'][j]):
            raise ValueError('exact optimum weights differ from checked certificate')
        values[i].append(verify_optimum(forms[g['left']][j], forms[g['right']], b, proof))
    if list(map(str, map(max, values))) != verdict['guard_bounds']:
        raise ValueError('exact guard maxima differ from checked bounds')
    sink = evidence['sink_optimum']
    if not same_data(sink['weights'], cert['lower_weights']):
        raise ValueError('exact sink weights differ from checked certificate')
    p = (nominal['makespan'],) + (Q(0),) * len(b)
    if str(verify_optimum(p, forms['m'], b, sink)) != verdict['downward_bound']:
        raise ValueError('exact sink optimum differs from checked bound')
    return {'all_comparisons_exact': True, 'guard_left_forms': len(expected),
            'sink_optima': 1, 'verdict': verdict,
            'scope': 'equal feasible primal and exact simplex upper bounds on complete reconstructed envelopes'}
