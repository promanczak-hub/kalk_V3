import sys, os
from dotenv import load_dotenv
load_dotenv(r'd:\kalk_v3\backend\.env')
sys.path.insert(0, r'd:\kalk_v3\backend')
from core.database import supabase

print('Fetching classes and engines from', os.getenv('SUPABASE_URL'))
classes = supabase.table('samar_classes').select('id, name').execute().data
engines = supabase.table('engines').select('id, name, category').execute().data

# We don't check depreciation_rates row per engine because the columns are per engine.
dep = supabase.table('samar_class_depreciation_rates').select('klasa_samar').execute().data
dep_class_set = set(d['klasa_samar'] for d in dep)

opt = supabase.table('samar_class_options_rv').select('samar_class_id, engine_type_id').execute().data
opt_set = set((o['samar_class_id'], o['engine_type_id']) for o in opt)

ub = supabase.table('ltr_admin_ubezpieczenia').select('klasa_samar_fk').execute().data
ub_set = set(u['klasa_samar_fk'] for u in ub)

errors = []

for c in classes:
    class_id = c['id']
    if class_id not in ub_set:
        errors.append(f'[Ubezp] Brak stawek ubezpieczenia dla klasy: {c["name"]} (ID {c["id"]})')
    
    if class_id not in dep_class_set:
        errors.append(f'[Deprec] Brak wiersza amortyzacji dla: {c["name"]} (ID {c["id"]})')

    for e in engines:
        engine_id = e['id']
        if (class_id, engine_id) not in opt_set:
            errors.append(f'[Opcje] Brak mnoznika opcji RV dla: {c["name"]} (ID {c["id"]}), silnik: {e["name"]} (ID {e["id"]})')

print("=== BRAKI BAZODANOWE ===")
for err in errors:
    print(err)
if not errors:
    print("Wszystko poprawne! Brak luk w mapowaniach bazy.")
