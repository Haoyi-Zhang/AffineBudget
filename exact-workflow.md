# Bounded exact order-and-error workflow

`simcert/exact_lp.py` supplements the numerical producer with rational
active-constraint LP solving. It is standard linear programming, not a new
duality or optimizer. A feasible primal parameter point and a valid simplex
upper bound with exactly equal values establish optimality. The separate
`verify_exact_evidence` consumer reconstructs the model, complete envelopes,
every guard/left-form pair and the sink before accepting those claims. It runs
no LP search and still calls the full exact certificate checker.

The bounded interface admits one to three parameters, at most twelve right
forms, and at most 4096 basis attempts per comparison, retaining the existing
rational input/witness budgets. Zero and mixed radii are supported. Singular
bases are skipped; exhaustion or arithmetic failure does not prove
infeasibility and cannot produce a partial accepted query. The numerical
producer's broader interface and all historical results remain separate.

## Real implementation defects and controls

- Python equality previously admitted Boolean/float substitutes for integer
  predecessor/order IDs and some replay fields, including the strictness flag.
  Typed structural equality and integer admission now preserve the literal
  record contract. Nine negative controls fail on the prior checks and pass
  after repair in ordinary and optimized Python. They do not demonstrate an
  unsafe numerical bound or an exploit.
- The unique weight for a one-form right envelope is one. Importing NumPy/SciPy
  before that fast path prevented solver-free production of even a constant
  model. Two owned dependency controls are red before and green after moving
  imports below the exact fast path. No numerical package was installed.
- Two benign internal counter-observations were rejected in ordinary Python
  but lost their checks under `-O`. Scientific conditions now use explicit
  exceptions rather than removable assertions; both modes reject the controls.
- The canonical JSON writer used the host newline convention, producing CRLF
  on Windows where the retained input contract requires LF. A byte-level red
  control and two full-suite input-audit failures exposed the difference.
  Explicit UTF-8/LF generation now reproduces all 54 original input bytes without
  modifying them.

Normal/optimized command receipts preserve all red outcomes and current checks.
These are ordinary arithmetic, dependency and metadata controls on owned data;
they are not new workloads, exploitation or scientific acceptance.

## Same information and same guarantee

`direct_primal_verdict` is an ordinary exhaustive primal-vertex LP reference.
It receives the identical complete nominal envelopes, radii, identifier/tie
rules and two-sided makespan objective. Both arms construct their own envelopes;
the witness arm also performs complete certificate and optimality replay.
The reference shares model code and rational elimination, is deliberately
simple, and is not optimized HiGHS or an independent complete simulator.

The actual Windows/CPython run covers all original 48 models, 648 dynamic points,
112 catalog queries and 2089 original comparison problems. All same-guarantee
answers match; full-box model coverage is 42/48, unchanged. The ordinary exact LP
and bounded witness backend accept 11/16, 13/16, 11/16 and 12/64 catalog entries.
Selections are `(1/2,1/2)`, `(1,1/2)`, `(1/2,1/2)`, `(1,0,1/4)`, with scores
6, 7, 6, 6 and bounds 1, 7/8, 7/8, 15/16. Counts and selections equal the
already retained numerical-refreshed supplement: no new coverage gain is claimed.

Zero primal-dual gaps for every queried comparison establish catalog optima
among invariant-order certificates, rather than only among particular frozen
or numerically proposed weights. This is not continuous-box optimality or
completeness for true error guarantees after order changes. The original frozen
pipeline still has 0/64 feasible entries and zero-radius bound 12/7; those files
are untouched. The new pipeline admits eight points at second radius zero and
four at one quarter, none at one half or one. No admitted entry has three
strictly positive radii.

## Complete measured costs and native boundary

One sequential run used 29 fresh batches and a 45-second parent wall watchdog
per child. All batches exited zero, with no partial/error record concealed.
Total child-startup/record-I/O/exit wall time is 62.4351597 seconds. CPU observed
at child receipts sums to 60.234375 seconds, excluding subsequent process-exit
and parent-only bookkeeping. Maximum whole-child Windows working set is
25,206,784 bytes (24.04 MiB); this is not per-arm memory or Linux address space.

| Cohort | Exact production | Full certificate/optimum replay | Ordinary primal LP | Frozen full check |
| --- | ---: | ---: | ---: | ---: |
| 48 models | 1.204697 s | 0.908937 s | 1.897875 s | 0.457088 s |
| 112 catalog queries | 18.289837 s | 3.826068 s | 24.694969 s | 1.942805 s |

Production plus replay is **slower on the main models**: 2.113634 versus
1.897875 seconds. Catalog totals are 22.115905 versus 24.694969 seconds. This
single-run prototype comparison is not a general speedup or an optimized-solver
benchmark. Common input/generator wall costs are 0.479848 and 1.162651 seconds;
dynamic replay, serialization, startup and all raw stage/CPU observations are
retained and included in the overall run. Reconstructing envelopes is not free.

The runtime is Windows 11 / CPython 3.12.14, with `-B -S` and
`PYTHONDONTWRITEBYTECODE=1`. NumPy is installed but unused here; SciPy is absent.
POSIX hard CPU/address-space limits cannot be claimed for Windows. This owned
fixture run requires explicit `--bounded-windows` and an external watchdog;
the original POSIX numerical entrypoints keep their guards and are not rerun.
No SciPy/HiGHS, hardware, production simulator, external target or service runs.
General arithmetic/frontier scaling and stronger published scheduling-system
comparison remain outside this bounded campaign.

## Raw records and reproduction

`results/exact-lp/` contains complete model/catalog/oracle JSONL records, rational
primal/dual evidence, actual stage timings, batch environment/cap records,
command stdout/stderr and exact enumerated source/input bindings. All original
inputs, numerical witnesses, native timings, negative results, archives and
history remain in their original locations. Broad command source snapshots are
not execution coverage or fresh literature fulltext certification.

From the artifact root, after reviewing the code:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -S -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python -B -O -S -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python -B -S exact_campaign.py models --start 0 --stop 8 --output /absolute/fresh/owned-output
```

The campaign entry applies the existing 3 GiB/35 CPU-second hard caps on POSIX.
Run each child with an external 45-second wall watchdog. For reviewed bounded
Windows fixtures only, append `--bounded-windows`; the raw receipt explicitly
states that the POSIX hard caps were not applied. Model batches partition
`[0,48)` with width eight; catalog batches partition `[0,112)` with width eight;
oracle batches partition `[0,2089)` with width at most 256. Outputs must be fresh
and outside the retained artifact. Never interpret a subset as a complete run.

The pipeline figure CSV is an inert export of all 64 raw entries:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -S export_figures.py --exact-catalog --results results/exact-lp --output /absolute/fresh/figure-data
```

It byte-matches the supplied manuscript CSV. It does not run an optimizer or
discard refused entries. The manuscript discloses generated additions in this
revision; no human authorship approval, venue compliance or novelty is inferred
from successful execution.
