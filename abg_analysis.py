"""
ABG Analysis Tool - v2.0
Author: Dr. Shoubhik Banerjee

Interactive command-line arterial blood gas interpreter.

Steps:
  1. pH -> acidemia / alkalemia / normal
  2. Primary disorder (worked out from pH; asked only when ambiguous)
  3. Expected compensation -> appropriate, or a concurrent disorder
  4. Anion gap (albumin-corrected) and delta ratio
  5. Oxygenation: P/F ratio, A-a gradient, hypoxemia grade
  6. Optional walk-through of possible causes

Changes from v1:
  - Metabolic alkalosis compensation uses 40 + 0.7 x (HCO3 - 24),
    not Winter's formula (which applies only to metabolic acidosis)
  - Normal ranges: pH 7.35-7.45, pCO2 35-45, HCO3 22-26
  - Anion gap checked whenever Na/Cl are given (detects hidden AG acidosis)
  - Hypoxemia graded mild 60-79 / moderate 40-59 / severe <40
  - Henderson-Hasselbalch mismatch warns instead of forcing re-entry
"""

NORMAL_PH = (7.35, 7.45)
NORMAL_PCO2 = (35, 45)
NORMAL_HCO3 = (22, 26)
AG_NORMAL = 12
COMP_TOL = 2          # +/- tolerance on expected compensation

# ─────────────────────────────────────────────
# DIFFERENTIALS DATABASE
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# INPUT UTILITIES
# ─────────────────────────────────────────────
def get_float(prompt, low, high, optional=False):
    """Prompt until a number in [low, high] is entered (or Enter, if optional)."""
    while True:
        raw = input(prompt).strip()
        if optional and raw == "":
            return None
        try:
            val = float(raw)
        except ValueError:
            print("    Please enter a numeric value." + (" (Enter to skip)" if optional else ""))
            continue
        if val < low:
            print(f"    Value too low (min {low})")
        elif val > high:
            print(f"    Value too high (max {high})")
        else:
            return val


def get_choice(prompt, valid_options):
    """Prompt until one of valid_options is entered."""
    while True:
        ans = input(prompt).strip().lower()
        if ans in valid_options:
            return ans
        print(f"    Please enter one of: {', '.join(valid_options)}")


