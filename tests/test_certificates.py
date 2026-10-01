import copy,itertools,json,unittest
from pathlib import Path
from fractions import Fraction as Q
from simcert.algebra import *
from simcert.model import *
from simcert.checker import check
from simcert.cases import shared_prefix,unstable,make_job,af

ROOT=Path(__file__).resolve().parents[1]

class Certificates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads((ROOT/"inputs/case-001.json").read_text())
        cls.cert=json.loads((ROOT/"results/models/case-001.json").read_text())["certificate"]
    def test_good_certificate(self):self.assertTrue(check(self.model,self.cert)["certified"])
    def test_required_result_coverage(self):
        self.assertEqual({p.stem for p in (ROOT/"results/models").glob("*.json")},
                         {f"case-{i:03d}" for i in range(48)})
        self.assertEqual({p.stem for p in (ROOT/"results/oracles").glob("*.json")},
                         {f"oracle-{i:04d}" for i in range(2089)})
        self.assertEqual({p.stem for p in (ROOT/"results/allocation").glob("*.json")},
                         {"case-007","case-019","case-031","case-043"})
        self.assertEqual({p.stem for p in (ROOT/"results/structure").glob("*.json")},
                         {f"join-{m}" for m in range(1,7)})
        self.assertEqual({p.stem for p in (ROOT/"inputs").glob("*.json")},
                         {f"case-{i:03d}" for i in range(48)}|{f"join-{m}" for m in range(1,7)})
    def test_reference_audit(self):
        from audit_references import audit
        report=audit()
        self.assertEqual(report["status"],"pass")
        self.assertEqual(report["references"],65)
        self.assertEqual(report["cited_references"],65)
        self.assertEqual(report["calibration_groups"],{"same venue":12,"influential":5,"adjacent":5})

    def test_generated_inputs_are_byte_exact_and_mutations_are_detected(self):
        from input_audit import audit
        report=audit()
        self.assertEqual(report["generated_inputs"],54)
        self.assertEqual(report["byte_equal_inputs"],54)
        self.assertTrue(report["temporary_directory_generation"])
        self.assertTrue(report["coefficient_mutation_detected"])

    def test_temporary_generation_leaves_retained_inputs_unchanged(self):
        from input_audit import audit
        self.assertTrue(audit()["source_inputs_unchanged"])

    @staticmethod
    def trivial_allocation_case(domain,case_id):
        k=len(domain);zeros=["0"]*k
        model={"case_id":case_id,"family":"allocation-regression","domain":list(domain),
          "jobs":[{"id":0,"resource":"r","deps":[],"release":["0"]+zeros,"service":["1"]+zeros}]}
        certificate={"radii":list(domain),"orders":{"r":[0]},"guards":[],"lower_weights":["1"]}
        return model,certificate

    def test_allocate_filters_half_domain_and_preserves_level_score(self):
        from campaign import allocate
        model,certificate=self.trivial_allocation_case(["1/2"],"allocation-domain-half")
        result=allocate(model,certificate,target=Q(1))
        self.assertEqual(len(result["candidates"]),3)
        self.assertEqual([r["radii"] for r in result["candidates"]],[["0"],["1/4"],["1/2"]])
        self.assertEqual(result["selected"]["radii"],["1/2"])
        self.assertEqual(result["selected"]["indices"],[2])
        self.assertEqual(result["selected"]["score"],2)
        self.assertEqual(result["selected"]["bound"],"0")

    def test_allocate_zero_domain_has_one_zero_entry(self):
        from campaign import allocate
        model,certificate=self.trivial_allocation_case(["0"],"allocation-domain-zero")
        result=allocate(model,certificate,target=Q(1))
        self.assertEqual(len(result["candidates"]),1)
        self.assertEqual(result["selected"],{"indices":[0],"radii":["0"],"score":0,"feasible":True,"bound":"0"})

    def test_allocate_filters_mixed_domains_per_coordinate(self):
        from campaign import allocate
        model,certificate=self.trivial_allocation_case(["0","1/2","1"],"allocation-domain-mixed")
        result=allocate(model,certificate,target=Q(1))
        self.assertEqual(len(result["candidates"]),12)
        self.assertEqual(result["selected"]["indices"],[0,2,3])
        self.assertEqual(result["selected"]["radii"],["0","1/2","1"])
        self.assertEqual(result["selected"]["score"],13)
        self.assertEqual(result["selected"]["bound"],"0")

    def test_reduction_equality_characterization(self):
        from reduction_check import formulas,evaluate
        data=json.loads((ROOT/"results/reduction.json").read_text())
        self.assertEqual(len(data["formulas"]),512)
        assignments=0;satisfiable=0
        for row,(n,cnf) in zip(data["formulas"],formulas()):
            self.assertEqual(row["variables"],n)
            self.assertEqual(row["clauses"],[list(c) for c in cnf])
            result=evaluate(n,cnf)
            for key,value in result.items():self.assertEqual(row[key],value)
            assignments+=result["assignments"]
            satisfiable+=result["satisfying_assignments"]>0
        self.assertEqual(data["summary"],{"formulas":512,"assignments":assignments,
                         "satisfiable_formulas":satisfiable,"mismatches":0})
    def bad(self,mutate):
        c=copy.deepcopy(self.cert);mutate(c)
        with self.assertRaises((ValueError,KeyError,TypeError)):check(self.model,c)
    def test_negative_weight(self):self.bad(lambda c:c["guards"][0]["weights"][0].__setitem__(0,"-1"))
    def test_mass_not_one(self):self.bad(lambda c:c["guards"][0]["weights"][0].__setitem__(0,"2"))
    def test_missing_guard(self):self.bad(lambda c:c["guards"].pop())
    def test_missing_left_coverage(self):self.bad(lambda c:c["guards"][0]["weights"].pop())
    def test_extra_guard(self):self.bad(lambda c:c["guards"].append(c["guards"][0]))
    def test_changed_tie_semantics(self):self.bad(lambda c:c["guards"][0]["guard"].__setitem__("strict",True))
    def test_wrong_orders(self):self.bad(lambda c:c["orders"]["bank0"].reverse())
    def test_box_outside_domain(self):self.bad(lambda c:c["radii"].__setitem__(0,"2"))
    def test_float_is_not_rational_input(self):self.bad(lambda c:c["radii"].__setitem__(0,0.5))
    def test_nonfinite(self):self.bad(lambda c:c["radii"].__setitem__(0,"nan"))
    def test_negative_radius(self):self.bad(lambda c:c["radii"].__setitem__(0,"-1"))
    def test_oversized_input(self):self.bad(lambda c:c["radii"].__setitem__(0,"1"*3100))
    def test_wrong_witness_dimension(self):self.bad(lambda c:c["lower_weights"].append("0"))
    def test_zero_service_rejected(self):
        m=copy.deepcopy(self.model);m["jobs"][0]["service"]=["0","0","0"]
        with self.assertRaises(ValueError):validate(m)
    def test_cycles_rejected(self):
        m=copy.deepcopy(self.model);m["jobs"][0]["deps"]=[m["jobs"][-1]["id"]]
        with self.assertRaises(ValueError):validate(m)
    def test_all_stored_certificates_and_dynamic_points(self):
        for file in sorted((ROOT/"results/models").glob("*.json")):
            data=json.loads(file.read_text());model=json.loads((ROOT/"inputs"/file.name).read_text())
            self.assertEqual(check(model,data["certificate"]),data["verdict"])
            n=simulate(model,[0]*len(model["domain"]))
            for sample in data["samples"]:
                a=simulate(model,sample["point"])
                self.assertEqual(str(a["makespan"]),sample["makespan"])
                self.assertEqual(a["orders"]==n["orders"],sample["same_order"])
    def test_all_oracle_witnesses(self):
        for file in sorted((ROOT/"results/oracles").glob("*.json")):
            d=json.loads(file.read_text());k=len(d["radii"])
            ps=[form(x,k) for x in d["left"]];qs=[form(x,k) for x in d["right"]];b=tuple(map(Q,d["radii"]))
            bound=max(mixture_bound(p,qs,w,b) for p,w in zip(ps,d["weights"]))
            (exact,pt),nv=exact_small_oracle(ps,qs,b)
            self.assertEqual(str(bound),d["bound"]);self.assertEqual(str(exact),d["oracle"])
            self.assertGreaterEqual(bound,exact)
    def test_all_catalog_candidates_and_optima(self):
        for file in sorted((ROOT/"results/allocation").glob("*.json")):
            data=json.loads(file.read_text());model=json.loads((ROOT/"inputs"/file.name).read_text())
            original=json.loads((ROOT/"results/models"/file.name).read_text())["certificate"]
            feasible=[]
            self.assertEqual(len(data["candidates"]),4**len(model["domain"]))
            for row in data["candidates"]:
                c=copy.deepcopy(original);c["radii"]=row["radii"]
                v=check(model,c,data["target"])
                self.assertEqual(v["certified"],row["feasible"])
                self.assertEqual(v["global_bound"],row["bound"])
                self.assertEqual(row["score"],sum((i+1)*j for i,j in enumerate(row["indices"])))
                if v["certified"]:feasible.append(row)
            best=max(feasible,key=lambda x:(x["score"],tuple(x["indices"]))) if feasible else None
            self.assertEqual(best,data["selected"])
            from campaign import allocate
            self.assertEqual(allocate(model,original,Q(data["target"])),data)
    def test_independent_join_structure(self):
        for file in sorted((ROOT/"results/structure").glob("*.json")):
            d=json.loads(file.read_text());m=d["m"];model=json.loads((ROOT/"inputs"/file.name).read_text())
            self.assertEqual(d["jobs"],1+5*m);self.assertEqual(len(d["samples"]),2**m)
            self.assertEqual(check(model,d["certificate"]),d["verdict"])
            self.assertEqual(Q(d["verdict"]["global_bound"]),Q(1,4))
            nom=simulate(model,[0]*m)
            for row in d["samples"]:
                a=simulate(model,row["point"])
                self.assertEqual(a["orders"],nom["orders"]);self.assertEqual(str(a["makespan"]),row["makespan"])
    def test_interior_maximum_not_box_corner(self):
        ps=[(Q(3,4),Q(0))];qs=[(Q(0),Q(1)),(Q(0),Q(-1))]
        (true,point),_=exact_small_oracle(ps,qs,[Q(1)])
        corners=[envelope(ps,[x])-envelope(qs,[x]) for x in [-1,1]]
        self.assertEqual(true,Q(3,4));self.assertEqual(max(corners),Q(-1,4));self.assertEqual(point,(Q(0),))
    def test_monotone_coefficients_need_mixture(self):
        p=(Q(3),Q(1),Q(1));qs=[(Q(13,4),Q(2),Q(0)),(Q(13,4),Q(0),Q(2))]
        self.assertEqual(mixture_bound(p,qs,[Q(1,2),Q(1,2)],[Q(1),Q(1)]),Q(-1,4))
        self.assertEqual(single_path_bound([p],qs,[Q(1),Q(1)]),Q(7,4))
    def test_order_change_amplification(self):
        m=unstable();nom=simulate(m,[0]);alt=simulate(m,[-1])
        self.assertEqual(nom["makespan"],Q(202));self.assertEqual(alt["makespan"],Q(10199,100))
        self.assertNotEqual(nom["orders"],alt["orders"])
    def test_strict_tie_guard_is_necessary(self):
        # Higher ID nominally first, but lower ID wins at equality.
        m={"domain":["1"],"jobs":[make_job(1,"bank",[],1,[0],1,af(2,0)),make_job(2,"bank",[],1,[0],1,af(Q(3,2),Q(1,2)))]}
        nominal,fs,guards,stats=prepare(m)
        self.assertTrue(guards[0]["strict"])
        c={"radii":["1"],"orders":nominal["orders"],"guards":[{"guard":guards[0],"weights":[["1"]]}],"lower_weights":["1"]}
        self.assertFalse(check(m,c)["certified"])
        self.assertNotEqual(simulate(m,[1])["orders"],nominal["orders"])
    def test_frontier_cap_is_fail_closed(self):
        with self.assertRaises(OverflowError):reduce_forms([(Q(0),Q(1)),(Q(0),Q(-1))],[Q(1)],cap=1)
    def test_complete_frontier_reconstruction(self):
        m=shared_prefix(2,1);nom,fs,guards,stats=prepare(m)
        for point in itertools.product([-1,0,1],repeat=2):
            actual=simulate(m,point)
            for i,t in actual["finish"].items():self.assertEqual(envelope(fs[f"c{i}"],point),t)


class BoundaryControlTests(unittest.TestCase):
    def test_changed_order_can_keep_makespan_constant(self):
        from boundary_check import evaluate
        stored=json.loads((ROOT/"results/boundary-control.json").read_text())
        current=evaluate()
        for key,value in current.items():self.assertEqual(value,stored[key])

if __name__=="__main__":unittest.main()
