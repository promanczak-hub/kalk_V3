import sys
sys.path.append(r"d:\kalk_v3\backend")

# Manual simulation
base_netto = 247850.0  # From PDF
options_netto = 34500.0 # From PDF (or 34700)
months = 48
total_km = 140000

rates_base = {0: 0.40, 1: 0.05, 2: 0.10, 3: 0.10, 4: 0.39, 5: 0.00, 6: 0.07, 7: 0.07}
rates_opts = {0: 0.46, 1: 0.40, 2: 0.32, 3: 0.26, 4: 0.21, 5: 0.16, 6: 0.12, 7: 0.09}

# Krok 1: Base WR
brand_corr = 0.0
effective_pct = rates_base[0] + brand_corr
wr_value_netto = base_netto * effective_pct
print(f"Krok 1: WR Base = {wr_value_netto}")

# Krok 2: Cascade
value_table = {4: wr_value_netto}
v = wr_value_netto
for yr in [3, 2, 1, 0]:
    rate = rates_base[0] if yr == 0 else rates_base[4 - yr]
    v = v * (1.0 + rate)
    value_table[yr] = v

v = wr_value_netto
for yr in [5, 6, 7]:
    rate = rates_base[yr]
    v = v * (1.0 - rate)
    value_table[yr] = v

print("Krok 2 Cascade table:", {k: round(v, 2) for k,v in sorted(value_table.items())})

years = int((months * 30.5) / 365)
print("Years mapped:", years)
rv_base = value_table.get(years, wr_value_netto)
rv_opts = options_netto * rates_opts[years]
rv_total = rv_base + rv_opts

print("Krok 3: RV Base =", rv_base)
print("Krok 3: RV Opts =", rv_opts)
print("Krok 3: RV Total =", rv_total)

# Krok 4: przebieg
under_rate = 0.0142
over_rate = 0.0284

przebieg_ponizej = min(total_km, 190000) - 140000
paczki_under = przebieg_ponizej / 10000.0
przebieg_powyzej = max(total_km - 190000, 0)
paczki_over = przebieg_powyzej / 10000.0

korekta_przebieg = (under_rate * rv_total * paczki_under) + (over_rate * rv_total * paczki_over)
print("Krok 4: przebieg corr =", korekta_przebieg)

# Krok 5: kolor, nadwozie
# We need color correction for SKODA Superb Diesel. 
# Usually niemetalik = 0, metalik = 0 (maybe)
color_corr = 0.0 
body_corr = 0.0

rv_pre_manual = rv_total + color_corr + body_corr - korekta_przebieg
print("Krok 5: rv_pre_manual =", rv_pre_manual)

vintage_pct = 0.0
# Rocznik correction is maybe 0 if "bieżący"
rv_final = rv_pre_manual + vintage_pct * (base_netto + options_netto)

print("Final RV =", rv_final)

