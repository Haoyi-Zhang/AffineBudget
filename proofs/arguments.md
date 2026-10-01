# Mathematical arguments

These are written proofs for a finite rational timing model. They are not machine-checked general proofs. Executable finite checks exercise the implementation separately. No hardware model relation is inferred from these arguments.

## 1. Model and fixed-order graph

Let J be a finite nonempty set of jobs, with unique integer identifiers, a fixed resource rho(i) per job, and an acyclic functional predecessor relation D_i. Let theta belong to the closed centered box B_d = {theta: |theta_h| <= d_h}; all d_h are nonnegative rationals. Release r_i(theta) and service s_i(theta) are rational affine functions; releases are nonnegative and services strictly positive throughout B_d. The actual readiness is A_i = max(r_i, max_{j in D_i} F_j). A free resource eagerly runs the arrived job with lexicographically smallest (A_i,i), nonpreemptively. All simultaneous completions are processed before dispatch. This semantics determines a unique finite execution: positive services and an acyclic finite dependency relation give a next completion or eligible release and no same-time zero-service cascade.

At theta=0, record each resource's job sequence. Add serialization to the functional dependencies to obtain a candidate graph. For a job with previous resource job p(i), candidate completion is Fhat_i = max(Ahat_i,Fhat_p(i)) + s_i, and Ahat_i = max(r_i,max_{j in D_i} Fhat_j). The previous-completion term is omitted for a first job. A candidate must contain every job exactly once on its assigned resource, and its graph must be acyclic.

Construct graph vertices source, arrival/completion for each job, and sink. A source-to-arrival edge has release weight; functional completion-to-arrival edges have weight zero; arrival-to-completion and previous-resource-completion-to-completion edges have service weight; every completion-to-sink edge has zero weight. The sink is makespan. This distinguishes readiness from start time, which is essential for FCFS comparisons.

For every vertex v, retain affine sums of all source-to-v paths. By induction in graph topological order, the maximum of those forms equals its candidate time. At an edge, affine forms add; at a join, predecessor form sets are united. Duplicate removal and removal of a form f dominated by a retained form g throughout B_d preserve the maximum. For f=(c_f,a_f), domination follows exactly from c_f-c_g + sum_h d_h |a_fh-a_gh| <= 0. If a dominating form is later removed by another dominator, transitivity preserves validity. The checker reconstructs full coverage, never trusts a producer-selected subset, and fails on a representation cap rather than truncating.

## 2. Exact comparison of explicit envelopes

Write <P>(theta)=max_{p in P}(c_p+a_p dot theta) for a nonempty finite set P. For requested radii 0 <= b <= d, define support S_b(c,a)=c+sum_h b_h|a_h|. For each p in P choose nonnegative rational weights lambda_q summing exactly to one over Q. The mixture U_b(p,lambda) is

    c_p - sum_q lambda_q c_q
      + sum_h b_h |a_ph - sum_q lambda_q a_qh|.

Because a convex combination of Q is never greater than <Q>, for every theta in B_b,

    p(theta) - <Q>(theta)
       <= p(theta) - sum_q lambda_q q(theta)
       <= U_b(p,lambda).

Taking the finite maximum over p proves a sound upper bound on D=max_{theta in B_b}(<P>-<Q>). No numerical tolerance is present in this proof.

**Ideal exactness.** For a fixed p, compute max_{theta,z} c_p+a_p dot theta-z subject to z>=c_q+a_q dot theta for every q and -b<=theta<=b. This feasible rational LP has a finite optimum, since the box is compact and the right envelope is continuous. Its dual attaches nonnegative lambda_q to the envelope inequalities, with sum lambda=1 from the free z variable. Nonnegative multipliers alpha_h,beta_h for the box satisfy alpha_h-beta_h=a_ph-sum lambda_q a_qh. Minimizing their objective contribution b_h(alpha_h+beta_h) gives b_h times the absolute residual coefficient, including when b_h=0. Strong LP duality gives

    max_theta [p(theta)-<Q>(theta)] = min_{lambda in simplex(Q)} U_b(p,lambda).

An optimum rational lambda exists for rational data. Finite maximization over p commutes with maximization over theta, proving D=max_p min_lambda U_b(p,lambda). This is an application of standard LP duality, not a new general duality theorem. The producer's floating-point solve and rational reconstruction need not attain this ideal; a poor but valid witness remains sound and may cause refusal.

