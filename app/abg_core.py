"""
abg_core.py - UI-free ABG engine. Logic mirrors abg_analysis.py v2.0.

analyse(inp) is a pure function: the same Inputs always give the same Result.
It never prompts. When the analysis needs something the user has not supplied,
it returns status="needs_input" and lists what is missing in Result.needs:

    "resp_primary"  -> set Inputs.resp_primary (True/False) and call again
    "acuity"        -> set Inputs.acuity ("acute"/"chronic") and call again
    "electrolytes"  -> set Inputs.na and Inputs.cl (albumin optional) and call again

status="invalid" means the values fail Henderson-Hasselbalch (HCO3 more than 6% off
24 x pCO2 / [H+]). Nothing is interpreted; the caller must have the values re-entered.

Electrolytes are requested, and the anion gap calculated, only when a metabolic
acidosis has to be classified (HAGMA vs NAGMA).
"""

from dataclasses import dataclass, field
from typing import List, Optional

NORMAL_PH = (7.35, 7.45)
# Midpoint thresholds (as v1): any deviation is examined, so a masked mixed
# disorder (e.g. HAGMA hidden by metabolic alkalosis at near-normal HCO3) is not missed
PCO2_MID, PCO2_TOL = 40, 2     # respiratory process if pCO2 outside 38-42
HCO3_MID = 24                  # metabolic acidosis if HCO3 < 24, alkalosis if > 24
AG_NORMAL = 12
# Corrected HCO3 = HCO3 + (AG - 12): the HCO3 expected if the anion-gap acid were removed.
# A deliberately wide grey zone: this is a qualitative flag, not a precise measurement.
CORR_HCO3_HIGH = 28            # above -> consider concurrent metabolic alkalosis
CORR_HCO3_LOW = 20             # below -> consider concurrent non-gap acidosis
COMP_TOL = 2

RESP_RATIOS = {
    "acidosis":  {"acute": 1.0, "chronic": 3.5},
    "alkalosis": {"acute": 2.0, "chronic": 5.0},
}

CAUSES = {
    "Respiratory alkalosis": [
        "Pain", "Anxiety", "Fever", "CVA", "Meningitis/Encephalitis",
        "Tumor", "Trauma", "High altitude", "Pneumonia", "Pulmonary edema",
        "Aspiration", "Severe anemia", "Pregnancy", "Salicylates",
        "Cardiac failure", "Progesterone", "Hemothorax", "Flail chest",
        "Pulmonary embolism", "Sepsis", "Hepatic failure",
        "Mechanical hyperventilation", "Heat exposure",
    ],
    "Respiratory acidosis": [
        "Anesthetics", "Morphine", "Sedatives", "Stroke", "Infection",
        "Airway obstruction", "Asthma", "COPD", "Pneumoconiosis", "ARDS",
        "Barotrauma", "Poliomyelitis", "Kyphoscoliosis", "Myasthenia",
        "Muscular dystrophies", "Obesity", "Hypoventilation",
        "Permissive hypercapnia",
    ],
    "Metabolic alkalosis": [
        "Acute alkali administration", "Milk-alkali syndrome", "Vomiting",
        "Aspiration", "Congenital chloridorrhea", "Villous adenoma",
        "Diuretics", "Posthypercapnic state",
        "Hypercalcemia/Hypoparathyroidism", "Penicillin/carbenicillin",
        "Hypomagnesemia", "Hypokalemia", "Bartter's syndrome",
        "Gitelman's syndrome", "Renal artery stenosis",
        "Accelerated hypertension", "Renin secreting tumor", "Estrogen",
        "Primary aldosteronism", "Adrenal enzyme deficiency",
        "Cushing's syndrome", "Licorice", "Carbenoxolone",
        "Chewer's tobacco", "Liddle's syndrome",
    ],
    "Non gap Metabolic acidosis": [
        "Diarrhea", "External pancreatic or small bowel drainage",
        "Ureterosigmoidostomy / jejunal/ileal loop", "CaCl", "MgSO4",
        "Cholestyramine", "Renal tubular acidosis", "K+ sparing diuretics",
        "Trimethoprim", "Pentamidine", "ACE-I/ARBs", "NSAIDs",
        "Calcineurin inhibitors", "Acid loads",
        "Loss of potential bicarbonate", "Rapid saline administration",
        "Cation exchange resins", "Hippurate",
    ],
    "Anion gap Metabolic acidosis": [
        "Lactic acidosis", "DKA", "Alcoholic ketoacidosis",
        "Starvation ketoacidosis", "Ethylene glycol", "Methanol",
        "Salicylates", "Propylene glycol", "Pyroglutamic acid",
        "Sepsis", "Uremia", "Paraldehyde", "Isoniazid", "Seizures",
    ],
}


