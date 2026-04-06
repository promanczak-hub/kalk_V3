from openpyxl import load_workbook
import pprint

wb = load_workbook('templates/extracted/backend/app/core/template_v6.xlsx', data_only=True)
ws = wb.active

for r in range(1, 15):
    row_data = [ws.cell(r, c).value for c in range(1, 16)]
    # if any element is not None
    if any(row_data):
        print(f"ROW {r}:")
        pprint.pprint(row_data)
