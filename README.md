# Error-budgeted parallel simulation

This standalone repository accompanies **Order-Stable Error Budgets for Affine-Timed Resource Models**. It contains a finite deterministic FCFS timing model, numerical certificate producer, exact rational checker, complete mathematical arguments, exact generated inputs, and measured results. It does not require the manuscript directory, a network connection for verification, private data, or a missing controller.

## What is established

A candidate resource order is an actual eager FCFS order precisely when its candidate readiness comparisons are self-consistent, with identifier-sensitive strictness. Complete max-affine envelopes and rational convex mixtures certify those comparisons over a parameter box. A successful certificate then establishes a two-sided makespan bound. The ideal explicit-envelope comparison is exact by LP duality; the floating-point producer is sound only through exact checking and is potentially incomplete. See `proofs/arguments.md`.

The retained campaign contains 48 generated models, 648 dynamic parameter points, 2,089 continuous-domain small comparison oracles, 112 catalog entries, six independent-join models with 126 sign-corner executions, and 512 Boolean-formula reduction checks with 6,144 assignments. These are synthetic mathematical models, not application, hardware, human, or production-simulator measurements. The checker and producer share the model/envelope implementation; independence from LP search is not independent implementation or independent peer review.

The prescribed 12 same-venue, five influential, and five adjacent full-paper calibration is complete in `literature-calibration.csv`. The closest parametric work is broader in scheduler/event-network semantics and full-domain partitioning; this repository instead supports a narrower one-box FCFS membership query with an exact order-and-error certificate. No dominance, runtime advantage, hardware fidelity, or production-simulator significance is inferred. There is no public repository address or external submission.

## Offline verification (no third-party Python packages)

From this directory, with ordinary CPython on Linux:

```sh
python -S verify.py
```

This discovers 31 tests, regenerates all 48 main inputs and six join inputs into a fresh temporary destination, byte-compares them with the 54 retained inputs, checks exact file coverage, reconstructs and checks all certificates, replays the 648 + 126 dynamic points, reruns every exact arrangement oracle, rechecks the 112 allocation decisions and selected optima, checks all 512 reduction formulas, reruns the separate changed-order/constant-makespan control, and audits all 65 cited bibliography records plus the 12/5/5 full-paper calibration matrix. Success exits zero. The JSON printed to standard output records test counts, CPU and wall time, peak resident memory, and worker count; test details go to standard error. The stored original-run receipt is `results/verification.json`. `-S` demonstrates that site packages, including SciPy, are not needed for this path. Do not use Python optimization flags that suppress assertions.

Tests are finite executable evidence, not a mechanization of the general theorems. The trusted base includes CPython rational arithmetic, input parsing, the model semantics, complete-envelope reconstruction, and the checker.

## Fresh production and reproduction

New witness production requires NumPy and SciPy with the HiGHS backend. They are used unmodified through their public interfaces; no external simulator baseline is vendored. The standard-library checker is separate. In an environment without those libraries, the offline verification command above still checks all delivered witnesses and exact data. The dependency declarations in `requirements.txt` identify required packages but deliberately do not promise bit-identical solver behavior across installations. The final producer recheck used CPython 3.13.5, NumPy 2.3.5, and SciPy 1.17.0 on x86-64 Linux with glibc 2.41; these tested versions are reported here as context, not as a toolchain fingerprint or a claim that other conforming installations fail.

Run the full production campaign sequentially, with each child limited to one numerical thread, 3 GiB address space, and 35 CPU seconds; the parent uses a 45-second wall-clock watchdog so ordinary scheduling or output delay does not consume the entire CPU-limit margin:

```sh
sh reproduce.sh fresh-results models
sh reproduce.sh fresh-results oracles
sh reproduce.sh fresh-results allocation
sh reproduce.sh fresh-results verify
```

The destination must not already exist for the first phase. Subsequent phases use that same destination and require the preceding phase receipt. Each command is a bounded resumable phase. The four phases run the pilot, 48 models in four batches, all 2,089 oracles in bounded batches, four allocation cases, the six structural models, the reduction check, separate unchanged-makespan order-switch control, summary export, and scientific reconciliation against the shipped results. It does not overwrite the retained measurements. It creates a reproduction receipt, per-batch accounting, all 54 regenerated inputs, exact generated data, and figure-data CSVs under the new destination; source-tree inputs remain immutable and are compared byte for byte during reconciliation. A changed or failed witness is not silently converted into an original success: reconciliation returns a nonzero status for changed scientific results. Timing measurements are expected to differ. Multiple LP optima may yield different rational weight vectors; the comparison checks the same exact verdicts and bound values, rather than byte identity of weights. A changed bound is reported even if it remains sound.

A typical bounded individual command is:

```sh
python campaign.py models --start 0 --stop 12 --output another-results
python campaign.py oracles --start 0 --stop 256 --output another-results
```

These commands can resume a missing batch. Do not confuse an arbitrary subset with the complete campaign; only the final verification phase reconciles the required set. The exact original input files in `inputs/` are also regenerated and compared by the tests. Scientific generation in the supplied scripts uses no network, GPU, external API, or other machine.