The envelope difference is continuous on a compact box. Thus a strict universal comparison <P><<Q> holds exactly when D<0, and a non-strict one exactly when D<=0. The compactness qualification prevents replacing a strict universal assertion with an invalid zero-margin argument on an open domain.

A witness can be supported on at most k+2 right forms without changing its averaged intercept and coefficient vector. To see this, any representation of that vector using more than k+2 positively weighted points in R^(k+1) has an affine dependence. Move the weights along the dependence until one vanishes, preserving nonnegativity, total mass and the average. Repeat. This is a representation fact; support minimization is not implemented or used to claim faster execution.

**Baselines.** A single-path bound is T=max_p min_q S_b(p-q). Restricting the simplex to unit vectors shows ideal D<=T. Independent intervals use I=max_p S_b(p) - max_q(c_q-sum_h b_h|a_qh|). For every p,q, S_b(p-q)<=S_b(p)-inf q. Choosing the q that maximizes its individual infimum proves T<=I. I is conservative: max_q inf q need not equal inf max_q q. The actual numerical producer is not guaranteed to attain the ideal D or to improve every baseline without checking its witness.

For P={0}, Q={1/4+theta,1/4-theta}, b=1, the half/half mixture gives -1/4, while each unit-vector witness gives 3/4. Adding a shared prefix 2phi on both sides preserves the mixture value but independent intervals give 19/4. For nonnegative coefficients, P={3+x+y}, Q={13/4+2x,13/4+2y} on [-1,1]^2 gives mixture -1/4 and single-path 7/4. Neither example claims that common-path cancellation originated here.

## 3. Resource-order self-consistency

For each adjacent pair i,j in each candidate resource sequence, require Ahat_i<=Ahat_j when i<j, and Ahat_i<Ahat_j when i>j. This is precisely lexicographic ordering of the readiness pairs. Adjacent comparisons imply all pairs by transitivity.

**Theorem.** Fix theta and an acyclic complete candidate. Actual eager FCFS execution has exactly the candidate sequences if and only if every adjacent comparison holds. When they hold, candidate and actual times coincide.

**Necessity.** If actual sequences equal the candidates, each actual completion satisfies the fixed-order recurrence, including its previous resource completion. An acyclic recurrence has a unique solution, so actual and candidate readiness/completion times coincide. FCFS orders the actual readiness pairs lexicographically; every adjacent comparison follows with the stated strictness.

**Sufficiency.** Evaluate the candidate recurrence and schedule each job at max(candidate readiness, previous candidate resource completion), or at readiness for the first job. This is feasible: releases and functional dependencies are respected, services have their prescribed positive lengths, and no same-resource jobs overlap. Guards make every resource sequence sorted by candidate readiness pair. Before the first job, a later job cannot be ready when the first is not. Between consecutive jobs, the next starts either at the previous completion or at its later readiness. During any resulting idle interval no later job can be ready, since that would contradict sorted readiness. At dispatch, no later ready job has a smaller readiness pair. Therefore this schedule is eager and FCFS. The deterministic event semantics has a unique execution, so the feasible candidate schedule is the actual one. The reasoning does not assume order preservation in order to prove it.

Applying the rational mixture bounds to all candidate readiness guards over B_b proves the same order at every point of B_b. An ideal witness exists for every true comparison of explicit envelopes; the practical producer may fail to find one. A failed guard is a refusal, not automatically a proof that the resource order changes. A sampled changed order can provide that separate proof of non-invariance.

## 4. Conditional makespan error

Let Q_C be the complete sink envelope and C0 the nominal makespan. The exact fixed-graph upward deviation is

    Eplus = max_q [c_q + sum_h b_h|a_qh| - C0].

This follows by commuting the two maxima. For any sink simplex mu, the downward deviation is at most

    Eminus = C0 - sum_q mu_q c_q
               + sum_h b_h |sum_q mu_q a_qh|.

This is the comparison bound of Section 2 with constant left form C0. Once all order guards pass, candidate and actual makespans coincide, and for every theta in B_b,

    |C(theta)-C0| <= max(0,Eplus,Eminus).

With an ideal sink mixture, both directions are exact and their maximum is the exact worst absolute deviation for that preserved order. Without a passed order premise, even a zero candidate-graph radius is not an execution guarantee.