@dataclass
class Inputs:
    ph: float
    pco2: float
    hco3: float
    pao2: Optional[float] = None
    fio2: Optional[float] = None          # fraction, 0.21-1.0
    na: Optional[float] = None
    cl: Optional[float] = None
    albumin: Optional[float] = None       # g/dL; uncorrected AG if None
    age: Optional[float] = None
    resp_primary: Optional[bool] = None   # answer to "needs resp_primary"
    acuity: Optional[str] = None          # answer to "needs acuity"


@dataclass
class Result:
    status: str = "ok"                    # ok | needs_input | invalid
    needs: List[str] = field(default_factory=list)
    hh_expected_hco3: Optional[float] = None
    hh_consistent: Optional[bool] = None
    suggested_resp_primary: Optional[bool] = None   # v2.0 "[suggested: y/n]"
    suggested_acuity: Optional[str] = None          # v2.0 "[HCO3 fits acute/chronic]"
    ph_status: Optional[str] = None
    headline: Optional[str] = None
    primary: Optional[str] = None
    concurrent: List[str] = field(default_factory=list)
    compensation: Optional[dict] = None
    ag_raw: Optional[float] = None
    ag_corrected: Optional[float] = None
    ag_albumin_corrected: bool = False
    ag_elevated: Optional[bool] = None
    corrected_hco3: Optional[float] = None
    second_process: Optional[str] = None
    pf_ratio: Optional[float] = None
    pf_grade: Optional[str] = None
    aa_gradient: Optional[float] = None
    aa_expected: Optional[float] = None
    hypoxemia: Optional[str] = None
    notes: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────
def _anion_gap(inp, r):
    r.ag_raw = inp.na - (inp.cl + inp.hco3)
    r.ag_corrected = r.ag_raw
    if inp.albumin is not None:
        r.ag_corrected += 2.5 * (4.0 - inp.albumin)
        r.ag_albumin_corrected = True
    r.ag_elevated = r.ag_corrected > AG_NORMAL
    if r.ag_elevated:
        r.corrected_hco3 = round(inp.hco3 + (r.ag_corrected - AG_NORMAL), 1)
        if r.corrected_hco3 > CORR_HCO3_HIGH:
            r.second_process = ("Consider a concurrent metabolic alkalosis "
                                "(e.g. vomiting, NG aspiration, diuretics)")
        elif r.corrected_hco3 < CORR_HCO3_LOW:
            r.second_process = ("Consider a concurrent non-gap acidosis "
                                "(e.g. saline load, diarrhoea, recovering DKA)")
        else:
            r.second_process = "No second metabolic process suggested"


def _ma_type(inp, r):
    """Name the metabolic acidosis (HAGMA vs NAGMA). The ONLY place the anion gap is calculated.
    Returns None and flags 'electrolytes' if Na/Cl are missing."""
    if inp.na is None or inp.cl is None:
        if "electrolytes" not in r.needs:
            r.needs.append("electrolytes")
        return None
    _anion_gap(inp, r)
    return "Anion gap Metabolic acidosis" if r.ag_elevated else "Non gap Metabolic acidosis"