## Model and certificate formats

An input JSON has `domain` (nonnegative rational radii) and dependency-topologically ordered `jobs`. Each job has a unique integer `id`, a nonempty string `resource`, predecessor IDs in `deps`, and affine `release` and `service` lists. A form `[c,a1,...,ak]` means `c + sum(ah*theta_h)`. Values are integer or rational strings, never binary floating-point input. Releases must be nonnegative and services strictly positive throughout the declared box. Jobs are eager, nonpreemptive FCFS; equal arrivals are ordered by integer ID; all completions at a timestamp precede dispatch.

A certificate records its requested `radii`, exact nominal `orders`, one record per adjacent readiness guard, one rational simplex vector for every left-envelope form, and a sink `lower_weights` simplex. The checker reconstructs all envelopes, so omitted left forms or guards cannot be trusted into correctness. The acceptance result distinguishes `order_certified` from a global target check. A numeric `global_bound` attached to a refused order is a conditional fixed-graph calculation, not an actual execution guarantee.

Input limits are eight parameters, 512 jobs, 4,096-bit input numerator/denominator, and 2,048 retained forms per frontier. A frontier overflow refuses rather than truncates. Intermediate arithmetic can exceed the input bit size. CPU/address-space guards bound the actual process; the general theorems do not assert polynomial scaling in a compact graph representation.

## Results and interpretation

| Family | Interval | Single path | Mixture | Sampled order-switch cases |
|---|---:|---:|---:|---:|
| Shared prefix | 0 | 0 | 12 | 0 |
| Staggered bank | 5 | 8 | 8 | 4 |
| Fork--join | 3 | 12 | 12 | 0 |
| Pipeline | 3 | 10 | 10 | 2 |
| Total (48 cases) | 11 | 30 | 42 | 6 |

All three formulas use identical canonical envelopes. Main coverage imposes no common error target; each mixture success also carries its own checked makespan bound. No accepted dynamic point violates its order or bound. All six refused models have sampled order changes. The 2,089 exact comparison values agree rationally, not merely within tolerance.

The frozen-witness allocator is optimal only over its enumerated catalog and fixed rational inequalities. At target one, the three feasible selected cases have scores 6, 7, 6 and bounds 1, 7/8, 7/8. The pipeline has zero feasible entries out of 64: its frozen downward witness remains at 12/7 even at zero radius, although actual zero-radius error is zero. This informative failure is retained. It is not an impossibility result about different witnesses or all abstraction choices.

`results/pilot.json` retains the three-job negative control: nominal makespan 202, perturbed 101.99, fixed-graph bound zero, order guard +1/100 and refusal. The proof gives unbounded amplification as the long service grows. The independent-join data show linear form counts `15m+4` alongside `2^m` designated readiness-selector patterns; dense coefficient storage is quadratic, and no runtime comparison with another symbolic executor is claimed.

A separate three-job control in `results/boundary-control.json` has a blocker followed by two unit services. Their FCFS order changes but the total makespan remains exactly five. It is correctly refused by the fixed-order guard. This establishes that order-guard completeness is not completeness for all true global-error guarantees; the control is outside the unchanged 48-case campaign.

## Files

`simcert/` contains rational algebra, the dynamic schedule evaluator, candidate graph construction, producer, checker, and generators. `tests/` contains finite checks and mutation controls. `inputs/` contains 54 exact main/structural models. `results/` contains raw inputs to the oracles, witnesses, exact outcomes, failures, original measurements, and accounting. `proofs/arguments.md` is a standalone mathematical account. `claim_evidence_ledger.csv` maps claims to proof and executable evidence. `literature-calibration.csv` records the completed 12/5/5 full-paper matrix and exact relationship to this work. `bibliography-audit.csv`, `scholarly/references.bib`, and `scholarly/citation-usage.csv` preserve the 65-record metadata and usage audit; `audit_references.py` enforces it offline. `external_resources.csv` records sources, access status, licensing, and unmodified dependency use.

`export_figures.py` derives coverage and structure CSVs from exact raw results, rather than redrawing reported numbers by hand. To regenerate data for another consumer:

```sh
python -S export_figures.py --results results --output exported-figure-data
```

The repository does not require LaTeX. The accompanying complete project separately includes the unmodified ACM class, manuscript source, TikZ/PGFPlots figures, and compiled paper.

## Reproduction and disclosure boundary

A clean extraction was used for the documented verification and complete regeneration; see `results/clean-reproduction.json`. Successful execution supports repeatability of these delivered cases, not the truth of every mathematical theorem or an independent review. There is no version/commit/checksum manifest. Exact input data are supplied, but cross-installation bit-identical numerical witness generation is not asserted. The exact checker establishes whether any proposed witness is acceptable.

An AI research assistant substantively contributed to problem formulation, mathematical arguments, code, input generation, experiments, analysis, literature comparison, and drafting. The research process is not represented as human-only or as mere writing assistance. No external human validation, external submission, or deployed behavior is asserted. All original repository files are offered under `LICENSE`; external software and scholarly works retain their separate rights, as recorded in the resource ledger. No third-party paper PDF, font, or simulator source is redistributed here.
