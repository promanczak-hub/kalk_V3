import json
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

CLASS_NAME_TRANSLATION = {
    # Klasy Podstawowe
    "Podstawowa - A MINI": "Podstawowa - A MINI",
    "Podstawowa - B MAŁE": "Podstawowa - B MAŁE",
    "Podstawowa - C NIŻSZA ŚREDNIA": "Podstawowa - C NIŻSZA ŚREDNIA",
    "Podstawowa - D ŚREDNIA": "Podstawowa - D ŚREDNIA",
    "Podstawowa - E WYŻSZA": "Podstawowa - E WYŻSZA",
    "Podstawowa - F LUKSUSOWE": "Podstawowa - F LUKSUSOWE",
    # Premium
    "Premium - B MAŁE": "Podstawowa - B MAŁE",  # uproszczenie do bazy
    "Premium - C NIŻSZA ŚREDNIA": "Podstawowa - C NIŻSZA ŚREDNIA",
    "Premium - D ŚREDNIA": "Podstawowa - D ŚREDNIA",
    "Premium - E WYŻSZA": "Podstawowa - E WYŻSZA",
    "Premium - F LUKSUSOWE": "Podstawowa - F LUKSUSOWE",
    "Premium - G SUPER LUKSUSOWE": "Podstawowa - G SUPER LUKSUSOWE",
    # Terenowe / SUV
    "Terenowa - B MAŁE SUV I CROSSOVER": "Terenowo-rekreacyjne (SUV) - B MAŁE",
    "Terenowa - C NIŻSZA ŚREDNIA SUV I CROSSOVER": "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA",
    "Terenowa - D ŚREDNIA SUV I CROSSOVER": "Terenowo-rekreacyjne (SUV) - D ŚREDNIA",
    "Terenowa - E WYŻSZA SUV I CROSSOVER": "Terenowo-rekreacyjne (SUV) - E WYŻSZA",
    "Terenowa - F LUKSUSOWE SUV I CROSSOVER": "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE",
    "Terenowa - G SUPER LUKSUSOWE SUV I CROSS": "Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE",
    "Premium Terenowa - B MAŁE SUV CROSSOVER": "Terenowo-rekreacyjne (SUV) - B MAŁE",
    "Premium Terenowa - C NIŻSZA ŚREDNIA SUV CROSSOVER": "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA",
    "Premium Terenowa - D ŚREDNIA SUV CROSSOVER": "Terenowo-rekreacyjne (SUV) - D ŚREDNIA",
    "Premium Terenowa - E WYŻSZA SUV CROSSOVER": "Terenowo-rekreacyjne (SUV) - E WYŻSZA",
    "Premium Terenowa - F LUKSUSOWE SUV CROSSOVER": "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE",
    "Premium Terenowa - G SUPER LUKSUSOWE SUV CROSS": "Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE",
    # VANY
    "Podstawowa - M WIELKOPRZESTRZENNE VAN": "Vany - D VANY",  # zbliżona
    "Premium - M WIELKOPRZESTRZENNE VAN": "Vany - D VANY",
    # Dostawcze / Pick-up
    "Terenowa - PICK-UP I INNE": "Pick-up - PICK-UP",
    "Dostawcza - 2 DOSTAWCZE DO 3,0t": "Lekkie dostawcze - VAN",
    "Dostawcza - 3 DOSTAWCZE POW. 3,0t do 3,5t": "Średnie dostawcze - ŚREDNIE DOSTAWCZE",
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

for raw_class_name, fuels in data.items():
    # Attempt to translate bad json keys (with potentially broken encodings like MA?E)
    # So we do a soft match since "MA?E" is a result of broken encoding in node script
    class_name = None
    for k, v in CLASS_NAME_TRANSLATION.items():
        # proste szukanie np. 'A MINI'
        if k.split(" - ")[-1] in raw_class_name.replace("?", "Ł"):
            class_name = v
            break
        # lub bezposrednio dopasowac
        if k == raw_class_name.replace("?", "Ł"):
            class_name = v
            break

    # jesli nie zmapowano i nie ma w the best picks
    if not class_name:
        # custom hardcode dla tych krzakow
        if "PICK-UP" in raw_class_name:
            class_name = "Pick-up - PICK-UP"
        elif "DOSTAWCZE DO 3,0t" in raw_class_name:
            class_name = "Lekkie dostawcze - VAN"
        elif "DOSTAWCZE POW. 3,0t" in raw_class_name:
            class_name = "Średnie dostawcze - ŚREDNIE DOSTAWCZE"
        elif "F LUKSUSOWE" in raw_class_name and "Terenowa" in raw_class_name:
            class_name = "Terenowo-rekreacyjne (SUV) - F LUKSUSOWE"
        elif "E WY" in raw_class_name and "Terenowa" in raw_class_name:
            class_name = "Terenowo-rekreacyjne (SUV) - E WYŻSZA"
        elif "D " in raw_class_name and "Terenowa" in raw_class_name:
            class_name = "Terenowo-rekreacyjne (SUV) - D ŚREDNIA"
        elif "C NI" in raw_class_name and "Terenowa" in raw_class_name:
            class_name = "Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA"
        elif "B MA" in raw_class_name and "Terenowa" in raw_class_name:
            class_name = "Terenowo-rekreacyjne (SUV) - B MAŁE"
        elif "M WIELKOPRZESTRZENNE" in raw_class_name:
            class_name = "Vany - D VANY"
        elif "G SUPER" in raw_class_name:
            class_name = "Podstawowa - G SUPER LUKSUSOWE"
        elif "F LUKSUSOWE" in raw_class_name:
            class_name = "Podstawowa - F LUKSUSOWE"
        elif "E WY" in raw_class_name:
            class_name = "Podstawowa - E WYŻSZA"
        elif "D " in raw_class_name and "REDNIA" in raw_class_name:
            class_name = "Podstawowa - D ŚREDNIA"
        elif "C NI" in raw_class_name and "REDNIA" in raw_class_name:
            class_name = "Podstawowa - C NIŻSZA ŚREDNIA"
        elif "B MA" in raw_class_name:
            class_name = "Podstawowa - B MAŁE"

    if not class_name:
        class_name = (
            raw_class_name  # fallback, probably will fail SQL but we can see it
        )

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
