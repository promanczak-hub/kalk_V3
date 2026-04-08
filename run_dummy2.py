dummy_matrix = []  # simulate what grid_params becomes
grid_params = []
seen_pairs = set()


def add_grid_pair(months_val, km_per_year_val, contract_km_val):
    km_per_year_val = (km_per_year_val // 1000) * 1000
    pair = (months_val, km_per_year_val)
    if pair in seen_pairs:
        return
    seen_pairs.add(pair)
    grid_params.append(pair)


req_months = 36
req_total_km = 60000

base_months = [24, 36, 48, 60]
base_km = [10000, 15000, 20000, 25000, 30000, 40000, 50000]

for m in base_months:
    for km in base_km:
        add_grid_pair(m, km, m * (km / 12))

margin_months = [-6, -3, 3, 6, 12, 18, 24]
for dm in margin_months:
    m = req_months + dm
    if m >= 12 and m <= 72:
        add_grid_pair(m, int(round((req_total_km / m) * 12)), req_total_km)

margin_km = [0.5, 0.75, 1.25, 1.5, 2.0]
for dkm in margin_km:
    new_total_km = req_total_km * dkm
    add_grid_pair(
        req_months, int(round((new_total_km / req_months) * 12)), new_total_km
    )

print(f"Total grid_params: {len(grid_params)}")
