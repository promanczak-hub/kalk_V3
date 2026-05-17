import os
import re

tables = [
    "tabela_rabaty",
    "engines",
    "control_center",
    "samar_klasa_wr",
    "ltr_admin_korekta_wr_roczniks",
    "ltr_admin_korekta_wr_markas",
    "ltr_admin_tabela_wr_doposazenies",
    "tyre_costs",
    "ltr_kalkulacje",
    "paint_types",
    "paint_parsing_rules",
    "vehicle_synthesis",
    "samar_class_base_rv",
    "ltr_admin_wspolczynniki_szkodowe",
    "samar_class_options_rv",
    "samar_service_costs",
    "service_rates_config",
    "service_base_costs_config",
    "transport_fees",
    "vehicle_matrix_cache",
    "ltr_offers",
    "extraction_corrections",
    "calculation_jobs",
    "samar_mileage_adjustments",
    "samar_service_brand_multipliers",
    "samar_service_fuel_multipliers",
    "samar_service_drive_multipliers",
    "samar_service_gearbox_multipliers",
    "tab_okres_final",
    "samar_class_depreciation_rates",
    "samar_class_mileage_corrections",
    "samar_brand_corrections",
    "replacement_car_rates",
    "ltr_admin_ubezpieczenia",
    "samar_class_service_rates",
    "koszty_opon",
    "samar_classes",
    "body_types",
]

directories = ["d:/kalk_v3/backend", "d:/kalk_v3/frontend"]
extensions = (".py", ".ts", ".tsx", ".sql")

# We only compile the regexes once
table_regexes = {table: re.compile(rf"\b{table}\b") for table in tables}
used_tables = set()

for directory in directories:
    for root, dirs, files in os.walk(directory):
        # Exclude node_modules, .venv, .git, etc. from traversal
        dirs[:] = [
            d
            for d in dirs
            if d
            not in (
                ".git",
                "node_modules",
                ".venv",
                ".next",
                "dist",
                "build",
                ".pytest_cache",
                "__pycache__",
            )
        ]

        for file in files:
            if file.endswith(extensions):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()

                    for table in tables:
                        if table in used_tables:
                            continue
                        if table_regexes[table].search(content):
                            used_tables.add(table)
                except Exception:
                    pass

orphaned_tables = [t for t in tables if t not in used_tables]

print(f"--- ORPHANED TABLES ({len(orphaned_tables)}) ---")
for table in orphaned_tables:
    print(f"{table}")
