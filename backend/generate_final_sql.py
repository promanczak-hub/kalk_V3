import json
import uuid

with open("d:/kalk_v3/parsed_features.json", "r", encoding="utf-8") as f:
    features = json.load(f)

# Need the category to UUID mapping since it's not in parsed_features explicitly.
# Wait, let me read the previously generated seed_features.sql to get the exact UUIDs for categories and features.
import re

known_categories = {}
feature_category_map = {}
feature_uuid_map = {}

with open("d:/kalk_v3/seed_features.sql", "r", encoding="utf-8") as f:
    sql = f.read()

cat_pattern = re.compile(
    r"INSERT INTO reverse_search\.universal_feature_categories \(id, category_key, display_name\) VALUES \('([^']+)', '([^']+)', '([^']+)'\);"
)
for match in cat_pattern.finditer(sql):
    known_categories[match.group(2)] = {
        "id": match.group(1),
        "display_name": match.group(3),
    }

feat_pattern = re.compile(
    r"INSERT INTO reverse_search\.universal_features \(id, category_id, feature_key, display_name, feature_type, metadata\) \nVALUES \('([^']+)', '([^']+)', '([^']+)', '([^']+)', '([^']+)', (NULL|'[^']+')\);"
)
for match in feat_pattern.finditer(sql):
    feature_uuid_map[match.group(3)] = match.group(1)
    feature_category_map[match.group(3)] = match.group(2)

# Generate new SQL
out = [
    "-- Clear old data\nDELETE FROM reverse_search.universal_features;\nDELETE FROM reverse_search.universal_feature_categories;\n\n-- Insert Categories"
]
for key, cat in known_categories.items():
    out.append(
        f"INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name, vehicle_scope, sort_order) VALUES ('{cat['id']}', '{key}', '{cat['display_name']}', 'both', 10);"
    )

out.append("\n-- Insert Features")
for feat in features:
    key = feat["feature_key"]
    if key not in feature_uuid_map:
        continue

    feat_uuid = feature_uuid_map[key]
    cat_uuid = feature_category_map[key]
    metadata = {"options": feat["options"], "original_column": feat["original_column"]}

    meta_json = json.dumps(metadata, ensure_ascii=False).replace("'", "''")
    display = feat["display_name"].replace("'", "''")

    out.append(
        f"INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata, vehicle_scope, is_filterable, sort_order) VALUES ('{feat_uuid}', '{cat_uuid}', '{key}', '{display}', '{feat['feature_type']}', '{meta_json}'::jsonb, 'both', true, 10);"
    )

with open("d:/kalk_v3/seed_features_with_metadata.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print(f"Generated seed_features_with_metadata.sql with {len(features)} features")
