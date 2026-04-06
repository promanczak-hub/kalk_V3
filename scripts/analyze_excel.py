import pandas as pd

file_path = r'C:\Users\proma\Downloads\2503_wynik_JŁ.xlsx'
xl = pd.ExcelFile(file_path)
print("Sheet names:", xl.sheet_names)

df = xl.parse(xl.sheet_names[0])
print("Shape:", df.shape)

# Find Octavia RS
matches = df[df.apply(lambda row: row.astype(str).str.contains('Octavia', case=False).any(), axis=1)]
print(f"Found {len(matches)} rows with Octavia")

# Try to find exactly row 1683 logic
try:
    print("Row 1681:")
    print(df.iloc[1681, :10].to_dict())
    
    # BV = 73 (0 indexed), BW = 74
    print("BV1683:", df.iloc[1681, 73])
    print("BW1683:", df.iloc[1681, 74])
except Exception as e:
    print("Row 1681 not found:", e)
    
