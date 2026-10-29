"""
Check that the app's engine (app/abg_core.py) gives exactly the same results as
the command-line program (abg_analysis.py) across a grid of ~7,000 ABGs.

Run from the repo root:   python tests/check_app_matches_cli.py
Exits with status 1 if anything differs, so the Android build stops on drift.
"""
import builtins, contextlib, io, itertools, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "app"))
import abg_analysis as v2
import abg_core as core

def run_v2(c):
    a = v2.ABGAnalysis()
    a.ph, a.pco2, a.hco3 = c["ph"], c["pco2"], c["hco3"]
    a.pao2 = c["pao2"]; a.fio2 = c["fio2"] if c["pao2"] is not None else None
    a.age = c["age"] if c["pao2"] is not None else None
    if c["na_upfront"]:
        a.na, a.cl, a.albumin = c["na"], c["cl"], c["alb"]
    asked = []; sug = {}
    def fake_input(prompt=""):
        if "PRIMARY" in prompt: asked.append("primary"); sug["rp"] = prompt.split("suggests: ")[1][0] == "y"; return "y" if c["resp_primary"] else "n"
        if "Acute or Chronic" in prompt: asked.append("acuity"); sug["ac"] = "chronic" if "fits chronic" in prompt else "acute"; return "a" if c["acuity"] == "acute" else "c"
        if prompt.strip().startswith("Na"): asked.append("electrolytes"); return str(c["na"])
        if prompt.strip().startswith("Cl"): return str(c["cl"])
        if prompt.strip().startswith("Albumin"): return "" if c["alb"] is None else str(c["alb"])
        raise RuntimeError("unexpected prompt: " + prompt)
    old = builtins.input; builtins.input = fake_input
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            a.analyse()
    finally:
        builtins.input = old
    comp = a.compensation and (a.compensation["verdict"], round(a.compensation["expected"], 1))
    return dict(headline=a.headline, primary=a.primary_disorder, concurrent=a.concurrent, comp=comp,
                ag=a.ag_corrected, chco3=a.corrected_hco3, second=a.second_process,
                pf=a.pf_ratio, pfg=a.pf_grade, aa=a.aa_gradient, aae=a.aa_expected,
                hyp=a.hypoxemia, notes=a.notes, asked=asked, sug=sug)

def run_core(c):
    i = core.Inputs(ph=c["ph"], pco2=c["pco2"], hco3=c["hco3"], pao2=c["pao2"],
                    fio2=c["fio2"] if c["pao2"] is not None else None,
                    age=c["age"] if c["pao2"] is not None else None)
    if c["na_upfront"]:
        i.na, i.cl, i.albumin = c["na"], c["cl"], c["alb"]
    asked = []; sug = {}
    for _ in range(6):
        r = core.analyse(i)
        if r.status != "needs_input": break
        n = r.needs[0]; asked.append("primary" if n == "resp_primary" else n)
        if n == "resp_primary": sug["rp"] = r.suggested_resp_primary
        if n == "acuity": sug["ac"] = r.suggested_acuity
        if n == "resp_primary": i.resp_primary = c["resp_primary"]
        elif n == "acuity": i.acuity = c["acuity"]
        else: i.na, i.cl, i.albumin = c["na"], c["cl"], c["alb"]
    comp = r.compensation and (r.compensation["verdict"], round(r.compensation["expected"], 1))
    return dict(headline=r.headline, primary=r.primary, concurrent=r.concurrent, comp=comp,
                ag=r.ag_corrected, chco3=r.corrected_hco3, second=r.second_process,
                pf=r.pf_ratio, pfg=r.pf_grade, aa=r.aa_gradient, aae=r.aa_expected,
                hyp=r.hypoxemia, notes=r.notes, asked=asked, sug=sug)

cases = []
for ph, pco2 in itertools.product([6.95, 7.10, 7.25, 7.33, 7.37, 7.40, 7.43, 7.48, 7.55, 7.65],
                                  [18, 25, 32, 38, 40, 44, 50, 60, 75]):
    hh = 24 * pco2 / 10 ** (9 - ph)
    if not 2 <= hh <= 60: continue
    for hco3 in (round(hh, 1), round(hh * 1.04, 1), round(hh * 1.25, 1)):         # consistent, and within 6%
        for na_up, (na, cl, alb) in [(True, (140, 104, 3.0)), (False, (140, 100, None)), (False, (138, 110, 4.0))]:
            for rp, ac in [(True, "acute"), (True, "chronic"), (False, "acute")]:
                for pao2, age in [(None, None), (65, 50), (90, None)]:
                    cases.append(dict(ph=ph, pco2=pco2, hco3=hco3, na_upfront=na_up, na=na, cl=cl, alb=alb,
                                      resp_primary=rp, acuity=ac, pao2=pao2, fio2=0.4, age=age))
# DKA + vomiting: normal pH, near-normal HCO3, history says metabolic
for rp in (False, True):
    cases.append(dict(ph=7.41, pco2=37, hco3=23, na_upfront=False, na=140, cl=95, alb=None,
                      resp_primary=rp, acuity="acute", pao2=None, fio2=0.4, age=None))
# HH-inconsistent case (must stop)
cases.append(dict(ph=7.20, pco2=40, hco3=30, na_upfront=False, na=140, cl=100, alb=None,
                  resp_primary=True, acuity="acute", pao2=None, fio2=0.4, age=None))

diffs = {}
stopped = 0
for c in cases:
    hh = 24 * c["pco2"] / 10 ** (9 - c["ph"])
    if abs(c["hco3"] - hh) > 0.06 * hh:
        r = core.analyse(core.Inputs(ph=c["ph"], pco2=c["pco2"], hco3=c["hco3"]))
        assert r.status == "invalid" and r.headline is None and r.primary is None, c
        stopped += 1
        continue
    a, b = run_v2(c), run_core(c)
    has_ma = any("Metabolic acidosis" in d for d in [b["primary"] or ""] + b["concurrent"])
    assert (b["ag"] is not None) == has_ma, ("AG rule broken", c, b)
    assert ("electrolytes" in b["asked"]) == (has_ma and not c["na_upfront"]), ("ask rule broken", c, b)
    rule_ok = globals().get("rule_ok", 0) + 1; globals()["rule_ok"] = rule_ok
    for k in a:
        if a[k] != b[k]:
            diffs.setdefault(k, []).append((c, a[k], b[k]))
print(f"{len(cases)} cases: {stopped} HH-invalid all stopped; {len(cases)-stopped} valid compared")
for k, lst in diffs.items():
    print(f"\n### field '{k}': {len(lst)} differences; first 3:")
    for c, x, y in lst[:3]:
        print(f"  ph={c['ph']} pco2={c['pco2']} hco3={c['hco3']}  v2={x!r}\n{' '*30}core={y!r}")
print(f"AG-only-in-MA rule held in {rule_ok} valid cases")
if diffs:
    sys.exit(1)
print("NO DIFFERENCES")
