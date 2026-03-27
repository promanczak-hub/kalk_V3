rows = [
    # BQ, BR, BS, BT, BU, BV, BY
    (0.17, 237071, 239725, 0.43, 0.08, 249114, 0.3574),
    (0.25, 72659, 72634, 0.46, 0.06, 70116, 0.4438),
    (0.26, 118024, 99140, 0.40, 0.00, 113870, 0.4033),
    (0.24, 80691, 70707, 0.39, 0.00, 81186, 0.3642),
    (0.22, 110313, 93408, 0.42, 0.00, 105865, 0.3538)
]

for bq, br, bs, bt, bu, bv, by in rows:
    print(f"Row: BR={br}, BS={bs}, BT={bt}, BU={bu}, BV={bv}, BY={by}")
    
    # Check if BV is BS / (BT+BU)? No
    print(f"  BS * (BT+BU) / (1-BQ): {bs * (bt+bu) / (1-bq):.2f}")
    print(f"  BR * (BT+BU) / (1-BQ): {br * (bt+bu) / (1-bq):.2f}")
    
    # What if BV is derived from (1 + BU) ?
    print(f"  BS * (1 + BU): {bs * (1+bu):.2f} == BV? {bv}")
    
    # What if BV = BR * X where X is some rate?
    print(f"  BV / BR = {bv/br:.4f}")
    print(f"  BV / BS = {bv/bs:.4f}")
    
    # Is BV / BS * 100 related to BT + BU?
    # Row 1: BV/BS = 249114 / 239725 = 1.039. Wait.
    # Row 2: BV/BS = 70116 / 72634 = 0.965. 
    # Row 3: BV/BS = 113870 / 99140 = 1.148.
    
    # What if Wartość RV [Brutto] is NOT the RV amount, but the Base Price + something?
    # NO, RV is usually smaller than price. A car doesn't gain value. 
    # Wait, RV value Brutto 249114? BR is 237071. It gained value! WHY?
    # Let me check if RV is actually the car value AFTER X months, or if it is the LOSS of value (Utrata Wartości).
    # If it's LOSS of value, 249114 > 237071! That's more than 100% loss?
    
    # What if the columns are:
    # BS = "48 M-CY 140 tys. km [Brutto]" (A residual value amount for the base car?)
    # BV = "Wartość RV [Brutto]" (Total residual value including options?)
    # Let's check: BS + BR * BQ ? 
    print(f"  BS + BR * BQ = {bs + br * bq:.2f} == BV? {bv}")
    
    # Let's try: BS * (1 + BQ) ? 
    print(f"  BS * (1 + BQ) = {bs * (1 + bq):.2f} == BV? {bv}")
    
    # What if BY = (BR - BX) / BR ?
    # BY is "WR (Kalkul.)" = RV (po korektach)
    print(f"  (BR - BV) / BR = {(br - bv) / br:.4f} == BY? {by}")
    
