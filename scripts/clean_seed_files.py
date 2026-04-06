import re
import os

files_to_clean = [
    "d:/kalk_v3/seed_features.sql",
    "d:/kalk_v3/seed_features_with_metadata.sql",
    "d:/kalk_v3/online_features_import.sql"
]

features_to_delete = [
    'il_europalet',
    'ilość_europalet1',
    'ilość_europalet2',
    'wysokość_progu_załadunku_w_mm',
    'wysokość_tylnych_drzwi_załadunku_w_mm',
    'szerokość_tylnych_drzwi_załadunku_w_mm',
    'wysokość_drzwi_bocznego_załadunku_w_mm',
    'szerokość_drzwi_bocznego_załadunku_w_mm',
    'wysokość_burt_załadunku_w_mm',
    'długość_platformy_windy',
    'szerokość_platformy_windy',
    'zbiornik_na_wodę_1_pojemność_w_litrach',
    'zbiornik_na_wodę_2_pojemność_zbiorniaka_w_litrach',
    'skrzynia_narzędziowa_1_w_litrach',
    'skrzynia_narzędziowa_2_w_litrach'
]

for filepath in files_to_clean:
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    
    for line in lines:
        should_delete = False
        for feat in features_to_delete:
            # Check if feature key is in the line. We must be careful not to delete partial matches,
            # but these are quite specific.
            if f"'{feat}'" in line:
                should_delete = True
                break
        
        if not should_delete:
            new_lines.append(line)
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

print("Seed files cleaned up.")