def _oxygenation(inp, r):
    if inp.pao2 is None or inp.fio2 is None:
        return
    r.pf_ratio = round(inp.pao2 / inp.fio2)
    alveolar = inp.fio2 * (760 - 47) - inp.pco2 / 0.8      # sea level, RQ 0.8
    r.aa_gradient = round(alveolar - inp.pao2, 1)
    if inp.age is not None:
        r.aa_expected = round(inp.age / 4 + 4, 1)

    if inp.pao2 >= 80:   r.hypoxemia = "No hypoxemia"
    elif inp.pao2 >= 60: r.hypoxemia = "Mild hypoxemia"
    elif inp.pao2 >= 40: r.hypoxemia = "Moderate hypoxemia"
    else:                r.hypoxemia = "Severe hypoxemia"

    if r.pf_ratio > 300:   r.pf_grade = "Normal"
    elif r.pf_ratio > 200: r.pf_grade = "Mild impairment (Berlin mild ARDS range)"
    elif r.pf_ratio > 100: r.pf_grade = "Moderate impairment (Berlin moderate ARDS range)"
    else:                  r.pf_grade = "Severe impairment (Berlin severe ARDS range)"


# ─────────────────────────────────────────────
# main entry point
# ─────────────────────────────────────────────
def analyse(inp: Inputs) -> Result:
    r = Result()

    # 1. Henderson-Hasselbalch validity: HCO3 = 24 x pCO2 / [H+]
    hh = 24 * inp.pco2 / 10 ** (9 - inp.ph)
    r.hh_expected_hco3 = round(hh, 1)
    r.hh_consistent = abs(inp.hco3 - hh) <= 0.06 * hh
    if not r.hh_consistent:
        # Hard stop: an internally inconsistent gas is not interpreted at all
        r.status = "invalid"
        r.notes.append(f"Values not internally consistent: expected HCO3 ≈ {hh:.1f} from this "
                       "pH and pCO2 (Henderson-Hasselbalch). Possible transcription error. "
                       "Re-check and re-enter.")
        return r

    # 2. Oxygenation (anion gap is only calculated if a metabolic acidosis is found)
    _oxygenation(inp, r)

    # 3. Classify pH and each component
    ph, pco2, hco3 = inp.ph, inp.pco2, inp.hco3
    if ph < NORMAL_PH[0]:   r.ph_status = "Acidemia"
    elif ph > NORMAL_PH[1]: r.ph_status = "Alkalemia"
    else:                   r.ph_status = "Normal pH"

    resp_abn = ("acidosis" if pco2 > PCO2_MID + PCO2_TOL else
                "alkalosis" if pco2 < PCO2_MID - PCO2_TOL else None)
    met_abn = ("acidosis" if hco3 < HCO3_MID else
               "alkalosis" if hco3 > HCO3_MID else None)
    resp_lean = "acidosis" if pco2 > 40 else "alkalosis" if pco2 < 40 else None
    met_lean = "acidosis" if hco3 < 24 else "alkalosis" if hco3 > 24 else None

    # 4. Normal acid-base status
    if r.ph_status == "Normal pH" and not resp_abn and not met_abn:
        r.headline = "Normal acid-base status"
        return r

    # 5. Which process is primary?
    if r.ph_status == "Acidemia":      want = "acidosis"
    elif r.ph_status == "Alkalemia":   want = "alkalosis"
    else:                              want = "acidosis" if ph < 7.40 else "alkalosis" if ph > 7.40 else None

    candidates = []
    if resp_abn and (r.ph_status == "Normal pH" or resp_abn == want):
        candidates.append("resp")
    if met_abn and (r.ph_status == "Normal pH" or met_abn == want):
        candidates.append("met")

    if len(candidates) == 2:
        r.suggested_resp_primary = want is None or resp_abn == want
        if inp.resp_primary is None:
            r.needs.append("resp_primary")
            r.status = "needs_input"
            return r
        primary = "resp" if inp.resp_primary else "met"
    elif len(candidates) == 1:
        primary = candidates[0]
    else:
        # borderline: whichever deviation explains the pH
        r_fit, m_fit = resp_lean == want, met_lean == want
        if r_fit != m_fit:
            primary = "resp" if r_fit else "met"
        else:
            primary = "resp" if abs(pco2 - 40) / 40 >= abs(hco3 - 24) / 24 else "met"

    if primary == "resp" and resp_lean is None:
        primary = "met"

    # 6. Respiratory primary
    if primary == "resp":
        direction = resp_lean
        ratios = RESP_RATIOS[direction]
        exp = {k: 24 + (pco2 - 40) / 10 * v for k, v in ratios.items()}
        r.suggested_acuity = ("chronic" if abs(hco3 - exp["chronic"]) < abs(hco3 - exp["acute"])
                              else "acute")
        if inp.acuity is None:
            r.needs.append("acuity")
            r.status = "needs_input"
            return r
        r.primary = f"{inp.acuity.capitalize()} Respiratory {direction}"
        expected = exp[inp.acuity]
        r.compensation = {
            "param": "HCO3", "expected": round(expected, 1), "actual": hco3,
            "low": round(expected - COMP_TOL, 1), "high": round(expected + COMP_TOL, 1),
            "formula": f"24 + {ratios[inp.acuity]} x (pCO2 - 40)/10 +/- {COMP_TOL}",
        }
        if hco3 < expected - COMP_TOL:
            r.compensation["verdict"] = "HCO3 lower than expected"
            r.concurrent.append(_ma_type(inp, r) or "Metabolic acidosis (type pending)")
        elif hco3 > expected + COMP_TOL:
            r.compensation["verdict"] = "HCO3 higher than expected"
            r.concurrent.append("Metabolic alkalosis")
        else:
            r.compensation["verdict"] = "Appropriate"

    # 7. Metabolic primary
    else:
        direction = met_lean or "acidosis"          # exactly as v2.0
        if direction == "acidosis":
            r.primary = _ma_type(inp, r) or "Metabolic acidosis (type pending)"
            expected = 1.5 * hco3 + 8
            formula = "Winter's: 1.5 x HCO3 + 8"
        else:
            r.primary = "Metabolic alkalosis"
            expected = 40 + 0.7 * (hco3 - 24)
            formula = "40 + 0.7 x (HCO3 - 24)"
        r.compensation = {
            "param": "pCO2", "expected": round(expected, 1), "actual": pco2,
            "low": round(expected - COMP_TOL, 1), "high": round(expected + COMP_TOL, 1),
            "formula": f"{formula} +/- {COMP_TOL}",
        }
        if pco2 > expected + COMP_TOL:
            r.compensation["verdict"] = "pCO2 higher than expected"
            r.concurrent.append("Respiratory acidosis")
        elif pco2 < expected - COMP_TOL:
            r.compensation["verdict"] = "pCO2 lower than expected"
            r.concurrent.append("Respiratory alkalosis")
        else:
            r.compensation["verdict"] = "Appropriate"

    if r.needs:
        r.status = "needs_input"
        return r

    # 9. Headline
    if r.concurrent:
        r.headline = f"{r.primary} with concurrent " + " and ".join(d.lower() for d in r.concurrent)
    else:
        c = r.compensation
        comp_abn = met_abn if c["param"] == "HCO3" else resp_abn
        full = r.ph_status == "Normal pH" and comp_abn is not None
        r.headline = f"{r.primary} with {'full' if full else 'appropriate'} compensation"

    return r


def causes_for(r: Result) -> List[str]:
    """Sorted, de-duplicated differential list for the disorders in a result."""
    out = []
    for d in [r.primary] + r.concurrent:
        if not d:
            continue
        for key, items in CAUSES.items():
            if key.lower() in d.lower():
                out.extend(i for i in items if i not in out)
    return sorted(out)
