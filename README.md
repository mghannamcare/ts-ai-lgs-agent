# TS AI – LGS Quantity & Cost Estimator | FINAL PROJECT v1.0

Focused workflow:
**Drawings + Specifications + BOQ → LGS Detailed Quantity Takeoff → Labor Hours → Indicative Saudi Cost**

This final version is intentionally focused on LGS / prefab office estimating.

## Run
1. Install Python 3.11+.
2. `pip install -r requirements.txt`
3. Optional for AI drawing/specification intelligence: set `OPENAI_API_KEY`.
4. Run: `streamlit run app.py`

## Demo
Use the sidebar button:
**Load Demo Project - SRA Contractor Office**

This loads the supplied contractor office benchmark:
- 27.7 × 13.2 m
- 365.64 m²
- detailed LGS/prefab quantity and cost rows
- explicit assumptions and clarifications

## Outputs
- Detailed LGS materials and quantities
- Waste-adjusted quantities
- Labor hours and labor cost
- Indicative unit costs
- Material/direct/estimated cost
- MEP provisional allowance
- Assumptions and clarifications
- Excel cost estimate

## Important
Indicative Saudi-market baseline rates are estimating assumptions, not supplier quotations. Confirm procurement quotations, engineered LGS design and MEP takeoff before commercial submission.
