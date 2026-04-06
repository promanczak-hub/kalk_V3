import re
import os

files_to_update = [
    "d:/kalk_v3/seed_features.sql",
    "d:/kalk_v3/seed_features_with_metadata.sql",
    "d:/kalk_v3/online_features_import.sql"
]

# We need to extract the category IDs for the target categories from the SQL file if possible,
# or from the database. Since they are UUIDs, let's find the UUIDs for target categories.
cat_ids = {
    'przestrzeń_ładunkowa': 'c6c23615-2428-4118-a4cd-aa20abddda84',
    'towing': 'cf35a46c-2bf1-400f-8971-2752d1236f18', # From DB output: [35] Holowanie / Hak (ID: cf35a46c-2bf1-400f-8971-2752d1236f18)
    'seats': '1f9892a9-51cc-4ed2-921e-36f30f2c9145'   # From DB output: [85] Fotele (ID: 1f9892a9-51cc-4ed2-921e-36f30f2c9145)
}

feature_moves = {
    'm2': 'c6c23615-2428-4118-a4cd-aa20abddda84',
    'd_uciag': 'cf35a46c-2bf1-400f-8971-2752d1236f18',
    's_nacisk_na_hak': 'cf35a46c-2bf1-400f-8971-2752d1236f18',
    'fotele_przednie_z_funkcją_masażu': '1f9892a9-51cc-4ed2-921e-36f30f2c9145',
    'fotele_tylne_z_funkcją_masażu': '1f9892a9-51cc-4ed2-921e-36f30f2c9145'
}

for filepath in files_to_update:
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    
    for line in lines:
        for feat, target_cat_id in feature_moves.items():
            if f"'{feat}'" in line:
                # The line format usually is:
                # INSERT INTO reverse_search.universal_features (id, category_id, feature_key, ...) VALUES ('...', 'OLD_CAT_ID', 'feature_key', ...)
                # Or SELECT '...', id, 'feature_key' (where id is category ID variable?)
                # We can just use a regex to replace the second UUID in VALUES ('UUID1', 'UUID2', 'feature_key'
                if "VALUES" in line:
                    match = re.search(r"VALUES \('([^']+)',\s*'([^']+)',\s*'([^']+)'", line)
                    if match and match.group(3) == feat:
                        line = line.replace(f"'{match.group(2)}'", f"'{target_cat_id}'")
        new_lines.append(line)
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

print("Seed files categories updated.")
