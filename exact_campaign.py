#!/usr/bin/env python3
"""Owned bounded exact-LP campaign, preserving all original scientific results.

Fresh external output only. No numerical package, network, simulator or target.
Windows execution requires an explicit bounded-fixture opt-in; it does not
pretend that POSIX address-space/CPU caps exist there. Parent watchdog required.
"""
import argparse
import copy
from fractions import Fraction as Q
from hashlib import sha256
import itertools
import json
import os
from pathlib import Path
import platform
import sys
import time

from simcert.algebra import same_data, rational, exact_small_oracle
from simcert.model import simulate
from simcert.cases import suite
from simcert.catalog_refresh import CASE_IDS, catalog
from simcert.exact_lp import (make_exact_certificate, direct_primal_verdict,
                             verify_exact_evidence, solve_comparison,
                             primal_vertex_reference, verify_optimum)
from simcert.checker import check
from campaign import oracle_inputs, save

ROOT = Path(__file__).resolve().parent


def peak_memory():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                    'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                    'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        function = psapi.GetProcessMemoryInfo
        function.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        function.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not function(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'peak_working_set_bytes': counters.PeakWorkingSetSize,
                'peak_commit_bytes': counters.PeakPagefileUsage,
                'source': 'Windows GetProcessMemoryInfo; own process only'}
    import resource
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {'peak_rss_bytes': rss if sys.platform == 'darwin' else 1024 * rss,
            'source': 'POSIX getrusage own process'}


def measured(function):
    wall, cpu = time.perf_counter(), time.process_time()
    value = function()
    return value, {'wall_seconds': time.perf_counter() - wall,
                   'cpu_seconds': time.process_time() - cpu}


def owned_model(case):
    path = ROOT / 'inputs' / (case + '.json')
    model = json.loads(path.read_text(encoding='utf-8'))
    generated = next(m for m in suite() if m['case_id'] == case)
    if not same_data(model, generated):
        raise ValueError('owned retained model differs from declared generator')
    return model, sha256(path.read_bytes()).hexdigest()


def contract_record(case, radii, target=None, point=None):
    started = time.perf_counter()
    (model, input_hash), load_cost = measured(lambda: owned_model(case))
    (cert, analysis), production = measured(lambda: make_exact_certificate(model, radii))
    exact, reconstruction = measured(lambda: verify_exact_evidence(model, cert, analysis, target))
    (reference, reference_analysis), reference_cost = measured(lambda: direct_primal_verdict(model, radii, target))
    verdict = exact['verdict']
    if not same_data({key: verdict[key] for key in reference}, reference):
        raise AssertionError('same-information full-contract primal reference mismatch')
    old = json.loads((ROOT / 'results/models' / (case + '.json')).read_text(encoding='utf-8'))
    frozen = copy.deepcopy(old['certificate'])
    frozen['radii'] = list(radii)
    frozen_verdict, frozen_cost = measured(lambda: check(model, frozen, target))
    return {'case_id': case, 'family': model['family'], 'input_sha256': input_hash,
            'radii': list(radii), 'target': target, 'catalog_point': point,
            'certificate': cert, 'exact_evidence': analysis, 'reconstruction': exact,
            'primal_reference_verdict': reference, 'primal_reference_evidence': reference_analysis,
            'frozen_verdict': frozen_verdict,
            'measurement': {'load_and_generator': load_cost, 'exact_production': production,
                'full_certificate_and_optimality_reconstruction': reconstruction,
                'direct_primal_reference': reference_cost, 'frozen_full_checker': frozen_cost,
                'compute_wall_seconds': time.perf_counter() - started,
                'scope': 'both full-contract arms include their own complete-envelope construction; exact arm also includes full certificate/optimality replay; frozen arm receives retained maximum-box witnesses; no cache or speedup claim'}}


def model_record(index):
    case = f'case-{index:03d}'
    model, _ = owned_model(case)
    radii = model['domain']
    record = contract_record(case, radii)
    nominal = simulate(model, [0] * len(radii))
    samples = []
    began = time.perf_counter()
    for point in itertools.product((-1, 0, 1), repeat=len(radii)):
        actual = simulate(model, point)
        same = same_data(actual['orders'], nominal['orders'])
        # same_data is for JSON string-keyed objects; resource names are strings.
        error = abs(actual['makespan'] - nominal['makespan'])
        verdict = record['reconstruction']['verdict']
        if verdict['certified'] and (not same or error > rational(verdict['global_bound'])):
            raise AssertionError('false exact certified dynamic execution')
        samples.append({'point': list(point), 'same_order': same,
                        'makespan': str(actual['makespan']), 'absolute_error': str(error)})
    record['samples'] = samples
    record['measurement']['dynamic_replay_wall_seconds'] = time.perf_counter() - began
    return record


