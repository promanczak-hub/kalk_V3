L1679 = 247850  # Base Gross
O1679 = 34500  # Options Gross

base_rate = 0.40  # TAB.WR KLASA for Year 4
BC1679 = L1679 * base_rate
print(f"BC1679 (Base Gross Y4): {BC1679}")

# TAB. DOPOSAZENIA col 6 is unknown but let's guess 0.20
options_rate = 0.20
options_rv = O1679 * options_rate
print(f"Options Gross Y4: {options_rv}")

BR1679_48m = BC1679 + options_rv
print(f"BR1679 (Total Gross Y4): {BR1679_48m}")

color_corr = -0.01 * L1679
print(f"Color Correction: {color_corr}")

AK1679_48m = 0
print(f"Mileage Correction: {AK1679_48m}")

BV1679_48m = BR1679_48m + color_corr - AK1679_48m
print(f"Final RV Gross: {BV1679_48m}")
print(f"Final RV Netto: {BV1679_48m / 1.23}")
