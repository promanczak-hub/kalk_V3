# -*- coding: utf-8 -*-
"""Read V1 Excel row 1679 (Octavia RS) to extract exact WR formula."""

import openpyxl

path = r"C:\Users\proma\Downloads\DRAFT_KALKULATORA_WARTOŚCI_REZYDUALNYCH_ver_aktualna_JŁ_02_02_2026 (2).xlsx"
wb = openpyxl.load_workbook(path, data_only=True)
ws = wb["KALKULATOR DH (dubel)"]

# Row 1679 = Octavia RS
row = 1679

# Print ALL columns with values for this row
print(f"Row {row} - all cells with values:")
for col in range(1, ws.max_column + 1):
    v = ws.cell(row=row, column=col).value
    if v is not None:
        col_letter = openpyxl.utils.get_column_letter(col)
        print(f"  {col_letter}({col}): {v}")

# Also print row 1 (headers) for context
print(f"\nRow 1 - headers (columns with data in row {row}):")
for col in range(1, ws.max_column + 1):
    v = ws.cell(row=row, column=col).value
    if v is not None:
        col_letter = openpyxl.utils.get_column_letter(col)
        header = ws.cell(row=1, column=col).value
        print(f"  {col_letter}({col}): header={header}")