def oracle_record(index, item):
    p_forms, qs, radii = item
    comparisons, reference_values = [], []
    for p in p_forms:
        proof, work = solve_comparison(p, qs, radii)
        reference, reference_work = primal_vertex_reference(p, qs, radii)
        optimum = verify_optimum(p, qs, radii, proof)
        if optimum != rational(reference['value']):
            raise AssertionError('exact comparison differs from primal reference')
        comparisons.append({'proof': proof, 'work': work, 'primal_reference': reference,
                            'primal_reference_work': reference_work})
        reference_values.append(optimum)
    (arrangement, maximizing_point), vertices = exact_small_oracle(p_forms, qs, radii)
    if max(reference_values) != arrangement:
        raise AssertionError('exact LP differs from independent arrangement oracle')
    original = json.loads((ROOT / 'results/oracles' / f'oracle-{index:04d}.json').read_text(encoding='utf-8'))
    data = {'left': [list(map(str, p)) for p in p_forms], 'right': [list(map(str, q)) for q in qs],
            'radii': list(map(str, radii))}
    if not same_data(data, {key: original[key] for key in data}):
        raise AssertionError('oracle problem selection differs')
    return {'id': index, **data, 'comparisons': comparisons, 'optimum': str(arrangement),
            'arrangement_point': list(map(str, maximizing_point)), 'arrangement_vertices': vertices}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('models', 'catalog', 'oracles'))
    parser.add_argument('--start', type=int, required=True)
    parser.add_argument('--stop', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bounded-windows', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT) or out in ROOT.parents:
        raise ValueError('fresh destination outside retained artifact required')
    if os.name == 'posix':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (35, 35))
        caps = {'hard_address_space_bytes': 3 * 1024**3, 'hard_cpu_seconds': 35}
    elif os.name == 'nt' and args.bounded_windows:
        caps = {'hard_address_space_bytes': None, 'hard_cpu_seconds': None,
                'scope': 'explicit owned bounded-fixture Windows run; parent wall watchdog required, not POSIX-cap equivalence'}
    else:
        raise SystemExit('Unsupported hard caps; Windows needs explicit bounded-fixture opt-in and external watchdog.')
    catalog_points = [(case, point) for case in CASE_IDS
                      for point in catalog(owned_model(case)[0])] if args.mode == 'catalog' else []
    limit = {'models': 48, 'catalog': 112, 'oracles': 2089}[args.mode]
    if not 0 <= args.start < args.stop <= limit or args.stop - args.start > (256 if args.mode == 'oracles' else 8):
        raise ValueError('batch outside declared complete cohort or bounded batch width')
    out.mkdir(parents=True, exist_ok=False)
    start, cpu = time.perf_counter(), time.process_time()
    count = 0
    status, error = 'completed', None
    oracle_problems = oracle_inputs() if args.mode == 'oracles' else []
    try:
        with (out / 'records.jsonl').open('x', encoding='utf-8', newline='\n') as handle:
            for index in range(args.start, args.stop):
                if args.mode == 'models':
                    row = model_record(index)
                elif args.mode == 'catalog':
                    case, point = catalog_points[index]
                    row = contract_record(case, point['radii'], '1', point)
                else:
                    row = oracle_record(index, oracle_problems[index])
                handle.write(json.dumps(row, sort_keys=True) + '\n')
                handle.flush()
                count += 1
    except Exception as exc:
        status, error = 'failed', {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        receipt = {'mode': args.mode, 'start': args.start, 'stop': args.stop,
                   'records_completed': count, 'status': status, 'error': error,
                   'wall_seconds_through_record_io': time.perf_counter() - start,
                   'scientific_cpu_seconds': time.process_time() - cpu,
                   'process_cpu_seconds_at_receipt': time.process_time(), 'memory': peak_memory(),
                   'caps': caps, 'environment': {'python': sys.version, 'platform': platform.platform(),
                       'PYTHONDONTWRITEBYTECODE': os.environ.get('PYTHONDONTWRITEBYTECODE'), 'site_disabled': sys.flags.no_site},
                   'scope': 'actual standard-library rational production/reference/reconstruction; no SciPy/HiGHS invocation, hardware trace or simulator acceleration'}
        save(out / 'receipt.json', receipt)
        print(json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
