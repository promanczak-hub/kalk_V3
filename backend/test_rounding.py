# Własny test żeby upewnić się o mojej tezie:
total_catalog_price = 525049.99
offer_final_price = 396412.75

calc_discount = ((total_catalog_price - offer_final_price) / total_catalog_price) * 100
print("calc_discount", calc_discount)
print("round(calc_discount)", round(calc_discount))

# Sugerowany z BD = 24.5
sugerowany_cena = total_catalog_price * (1 - 24.5 / 100)
print("sugerowany_cena", sugerowany_cena)