For fixed witnesses all comparison and error expressions are constants plus nonnegative weighted radii. Shrinking radii never increases their bounds; strict passed inequalities remain strict. Nevertheless, a frozen sink witness can have Eminus(0)=C0-sum mu_q c_q>0. At zero the actual error is zero; a witness optimized for a larger box may trade an inferior intercept for smaller uncertain coefficients. A unit vector on a nominally maximal sink form restores the exact zero bound when reoptimized at zero. Frozen-witness infeasibility is therefore not intrinsic model infeasibility.

## 5. Finite catalog

For each dimension, retain only levels from 0,1/4,1/2,1 that do not exceed that coordinate's declared domain radius. Keep the levels' original indices ell_h in {0,1,2,3}, with score sum_h h*ell_h and the original lexicographic tie-break. Freeze all maximum-box guard and sink mixtures. Enumerate every admissible catalog vector and check the exact inequalities and a global target. Return the passing vector with maximal score and then lexicographically maximal indices. Because every vector is checked once, this is an exact optimum over that catalog and those fixed inequalities. If none passes, that restricted feasible set is empty. It does not optimize continuous boxes, all possible witnesses, execution speed, or physical abstraction implementation costs. The enumeration has product_h |L_h| candidates, where L_h contains the catalog levels not exceeding the h-th declared radius; it is at most 4^k and is deliberately small-dimensional.

## 6. Why local error without order control is insufficient

Take M>=2 and 0<epsilon<1/2. Jobs A,B share one resource, IDs A<B. A is released at 1 with service M. B is released at 1+epsilon+2epsilon*theta with service 1, theta in [-1,1]. Job T depends on B, uses a private resource, and has service M. Services/releases satisfy the model assumptions.

At theta=0, A precedes B, so C0=2M+2. At theta=-1, B arrives at 1-epsilon and precedes A. B completes at 2-epsilon. Both A and T then finish at M+2-epsilon, giving global deviation M+epsilon despite a local release perturbation of only 2epsilon. Their ratio is unbounded as M grows. In the fixed nominal graph, A still blocks B: throughout the box, 1+M >= 1+3epsilon under the chosen constraints. Hence that candidate makespan is constant and its error bound is zero. The guard A_arrival<=B_arrival instead has upper bound epsilon>0 and refuses. This is an explicit instance of a known timing-anomaly boundary, not a claim that scheduling anomalies are new.

## 7. Independent joins separate selectors from resource order

For m>=1, use a prefix job of service 5. For each h add three private preparations, all depending on the prefix, with services 2, 9/4+theta_h and 9/4-theta_h. Add unit-service bank jobs A_h depending on the first and B_h depending on the other two; A_h has smaller ID, and each pair has its own bank. There are 1+5m jobs and theta in [-1,1]^m.

A_h is ready at 7; B_h is ready at 29/4+|theta_h|, so the bank order is invariant. At each nonzero theta_h, the sign chooses B_h's maximizing preparation. The 2^m open orthants realize 2^m distinct vectors of these designated readiness selectors, not distinct resource orders. Other internal maxima need not have only these patterns.

A_h completes at 8; B_h completes at max(9,33/4+theta_h,33/4-theta_h). Thus C=max(9,max_h(33/4+|theta_h|)), with nominal/minimum 9 and maximum 37/4. Its exact error is 1/4. Each guard has a half/half two-form witness.

Source, prefix arrival and prefix completion contribute three retained forms. In each five-job block, the first four jobs each have one arrival and one completion form; the last has two arrival and three completion forms, hence thirteen forms per block. The sink retains constant 9 and the 2m signed coordinate forms; none pairwise dominates another over the box. Total forms are 15m+4, the largest frontier is 2m+1, vertices 10m+4, and edges 22m+3. Dense coefficients need m+1 scalars per form, so this is quadratic scalar storage, not a linear bit bound. The separation makes no runtime prediction for another symbolic scheduler implementation.

## 8. Strict comparison of compact affine DAGs

This result concerns arbitrary compact affine-weighted acyclic graphs with unbounded parameter dimension, a broader class than the finite job interface and its implementation limits.

**Theorem.** Deciding whether F_u(theta)<F_v(theta) throughout a rational closed box is coNP-complete for source-to-sink longest-path functions. Hardness holds with strictly positive weights on every edge throughout the box.

