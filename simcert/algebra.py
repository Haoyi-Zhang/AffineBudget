"""Rational max-affine envelopes. No optimization library is trusted here."""
from fractions import Fraction as Q
from itertools import combinations, product

MAX_BITS = 4096
MAX_FORMS = 2048

def rational(x):
    if isinstance(x, bool) or isinstance(x, float):
        raise ValueError("integers or rational strings required")
    if not isinstance(x, (str, int, Q)):
        raise ValueError("bad rational type")
    if isinstance(x, str) and len(x) > 3000:
        raise ValueError("oversized rational")
    y = Q(x)
    if max(y.numerator.bit_length(), y.denominator.bit_length()) > MAX_BITS:
        raise ValueError("rational bit budget exceeded")
    return y

def form(xs, k):
    if len(xs) != k + 1:
        raise ValueError("affine dimension mismatch")
    return tuple(rational(x) for x in xs)

def dot(a, b):
    return sum((x*y for x, y in zip(a, b)), Q(0))

def value(f, x):
    return f[0] + dot(f[1:], x)

def upper(f, b):
    return f[0] + sum((abs(a)*r for a,r in zip(f[1:],b)), Q(0))

def add(f, g):
    return tuple(a+b for a,b in zip(f,g))

def sub(f, g):
    return tuple(a-b for a,b in zip(f,g))

def envelope(fs, x):
    return max(value(f,x) for f in fs)

def reduce_forms(fs, b, cap=MAX_FORMS):
    # Streaming pairwise dominance: dropping f is sound only if a retained g
    # dominates f on the entire declared domain. Never silently truncate.
    keep=[]
    for f in fs:
        if f in keep or any(upper(sub(f,g),b) <= 0 for g in keep):
            continue
        keep=[g for g in keep if upper(sub(g,f),b) > 0]
        keep.append(f)
        if len(keep)>cap:
            raise OverflowError("affine frontier cap exceeded")
    return tuple(sorted(keep))

def mixture_bound(p, qs, weights, b):
    if len(weights) != len(qs):
        raise ValueError("witness dimension mismatch")
    ws=tuple(rational(w) for w in weights)
    if any(w<0 for w in ws) or sum(ws,Q(0))!=1:
        raise ValueError("witness is not a convex combination")
    avg=tuple(sum((w*q[i] for w,q in zip(ws,qs)),Q(0)) for i in range(len(p)))
    return upper(sub(p,avg),b)

def interval_bound(ps,qs,b):
    hi=max(upper(p,b) for p in ps)
    lo=max(q[0]-sum((abs(a)*r for a,r in zip(q[1:],b)),Q(0)) for q in qs)
    return hi-lo

def single_path_bound(ps,qs,b):
    return max(min(upper(sub(p,q),b) for q in qs) for p in ps)

def exact_small_oracle(ps,qs,b):
    """Independent exact arrangement oracle, for 1D/2D boxes only.

    In each cell where the right envelope is affine, left minus right is
    convex, hence its maximum on the cell occurs at a vertex. Box boundaries
    and all right-form equality lines enumerate a superset of those vertices.
    """
    k=len(b)
    if k not in (1,2) or any(r<=0 for r in b):
        raise ValueError("oracle needs a positive 1D or 2D box")
    candidates=set(product(*[(-r,r) for r in b]))
    lines=[]
    for i in range(k):
        a=[Q(0)]*k;a[i]=Q(1)
        lines.extend([(tuple(a),r) for r in (-b[i],b[i])])
    for q,r in combinations(qs,2):
        d=sub(q,r)
        if any(d[1:]):lines.append((d[1:],-d[0]))
    if k==1:
        for a,c in lines:
            if a[0]: candidates.add((c/a[0],))
    else:
        for (a,c),(d,e) in combinations(lines,2):
            det=a[0]*d[1]-a[1]*d[0]
            if det:
                candidates.add(((c*d[1]-a[1]*e)/det,(a[0]*e-c*d[0])/det))
    candidates=[x for x in candidates if all(-r<=v<=r for v,r in zip(x,b))]
    scored=[(envelope(ps,x)-envelope(qs,x),x) for x in candidates]
    return max(scored),len(candidates)