# ─────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────
class ABGAnalysis:
    """One complete ABG analysis. Call collect_inputs(), analyse(), display()."""

    def __init__(self):
        # Inputs
        self.ph = self.pco2 = self.hco3 = None
        self.pao2 = self.fio2 = None
        self.na = self.cl = self.albumin = self.age = None

        # Results
        self.ph_status = None
        self.primary_disorder = None
        self.concurrent = []          # list of concurrent disorder names
        self.compensation = None      # dict: param, expected, low, high, actual, verdict, formula
        self.headline = None
        self.notes = []
        self.ag_raw = self.ag_corrected = self.ag_elevated = None
        self.delta_ratio = self.delta_interp = None
        self.pf_ratio = self.aa_gradient = self.aa_expected = None
        self.hypoxemia = self.pf_grade = None

    # ──────────────────────────────────────────
    # INPUT
    # ──────────────────────────────────────────
    def collect_inputs(self):
        print("\n  ── Enter ABG Values ──")
        while True:
            self.ph = get_float("    pH          : ", 6.5, 7.8)
            self.pco2 = get_float("    pCO2 (mmHg) : ", 5, 150)
            self.hco3 = get_float("    HCO3 (mEq/L): ", 2, 60)
            expected = self._hh_expected_hco3()
            if abs(self.hco3 - expected) <= 0.06 * expected:
                break
            print(f"    ⚠  Expected HCO3 ≈ {expected:.1f} from this pH & pCO2 "
                  "(Henderson-Hasselbalch). Possible transcription error.")
            if get_choice("    Re-enter values? (y/n): ", ("y", "n")) == "n":
                self.notes.append(f"Values not internally consistent (expected HCO3 ≈ {expected:.1f}).")
                break

        self.pao2 = get_float("    pO2 (mmHg)  : ", 1, 700, optional=True)
        if self.pao2 is not None:
            self.fio2 = get_float("    FiO2 (%)    : ", 21, 100) / 100

        print("\n  ── Electrolytes for anion gap (Enter to skip) ──")
        self.na = get_float("    Na (mEq/L)     : ", 100, 180, optional=True)
        if self.na is not None:
            self.cl = get_float("    Cl (mEq/L)     : ", 70, 140)
            self.albumin = get_float("    Albumin (g/dL) : ", 0.5, 6.0, optional=True)

        if self.pao2 is not None:
            self.age = get_float("\n    Age (years, for A-a gradient; Enter to skip): ", 0, 120, optional=True)

    def _hh_expected_hco3(self):
        # [H+] (nmol/L) = 24 x pCO2 / HCO3
        return 24 * self.pco2 / (10 ** (9 - self.ph))

    # ──────────────────────────────────────────
    # ANION GAP
    # ──────────────────────────────────────────
    def _ensure_electrolytes(self):
        """Ask for Na/Cl if a metabolic acidosis needs classifying and they were skipped."""
        if self.na is None:
            print("\n  ── Metabolic acidosis found: Na and Cl needed to classify it ──")
            self.na = get_float("    Na (mEq/L)     : ", 100, 180)
            self.cl = get_float("    Cl (mEq/L)     : ", 70, 140)
            self.albumin = get_float("    Albumin (g/dL, Enter to skip): ", 0.5, 6.0, optional=True)
            self._calculate_anion_gap()

    def _calculate_anion_gap(self):
        if self.na is None or self.cl is None:
            return
        self.ag_raw = self.na - (self.cl + self.hco3)
        self.ag_corrected = self.ag_raw
        if self.albumin is not None:
            self.ag_corrected += 2.5 * (4.0 - self.albumin)
        self.ag_elevated = self.ag_corrected > AG_NORMAL

        self.delta_ratio = self.delta_interp = None
        if self.ag_elevated:
            delta_hco3 = 24 - self.hco3
            if delta_hco3 > 0:
                self.delta_ratio = round((self.ag_corrected - AG_NORMAL) / delta_hco3, 2)
                if self.delta_ratio < 0.4:
                    self.delta_interp = "Non-gap metabolic acidosis predominates"
                elif self.delta_ratio < 1.0:
                    self.delta_interp = "Mixed anion-gap + non-gap metabolic acidosis"
                elif self.delta_ratio <= 2.0:
                    self.delta_interp = "Pure anion-gap metabolic acidosis"
                else:
                    self.delta_interp = ("Anion-gap acidosis + concurrent metabolic alkalosis "
                                         "(or chronic respiratory acidosis)")
            else:
                self.delta_interp = "Raised AG with HCO3 ≥ 24: concurrent metabolic alkalosis likely"

    def _met_acidosis_type(self):
        self._ensure_electrolytes()
        return "Anion gap Metabolic acidosis" if self.ag_elevated else "Non gap Metabolic acidosis"

    # ──────────────────────────────────────────
    # OXYGENATION
    # ──────────────────────────────────────────
    def _analyse_oxygenation(self):
        if self.pao2 is None:
            return
        self.pf_ratio = round(self.pao2 / self.fio2)
        pao2_alveolar = self.fio2 * (760 - 47) - self.pco2 / 0.8   # sea level, RQ 0.8
        self.aa_gradient = round(pao2_alveolar - self.pao2, 1)
        if self.age is not None:
            self.aa_expected = round(self.age / 4 + 4, 1)

        if self.pao2 >= 80:   self.hypoxemia = "No hypoxemia"
        elif self.pao2 >= 60: self.hypoxemia = "Mild hypoxemia"
        elif self.pao2 >= 40: self.hypoxemia = "Moderate hypoxemia"
        else:                 self.hypoxemia = "Severe hypoxemia"

        if self.pf_ratio > 300:   self.pf_grade = "Normal"
        elif self.pf_ratio > 200: self.pf_grade = "Mild impairment (Berlin mild ARDS range)"
        elif self.pf_ratio > 100: self.pf_grade = "Moderate impairment (Berlin moderate ARDS range)"
        else:                     self.pf_grade = "Severe impairment (Berlin severe ARDS range)"

    # ──────────────────────────────────────────
    # CORE ANALYSIS
    # ──────────────────────────────────────────
    def analyse(self):
        self._calculate_anion_gap()
        self._analyse_oxygenation()

        ph, pco2, hco3 = self.ph, self.pco2, self.hco3
        if ph < NORMAL_PH[0]:   self.ph_status = "Acidemia"
        elif ph > NORMAL_PH[1]: self.ph_status = "Alkalemia"
        else:                   self.ph_status = "Normal pH"

        resp_abn = ("acidosis" if pco2 > NORMAL_PCO2[1] else
                    "alkalosis" if pco2 < NORMAL_PCO2[0] else None)
        met_abn = ("acidosis" if hco3 < NORMAL_HCO3[0] else
                   "alkalosis" if hco3 > NORMAL_HCO3[1] else None)
        resp_lean = "acidosis" if pco2 > 40 else "alkalosis" if pco2 < 40 else None
        met_lean = "acidosis" if hco3 < 24 else "alkalosis" if hco3 > 24 else None

        # ── Normal acid-base ──
        if self.ph_status == "Normal pH" and not resp_abn and not met_abn:
            if self.ag_elevated:
                self.headline = "Normal pH, pCO2 and HCO3, but raised anion gap"
                self.concurrent = ["Anion gap Metabolic acidosis", "Metabolic alkalosis"]
                self.notes.append("Suggests a hidden mixed disorder: AG metabolic acidosis "
                                  "offset by metabolic alkalosis.")
            else:
                self.headline = "Normal acid-base status"
            return

        # ── Which process is primary? ──
        if self.ph_status == "Acidemia":    want = "acidosis"
        elif self.ph_status == "Alkalemia": want = "alkalosis"
        else: want = "acidosis" if ph < 7.40 else "alkalosis" if ph > 7.40 else None

        candidates = []
        if resp_abn and (self.ph_status == "Normal pH" or resp_abn == want):
            candidates.append("resp")
        if met_abn and (self.ph_status == "Normal pH" or met_abn == want):
            candidates.append("met")

        if len(candidates) == 1:
            primary = candidates[0]
        elif len(candidates) == 2:
            print(f"\n  pH {ph} ({self.ph_status}) | pCO2 {pco2}: respiratory {resp_abn} | "
                  f"HCO3 {hco3}: metabolic {met_abn}")
            default = "y" if (want is None or resp_abn == want) else "n"
            ans = get_choice(f"  Is Respiratory the PRIMARY disorder? (y/n) [suggested: {default}]: ",
                             ("y", "n"))
            primary = "resp" if ans == "y" else "met"
        else:
            # Borderline values: pick whichever deviation explains the pH
            r_fit, m_fit = resp_lean == want, met_lean == want
            if r_fit != m_fit:
                primary = "resp" if r_fit else "met"
            else:
                primary = "resp" if abs(pco2 - 40) / 40 >= abs(hco3 - 24) / 24 else "met"

        if primary == "resp" and resp_lean:
            self._analyse_resp_primary(resp_lean)
        else:
            self._analyse_met_primary(met_lean or "acidosis")

        # A raised AG matters whatever the primary disorder
        all_dis = [self.primary_disorder] + self.concurrent
        if self.ag_elevated and not any("Metabolic acidosis" in d for d in all_dis):
            self.concurrent.append("Anion gap Metabolic acidosis")
        if (self.delta_ratio is not None and self.delta_ratio > 2
                and "Metabolic alkalosis" not in all_dis):
            self.notes.append("Delta ratio > 2: consider concurrent metabolic alkalosis "
                              "(or pre-existing chronic respiratory acidosis).")

        if self.concurrent:
            self.headline = (f"{self.primary_disorder} with concurrent "
                             + " and ".join(d.lower() for d in self.concurrent))
        else:
            # "Full" only if pH normalised AND the compensating value is itself abnormal
            comp_abn = met_abn if self.compensation["param"] == "HCO3" else resp_abn
            full = self.ph_status == "Normal pH" and comp_abn is not None
            self.headline = f"{self.primary_disorder} with {'full' if full else 'appropriate'} compensation"

    def _analyse_resp_primary(self, direction):
        ratios = {"acidosis": {"acute": 1.0, "chronic": 3.5},
                  "alkalosis": {"acute": 2.0, "chronic": 5.0}}[direction]
        exp = {k: 24 + (self.pco2 - 40) / 10 * r for k, r in ratios.items()}
        suggested = "c" if abs(self.hco3 - exp["chronic"]) < abs(self.hco3 - exp["acute"]) else "a"
        ans = get_choice(f"  Acute or Chronic? (a/c) [HCO3 fits {'chronic' if suggested == 'c' else 'acute'}]: ",
                         ("a", "c"))
        acuity = "acute" if ans == "a" else "chronic"
        self.primary_disorder = f"{acuity.capitalize()} Respiratory {direction}"

        expected = exp[acuity]
        self.compensation = {
            "param": "HCO3", "expected": expected, "actual": self.hco3,
            "low": expected - COMP_TOL, "high": expected + COMP_TOL,
            "formula": f"24 + {ratios[acuity]} x (pCO2 - 40)/10",
        }
        if self.hco3 < expected - COMP_TOL:
            self.compensation["verdict"] = "HCO3 lower than expected"
            self.concurrent.append(self._met_acidosis_type())
        elif self.hco3 > expected + COMP_TOL:
            self.compensation["verdict"] = "HCO3 higher than expected"
            self.concurrent.append("Metabolic alkalosis")
        else:
            self.compensation["verdict"] = "Appropriate"

    def _analyse_met_primary(self, direction):
        if direction == "acidosis":
            self.primary_disorder = self._met_acidosis_type()
            expected = 1.5 * self.hco3 + 8
            formula = "Winter's: 1.5 x HCO3 + 8"
        else:
            self.primary_disorder = "Metabolic alkalosis"
            expected = 40 + 0.7 * (self.hco3 - 24)
            formula = "40 + 0.7 x (HCO3 - 24)"

        self.compensation = {
            "param": "pCO2", "expected": expected, "actual": self.pco2,
            "low": expected - COMP_TOL, "high": expected + COMP_TOL, "formula": formula,
        }
        if self.pco2 > expected + COMP_TOL:
            self.compensation["verdict"] = "pCO2 higher than expected"
            self.concurrent.append("Respiratory acidosis")
        elif self.pco2 < expected - COMP_TOL:
            self.compensation["verdict"] = "pCO2 lower than expected"
            self.concurrent.append("Respiratory alkalosis")
        else:
            self.compensation["verdict"] = "Appropriate"

    # ──────────────────────────────────────────
    # DISPLAY
    # ──────────────────────────────────────────
    def display(self):
        W = 60
        print("\n" + "═" * W)
        print("  ABG ANALYSIS RESULT")
        print("═" * W)
        print(f"  pH {self.ph}  ->  {self.ph_status}")
        print(f"\n  {self.headline}")

        if self.compensation:
            c = self.compensation
            print("\n  ── Compensation ──────────────────────────────")
            print(f"  Expected {c['param']:5s}    : {c['expected']:.1f} ({c['low']:.1f}-{c['high']:.1f})")
            print(f"  Measured {c['param']:5s}    : {c['actual']}")
            print(f"  Formula            : {c['formula']} ± {COMP_TOL}")
            print(f"  Verdict            : {c['verdict']}")

        if self.ag_raw is not None:
            print("\n  ── Anion Gap ─────────────────────────────────")
            print(f"  AG                 : {self.ag_raw:.1f} mEq/L")
            if self.albumin is not None:
                print(f"  AG (albumin-corr.) : {self.ag_corrected:.1f} mEq/L")
            print(f"  Status             : {'Raised (>12)' if self.ag_elevated else 'Normal (≤12)'}")
            if self.delta_ratio is not None:
                print(f"  Delta ratio        : {self.delta_ratio}")
            if self.delta_interp:
                print(f"  Interpretation     : {self.delta_interp}")

        if self.pf_ratio is not None:
            print("\n  ── Oxygenation ───────────────────────────────")
            print(f"  Hypoxemia          : {self.hypoxemia}")
            print(f"  P/F ratio          : {self.pf_ratio} ({self.pf_grade})")
            aa = f"{self.aa_gradient} mmHg"
            if self.aa_expected is not None:
                aa += (f" ({'raised' if self.aa_gradient > self.aa_expected else 'normal'}; "
                       f"expected ≤ {self.aa_expected})")
            else:
                aa += " (age not given; not assessed)"
            print(f"  A-a gradient       : {aa}")
            if self.pf_ratio <= 300:
                print("  Note: ARDS also needs acute onset, bilateral opacities, PEEP ≥ 5.")

        for n in self.notes:
            print(f"\n  ⚠  {n}")
        print("═" * W)

    # ──────────────────────────────────────────
    # DIFFERENTIALS
    # ──────────────────────────────────────────
    def walkthrough_causes(self):
        disorders = [self.primary_disorder] + self.concurrent if self.primary_disorder else self.concurrent
        causes = []
        for d in disorders:
            for key, items in CAUSES.items():
                if key.lower() in d.lower():
                    causes.extend(i for i in items if i not in causes)
        if not causes:
            return
        if get_choice("\n  Walk through possible causes? (y/n): ", ("y", "n")) != "y":
            return

        causes.sort()
        selected = []
        print(f"\n  {len(causes)} possible causes to evaluate:\n")
        for i, cause in enumerate(causes, 1):
            if get_choice(f"  {i:2d}) {cause}: probable? (y/n): ", ("y", "n")) == "y":
                selected.append(cause)

        print("\n  ── Probable Causes Selected ──")
        if selected:
            for i, c in enumerate(selected, 1):
                print(f"    {i}. {c}")
        else:
            print("    None selected.")


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def main():
    print("\n" + "═" * 60)
    print("  ABG Analysis Tool  |  Dr. Shoubhik Banerjee  |  v2.0")
    print("  Decision support only: interpret with the clinical picture.")
    print("═" * 60)

    while True:
        abg = ABGAnalysis()
        abg.collect_inputs()
        abg.analyse()
        abg.display()
        abg.walkthrough_causes()
        if get_choice("\n  Analyse another ABG? (y/n): ", ("y", "n")) != "y":
            break

    print("\n  Thank you!")


if __name__ == "__main__":
    main()
