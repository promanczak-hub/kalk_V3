import pandas as pd


def sf(v):
    if pd.isna(v) or not str(v).strip():
        return 0.0
    s_val = str(v).replace("%", "").replace(",", ".").strip()
    try:
        val = float(s_val)
        if abs(val) > 0.5:
            val = val / 100.0
        return val
    except:
        return 0.0


url = "https://docs.google.com/spreadsheets/d/1GzJk87wYrOT0RyrkYdMFGoG6rKhYop9497MvhdRTp-Q/export?format=csv&gid=2032958193&range=A1:D34"
df = pd.read_csv(url)
v1 = [sf(x) for x in df.iloc[:, 1]]
v2 = [sf(x) for x in df.iloc[:, 2]]
print("Max abs v1:", max((abs(x) for x in v1), default=0))
print("Max abs v2:", max((abs(x) for x in v2), default=0))
large_vals = [x for x in v1 + v2 if abs(x) >= 1.0]
print("Any >= 1.0?", large_vals)
