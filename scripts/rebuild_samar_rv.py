"""Rebuild script for samar_rv.py — extracts only needed parts."""

from __future__ import annotations

content = open("backend/core/samar_rv.py", "r", encoding="utf-8").read()
lines = content.splitlines(keepends=True)

IMPORTS = (
    '"""\n'
    "Kalkulator Wartości Rezydualnej (SAMAR V3).\n"
    "\n"
    "Algorytm:\n"
    "  1. WR bazy = cena_bazowa x (WR_klasa% + korekta_marka%)\n"
    "  2. Kaskadowa deprecjacja rok->rok (compound, 7 lat)\n"
    "  3. RV opcji = opcje x stawka_opcji_per_rok[delta_lat]\n"
    "  4. Korekta przebiegu\n"
    "  5. Korekty: kolor, nadwozie (z zabudowa), rocznik\n"
    "  6. Korekta reczna + wynik koncowy\n"
    "\n"
    "Kluczowe tabele: samar_class_depreciation_rates,\n"
    "                 samar_class_mileage_corrections,\n"
    "                 body_type_wr_corrections, paint_types.\n"
    "\n"
    "Moduly pomocnicze:\n"
    "  - core.samar_rv_fetchers  -- cached DB fetchers + _normalize_fuel_name\n"
    "  - core.samar_rv_readiness -- ReadinessItem + check_rv_readiness\n"
    '"""\n'
    "\n"
    "from __future__ import annotations\n"
    "import logging\n"
    "from dataclasses import dataclass, field\n"
    "from typing import Any, Dict, List, Optional\n"
    "\n"
    "from core.database import supabase\n"
    "from core.samar_rv_fetchers import (\n"
    "    KNOWN_FUEL_TYPES,\n"
    "    _normalize_fuel_name,\n"
    "    fetch_base_rv_percent_cached,\n"
    "    fetch_brand_correction_cached,\n"
    "    fetch_body_correction_cached,\n"
    "    fetch_color_correction_cached,\n"
    "    fetch_depreciation_rates_cached,\n"
    "    fetch_lo_param_cached,\n"
    "    fetch_mileage_corrections_cached,\n"
    "    fetch_vintage_correction_cached,\n"
    "    fetch_zabudowa_correction_cached,\n"
    ")\n"
    "from core.samar_rv_readiness import ReadinessItem, check_rv_readiness\n"
    "\n"
    "logger = logging.getLogger(__name__)\n"
    "\n"
    "# ===============================================================\n"
    "# Cache klasy SAMAR\n"
    "# ===============================================================\n"
    "\n"
    "_SAMAR_CACHE: Dict[str, int] = {}\n"
    "\n"
)

# get_samar_class_id function (0-indexed lines 34-77)
samar_id_fn = "".join(lines[34:78])

# RVInput + RVOutput dataclasses (0-indexed 420-454)
rv_dataclasses = "".join(lines[420:455])

# SamarRVCalculator to end (0-indexed 675+)
rv_calc = "".join(lines[675:])

new_content = IMPORTS + samar_id_fn + "\n\n" + rv_dataclasses + "\n\n" + rv_calc

open("backend/core/samar_rv.py", "w", encoding="utf-8").write(new_content)
line_count = len(new_content.splitlines())
print(f"Written {line_count} lines")

import ast

try:
    ast.parse(new_content)
    print("Syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")
    # Show context
    ctx_lines = new_content.splitlines()
    start = max(0, e.lineno - 3)
    end = min(len(ctx_lines), e.lineno + 2)
    for i, l in enumerate(ctx_lines[start:end], start=start + 1):
        print(f"  {i}: {l}")
