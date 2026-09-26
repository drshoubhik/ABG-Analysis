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
- **Na, Cl and albumin** (optional; asked for later if a metabolic acidosis needs classifying)
- **Age** (optional; used for the A–a gradient)

It works through the analysis step by step:

1. **pH:** acidemia, alkalemia or normal.
2. **Primary disorder:** worked out from the pH. You're only asked when both processes could explain it.
3. **Compensation:** the expected value is compared with the measured one, to show either appropriate compensation or a concurrent disorder.
   - Respiratory: acute/chronic HCO₃ rules (1, 3.5, 2 and 5 per 10 mmHg)
   - Metabolic acidosis: Winter's formula
   - Metabolic alkalosis: 40 + 0.7 × (HCO₃ − 24)
4. **Anion gap:** albumin-corrected, with the delta ratio.
5. **Oxygenation:** hypoxemia grade, P/F ratio and A–a gradient.
6. **Causes:** an optional walk-through of possible causes.

## Files

| File | What it is |
|---|---|
| `abg_analysis.py` | **Current version (v2.0).** Rewritten with classes, with clinical fixes (see below) |
| `ABG Analysis.py` | Original v1 script (2024), kept for reference |
| `ABG Analysis.exe` / `.zip` | Windows build of the v1 script |

## Changes in v2.0

- **Metabolic alkalosis compensation:** now uses 40 + 0.7 × (HCO₃ − 24). Winter's formula applies only to metabolic acidosis.
- **Normal ranges:** now pH 7.35–7.45, pCO₂ 35–45 and HCO₃ 22–26. Previously any HCO₃ other than exactly 24 counted as abnormal.
- **Primary disorder:** now worked out from the pH instead of always being asked.
- **Anion gap:** checked whenever Na/Cl are given, so a hidden AG acidosis isn't missed. It's corrected for albumin and comes with the delta ratio.
- **A–a gradient:** added, with an age-adjusted normal.
- **Hypoxemia grades:** now mild 60–79, moderate 40–59 and severe below 40. The P/F ratio is reported against Berlin ARDS thresholds.
- **Henderson–Hasselbalch check:** a mismatch now gives a warning instead of forcing you to re-enter the values.

*Decision support only. Always interpret the results alongside the clinical picture.*
