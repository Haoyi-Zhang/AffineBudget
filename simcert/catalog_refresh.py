"""Supplementary finite-catalog witness refresh; the checker is unchanged."""
from __future__ import annotations
import copy
import itertools
from fractions import Fraction as Q
from .algebra import rational
from .checker import check
from .model import prepare, validate

CASE_IDS = ("case-007", "case-019", "case-031", "case-043")
LEVELS = (Q(0), Q(1, 4), Q(1, 2), Q(1))


def catalog(model):
    domain = validate(model)
    if len(domain) > 3:
        raise ValueError("supplement limited to at most three parameters")
    choices = [tuple((i, r) for i, r in enumerate(LEVELS) if r <= d) for d in domain]
    points = []
    for entry in itertools.product(*choices):
        indices = [i for i, _ in entry]
        points.append({"indices": indices, "radii": [str(r) for _, r in entry],
                       "score": sum((h + 1) * i for h, i in enumerate(indices))})
    if len(points) > 64:
        raise ValueError("supplement catalog exceeds 64 points")
    return points


def selected(rows):
    accepted = [r for r in rows if r["feasible"]]
    return max(accepted, key=lambda r: (r["score"], tuple(r["indices"]))) if accepted else None


def frozen_row(model, certificate, point, target):
    witness = copy.deepcopy(certificate)
    witness["radii"] = list(point["radii"])
    verdict = check(model, witness, target)
    return dict(point, feasible=verdict["certified"], bound=verdict["global_bound"])


def nominal_onehot(model, radii):
    """Propose only at zero; this is not an acceptance shortcut."""
    domain = validate(model)
    b = tuple(rational(r) for r in radii)
    if len(b) != len(domain) or any(b):
        raise ValueError("nominal fallback requires exactly zero radii")
    nominal, forms, guards, _ = prepare(model)

    def unit(qs):
        # First nominally maximal form in the checker's canonical ordering.
        index = max(range(len(qs)), key=lambda i: qs[i][0])
        return ["1" if j == index else "0" for j in range(len(qs))]

    return {"radii": list(map(str, b)), "orders": nominal["orders"],
            "guards": [{"guard": g, "weights": [unit(forms[g["right"]])
                                                 for _ in forms[g["left"]]]}
                       for g in guards],
            "lower_weights": unit(forms["m"])}


def refreshed_row(model, point, target, propose=None, call_event=None):
    """Retain numerical errors/refusals even when a zero fallback succeeds."""
    if propose is None:
        from .producer import make_certificate
        propose = make_certificate
    attempts = []

    def attempt(policy, factory):
        record = {"policy": policy}
        try:
            if call_event is not None:
                call_event(policy)
            cert = factory()
        except Exception as exc:
            record.update(status="producer_error", error_type=type(exc).__name__, error=str(exc))
        else:
            record["certificate"] = cert
            try:
                if call_event is not None:
                    call_event("exact-checker")
                verdict = check(model, cert, target)
                if tuple(map(rational, cert["radii"])) != tuple(map(rational, point["radii"])):
                    raise ValueError("proposal radii differ from catalog point")
            except Exception as exc:
                record.update(status="checker_error", error_type=type(exc).__name__, error=str(exc))
            else:
                record.update(status="certified" if verdict["certified"] else "refused",
                              verdict=verdict)
        attempts.append(record)
        return record

    chosen = attempt("existing-numerical-producer", lambda: propose(model, point["radii"]))
    if chosen["status"] != "certified" and all(rational(r) == 0 for r in point["radii"]):
        fallback = attempt("zero-only-nominal-onehot", lambda: nominal_onehot(model, point["radii"]))
        if fallback["status"] == "certified":
            chosen = fallback
    verdict = chosen.get("verdict")
    return dict(point, feasible=chosen["status"] == "certified",
                bound=verdict["global_bound"] if verdict else None,
                status=chosen["status"], attempts=attempts)


def compare_catalog(model, certificate, retained, propose=None, record=None,
                    recheck_frozen=True, call_event=None):
    target = rational(retained["target"])
    if target != 1:
        raise ValueError("supplement preserves target one")
    points = catalog(model)
    if recheck_frozen:
        frozen = [frozen_row(model, certificate, p, target) for p in points]
    else:
        # Numerical arm only. These copied fields are not a fresh certification:
        # the separate portable reconciler must recheck both arms in full.
        frozen = copy.deepcopy(retained["candidates"])
        if [{k: row[k] for k in ("indices", "radii", "score")} for row in frozen] != points:
            raise ValueError("retained frozen point coverage changed")
        if any(type(row["feasible"]) is not bool for row in frozen):
            raise ValueError("invalid retained feasibility field")
    expected = {"case_id": model["case_id"], "target": "1",
                "objective": "sum((dimension+1)*level_index)",
                "restriction": "frozen maximum-domain witnesses and finite catalog only",
                "selected": selected(frozen), "candidates": frozen}
    if expected != retained:
        raise ValueError("retained frozen catalog differs; no resealing")
    rows = []
    for point, old in zip(points, frozen):
        new = refreshed_row(model, point, target, propose, call_event)
        row = {"frozen": old, "refreshed": new}
        rows.append(row)
        if record is not None:
            record(row)
    fresh = [r["refreshed"] for r in rows]
    errors = sum(a["status"].endswith("_error") for r in fresh for a in r["attempts"])
    return {"case_id": model["case_id"], "target": "1", "points": len(points),
            "frozen_selected": selected(frozen), "refreshed_selected": selected(fresh),
            "newly_certified": sum(not r["frozen"]["feasible"] and r["refreshed"]["feasible"] for r in rows),
            "lost_certifications": sum(r["frozen"]["feasible"] and not r["refreshed"]["feasible"] for r in rows),
            "numerical_or_checker_errors": errors, "complete_catalog_visited": True,
            "frozen_rechecked": recheck_frozen,
            "rows": rows, "scope": "these supplied witnesses on the same finite catalog; no continuous optimum or timing comparison"}