**Hardness.** For a three-literal CNF with n>=3 variables and distinct variables per clause, use theta in [-1,1]^n and write each literal as s*theta_i, s in {-1,1}. Define

    F_u = 2n + sum_i |theta_i|,
    F_v = max(3n, max_clauses [3n-1-sum_literals s*theta_i]).

Realize F_u by n serial diamonds, with branch weights 2+theta_i and 2-theta_i. Subdivide each branch into two edges of half the weight to obtain simple-graph branches, each edge at least 1/2. Realize F_v by one separate two-edge path per clause form and one for constant 3n, splitting each weight equally. A clause form is at least 3n-4>0. Size and encoding are polynomial.

Every box point satisfies F_u<=3n<=F_v. Equality requires all |theta_i|=1 and all clause sums >=-1. At Boolean points a clause sum is -3 precisely for an unsatisfied clause, and otherwise is at least -1. Therefore equality somewhere is equivalent to satisfiability. Universal strict inequality is equivalent to unsatisfiability, proving coNP-hardness using the standard NP-completeness of three-literal satisfiability.

**Membership.** A counterexample chooses a left source-to-sink path p and a point at which p(theta)>=F_v(theta). Introduce right-graph potentials t_w with source zero, t_w>=t_z+weight_zw(theta) for each edge in its source-to-sink subgraph, t_sink<=p(theta), and the box constraints. This polynomial-size rational LP is feasible exactly when the chosen path dominates the right longest-path value somewhere. A feasible rational linear system has a polynomial-encoding rational feasible point. The path and that point/potential assignment are a polynomially checkable witness. Conversely, if F_u>=F_v somewhere, choose a maximizing left path and the actual longest-path potentials. Thus the complement is in NP.

The result explains why a polynomial-size LP for explicit envelopes does not imply polynomial work in every compact graph. The finite Boolean checks test the reduction algebra but do not prove this complexity statement.

## 9. Exact small oracle and evidence boundary

For one or two dimensions with positive radii, take all box boundaries and all equality hyperplanes of right-hand forms. Their intersections include every vertex of every cell where the right envelope is affine. In such a cell the left envelope minus that affine function is convex, hence its maximum is attained at a vertex of the compact cell. Enumerating the arrangement vertices, retaining points inside the box, and evaluating rationally therefore obtains the true maximum. Degenerate parallel/coincident lines add no new necessary vertices; box corners are explicitly included.

Corner-only checking is not sufficient: 3/4-|theta| equals -1/4 at the two endpoints but has maximum 3/4 at zero. The exact arrangement oracle includes that interior point. The shipped 2,089 problems exercise this distinct optimization argument; agreement is finite validation, not a replacement for the proof of duality or order self-consistency.

All results are conditional on the exact supplied timing interface. No calibration study establishes that a hardware or production simulator satisfies it. A missing order guard, incomplete left frontier, or nonunit mixture invalidates a certificate; a numerical search success alone establishes nothing. Full-paper comparison with the closest parametric scheduling and event-network methods establishes an incomparable scope: those methods characterize full parameter regions in broader models, whereas this work checks one nominated FCFS order on one box and attaches an exact order-and-error certificate. No dominance, runtime advantage, or production-architecture relevance is inferred.

## 10. A changed order need not change makespan

Let a single bank contain a blocker (release0, service3), A (release1, service1), and B (release1+theta/2, service1), with IDs blocker<A<B and theta in [-1,1]. The blocker begins at zero. Both other jobs are ready by 3/2<3, so after its completion they consume two unit services with no idle gap. B precedes A when theta<0, while A precedes B when theta>=0 by the stated tie rule. Makespan is exactly5 throughout the box. The nominal fixed-order guard A_arrival<=B_arrival has contrast -theta/2 and exact maximum1/2, so it must be refused over the box. The fixed-order sink nevertheless also equals5.

Thus order self-consistency is necessary and sufficient for those resource sequences, not necessary for a small true makespan error. Even ideal comparisons do not make the whole order-and-error procedure a complete decision method for arbitrary error budgets. An order-independent invariant or multiple order regions could accept this model, but those mechanisms are not implemented. This control and the amplification example prevent interpreting every refusal as a large timing error or every constant candidate sink as safe.
