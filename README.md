# ABG Analysis

My first code share. i have seen many programs on ABG analysis but being a doctor I didn't find any which was what I wanted. This is close to what I wanted. As a beginner I know the code can be improved. Community help needed. So putting it out there.

## Running it

You need Python 3.8 or newer; no extra packages are required.

```
python abg_analysis.py
```

The program asks for:
- **pH, pCO₂ and HCO₃**
- **pO₂ and FiO₂** (optional)
- **Na, Cl and albumin** (asked for only if there is a metabolic acidosis to classify; albumin optional)
- **Age** (optional; used for the A–a gradient)

It works through the analysis step by step:

1. **pH:** acidemia, alkalemia or normal.
2. **Primary disorder:** the program is history-led. Whenever the gas can't decide by itself (a normal pH, or both pCO₂ and HCO₃ moving in the pH's direction), you're asked whether the clinical picture points to a respiratory or a metabolic primary, and the calculations start from your answer. When only one process explains the pH, the pH decides.
3. **Compensation:** the expected value is compared with the measured one, to show either appropriate compensation or a concurrent disorder.
   - Respiratory: acute/chronic HCO₃ rules (1, 3.5, 2 and 5 per 10 mmHg)
   - Metabolic acidosis: Winter's formula
   - Metabolic alkalosis: 40 + 0.7 × (HCO₃ − 24)
4. **Anion gap:** for metabolic acidosis only (HAGMA vs NAGMA), albumin-corrected. If the gap is raised, the corrected HCO₃ (HCO₃ + AG excess) flags a possible second metabolic process: above 28 suggests a concurrent metabolic alkalosis, below 20 a concurrent non-gap acidosis.
5. **Oxygenation:** hypoxemia grade, P/F ratio and A–a gradient.
6. **Causes:** an optional walk-through of possible causes.

## Files

| File | What it is |
|---|---|
| `abg_analysis.py` | **Current version (v2.0).** Rewritten with classes, with clinical fixes (see below) |
| `ABG Analysis.py` | Original v1 script (2024), kept for reference |
| `ABG Analysis.exe` / `.zip` | Windows build of the v1 script |
| `app/` | Android app (Kivy): `main.py` is the screen, `abg_core.py` the same clinical logic without terminal prompts |
| `tests/check_app_matches_cli.py` | Checks the app gives exactly the same results as `abg_analysis.py` (~7,000 ABGs) |

## Android app

Every push to `main` that touches the app or the logic builds an installable APK with GitHub Actions and publishes it to the **[apk-latest release](https://github.com/drshoubhik/ABG-Analysis/releases/tag/apk-latest)**. To install:

1. Open that link on your Android phone.
2. Tap **ABG-Analyser.apk** to download it.
3. Open the download and allow installing from this source when asked. Later builds install over the top as updates.

The build first runs `tests/check_app_matches_cli.py` and stops if the app and the command-line program disagree on any case. If you change the clinical logic, change it in both `abg_analysis.py` and `app/abg_core.py`.

To try the app on a desktop: `pip install kivy`, then `python app/main.py`.

## Changes in v2.0

- **Metabolic alkalosis compensation:** now uses 40 + 0.7 × (HCO₃ − 24). Winter's formula applies only to metabolic acidosis.
- **Thresholds:** pH normal range 7.35–7.45. pCO₂ and HCO₃ are judged against the midpoint as in v1 (pCO₂ 40 ± 2, HCO₃ 24), so even with a normal pH a low HCO₃ is treated as a metabolic acidosis and classified with the anion gap. This is what finds a high-AG acidosis masked by a metabolic alkalosis.
- **Primary disorder:** taken from the clinical history whenever the gas is ambiguous; worked out from the pH only when one process alone explains it.
- **Anion gap:** Na, Cl and albumin are asked for only when a metabolic acidosis needs classifying as HAGMA or NAGMA. The gap is corrected for albumin.
- **Delta ratio replaced by corrected HCO₃:** the ratio divides two small, noisy differences and becomes unstable when HCO₃ is near 24. Corrected HCO₃ carries the same information as a simple flag with a wide grey zone (20–28), reported as a suggestion rather than a diagnosis.
- **A–a gradient:** added, with an age-adjusted normal.
- **Hypoxemia grades:** now mild 60–79, moderate 40–59 and severe below 40. The P/F ratio is reported against Berlin ARDS thresholds.
- **Henderson–Hasselbalch check:** a mismatch (HCO₃ more than 6% off the value expected from pH and pCO₂) stops the analysis; the values must be re-entered. An inconsistent gas is never interpreted.

*Decision support only. Always interpret the results alongside the clinical picture.*
