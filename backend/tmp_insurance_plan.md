---

# Implementation Plan: LTR Insurance Calculator (Ubezpieczenie)

This plan outlines the architecture for migrating the legacy `LTRSubCalculatorUbezpieczenie` to the V3 environment. The calculator calculates the annual and monthly insurance premiums based on the financed capital.

## Logic Rules (from V1)

1.  **Base Premium (`Podstawa`)**:
    - The base value for year 1 is the total financed capital (`Cena Zakupu` after discounts + factory options).
    - For subsequent years, the base depreciates using an amortization factor: `Podstawa = Podstawa * (1 - (miesiac * AmortyzacjaUbezpieczenia))`.
2.  **Modifiers**:
    - `NaukaJazdy` (Driving School): If true, multiplies the base AC premium by a specific global parameter.
    - `DoubezpieczenieKradziezy` (Theft Insurance): Adds an additional multiplier/fixed rate.
3.  **Participation**:
    - `ExpressPlaciUbezpieczenie`: If false, the insurance is calculated but the final cost added to the PMT is 0 (the client brings their own insurance).
4.  **Rates**:
    - Basic AC/OC/NW rates are fetched globally or based on vehicle parameters.

## Proposed Changes

### Backend Logic Update

#### [NEW] `d:\kalk_v3\backend\core\insurance.py`

_(Note: File exists, but needs to be adapted or verified against V1 rules)_

- Ensure `InsuranceCalculator` class exists.
- Accept inputs: `base_price` (capital), `months`, `is_driving_school`, `express_pays_insurance`, `ac_rate`, `oc_rate`, `nw_rate`.
- Logic Flow:
  1. Loop through years (`months / 12`).
  2. Year 1 Base = `base_price`. Calculate AC, OC, NW.
  3. Year 2+ Base = `base_price * (1 - (months * depreciation_rate))`.
  4. Apply `is_driving_school` multiplier to AC if true.
  5. Sum total. If `express_pays_insurance` is False, return 0 for financial logic, but maintain the raw number for the breakdown UI.

#### [MODIFY] `d:\kalk_v3\backend\core\engine_v3.py`

- Wire the UI flags (`NaukaJazdy`, `UbezpieczenieWExpress`) into `CalculatorInputV3`.
- Pass these to the `InsuranceCalculator`.

## Verification Plan

### Automated Tests

- Create/Update `tests/test_insurance.py`.
- Verify `ExpressPlaciUbezpieczenie=False` yields `0.0` monthly cost.
- Verify `NaukaJazdy=True` spikes the AC premium line correctly.
- Verify multi-year depreciation (e.g., Year 2 premium < Year 1 premium).
