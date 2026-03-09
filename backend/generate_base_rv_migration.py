import json
import os
from datetime import datetime

with open("tmp_rv_mapped.json", encoding="utf-8") as f:
    data = json.load(f)

engine_mapping = {
    "BENZYNA": "Benzyna",
    "DIESEL": "Diesel",
    "EV": "Elektryczny",
    "PHEV": "Hybryda Plug-in",
    "HEV": "Hybryda (HEV)",
}

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
filename = f"../supabase/migrations/{timestamp}_create_base_rv_table.sql"

sql = """-- Create samar_class_base_rv table
CREATE TABLE IF NOT EXISTS public.samar_class_base_rv (
    id SERIAL PRIMARY KEY,
    samar_class_id INTEGER NOT NULL REFERENCES public.samar_classes(id) ON DELETE CASCADE,
    engine_type_id INTEGER NOT NULL REFERENCES public.engines(id),
    base_rv_percent NUMERIC NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(samar_class_id, engine_type_id)
);

-- RLS policies
ALTER TABLE public.samar_class_base_rv ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read access" ON public.samar_class_base_rv FOR SELECT USING (true);
CREATE POLICY "Allow authenticated insert" ON public.samar_class_base_rv FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow authenticated update" ON public.samar_class_base_rv FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Allow authenticated delete" ON public.samar_class_base_rv FOR DELETE USING (auth.role() = 'authenticated');

-- Seed data
"""

for class_name, fuels in data.items():
    for fuel_code, percentage in fuels.items():
        engine_name = engine_mapping.get(fuel_code)
        if not engine_name:
            continue

        sql += f"""
INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    {percentage}
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = '{class_name}' AND e.name = '{engine_name}'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;
"""

with open(filename, "w", encoding="utf-8") as f:
    f.write(sql)
print(f"Created {filename}")
