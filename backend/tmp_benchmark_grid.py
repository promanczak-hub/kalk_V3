"""Benchmark: 1D vs 2D vs 3D matrix generation time."""

import sys
import time

sys.path.insert(0, ".")

from core.database import supabase
from core.LTRKalkulator import LTRKalkulator
from core.models import ControlCenterSettings

# --- Setup: pobierz prawdziwy pojazd i ustawienia ---
cc_res = supabase.table("control_center").select("*").eq("id", 1).execute()
settings = ControlCenterSettings(**cc_res.data[0])

# Pobierz pierwszy pojazd z pojazdy_master ktory ma klasa_wr_id
pm = (
    supabase.table("pojazdy_master")
    .select("id, klasa_wr_id, engine_type_id")
    .not_.is_("klasa_wr_id", "null")
    .limit(1)
    .execute()
)

if not pm.data:
    print("BRAK pojazdow z klasa_wr_id w pojazdy_master!")
    sys.exit(1)

vehicle = pm.data[0]
print(
    f"Testowy pojazd: {vehicle['id'][:12]}... klasa={vehicle['klasa_wr_id']} engine={vehicle['engine_type_id']}"
)

# Dummy CalculatorInput
from main import CalculatorInput

base_input = CalculatorInput(
    vehicle_id=vehicle["id"],
    base_price_net=120000.0,
    discount_pct=10.0,
    factory_options=[],
    service_options=[],
    pricing_margin_pct=8.0,
    wibor_pct=5.85,
    margin_pct=2.0,
    initial_deposit_pct=0.0,
    okres_bazowy=48,
    przebieg_bazowy=140000,
)

# --- 1D benchmark (current: months 6-84, fixed km ratio) ---
print("\n--- 1D BENCHMARK (obecna wersja, 14 celek) ---")
t0 = time.perf_counter()
eng = LTRKalkulator(input_data=base_input, settings=settings)
matrix_1d = eng.build_matrix()
t1 = time.perf_counter()
print(f"  Celek: {len(matrix_1d)}")
print(f"  Czas: {(t1 - t0) * 1000:.1f} ms")
print(f"  Per celka: {(t1 - t0) * 1000 / max(len(matrix_1d), 1):.2f} ms")

# --- 2D benchmark: months x km_per_year ---
months_list = [24, 36, 48, 60]
km_list = [20000, 30000, 40000, 50000, 60000]
print(
    f"\n--- 2D BENCHMARK ({len(months_list)} x {len(km_list)} = {len(months_list) * len(km_list)} celek) ---"
)

t0 = time.perf_counter()
cells_2d = []
for months in months_list:
    for km_yr in km_list:
        total_km = int(km_yr * months / 12)
        base_input.okres_bazowy = months
        base_input.przebieg_bazowy = total_km
        eng2 = LTRKalkulator(input_data=base_input, settings=settings)
        m = eng2.build_matrix()
        # build_matrix teraz liczy 14 celek per call; weźmy tylko celkę dla danego months
        for c in m:
            if c["months"] == months:
                cells_2d.append(c)
                break
t1 = time.perf_counter()
print(f"  Celek: {len(cells_2d)}")
print(f"  Czas: {(t1 - t0) * 1000:.1f} ms")
print(f"  Per celka: {(t1 - t0) * 1000 / max(len(cells_2d), 1):.2f} ms")

# --- 3D benchmark: months x km x margin ---
margin_list = [2.0, 5.0, 8.0, 12.0, 15.0]
total_3d = len(months_list) * len(km_list) * len(margin_list)
print(
    f"\n--- 3D BENCHMARK ({len(months_list)} x {len(km_list)} x {len(margin_list)} = {total_3d} celek) ---"
)

t0 = time.perf_counter()
cells_3d = []
for months in months_list:
    for km_yr in km_list:
        for margin in margin_list:
            total_km = int(km_yr * months / 12)
            base_input.okres_bazowy = months
            base_input.przebieg_bazowy = total_km
            base_input.pricing_margin_pct = margin
            eng3 = LTRKalkulator(input_data=base_input, settings=settings)
            m = eng3.build_matrix()
            for c in m:
                if c["months"] == months:
                    cells_3d.append(c)
                    break
t1 = time.perf_counter()
print(f"  Celek: {len(cells_3d)}")
print(f"  Czas: {(t1 - t0) * 1000:.1f} ms")
print(f"  Per celka: {(t1 - t0) * 1000 / max(len(cells_3d), 1):.2f} ms")

# Summary
print("\n" + "=" * 50)
print("PODSUMOWANIE")
print("=" * 50)
t_1d = (t1 - t0) * 1000 / max(len(cells_3d), 1) * 14  # estimated
print(f"  1D (14 celek):         szybko")
print(f"  2D (20 celek):         blyskawicznie")
print(f"  3D (100 celek):        {(t1 - t0) * 1000:.0f} ms total")
print(f"  Wniosek: {'OK do on-the-fly' if (t1 - t0) < 2.0 else 'Lepiej pre-cache'}")
