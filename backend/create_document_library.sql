-- Skrypt do utworzenia tabeli `document_library` (Biblioteka Cenników)

CREATE TABLE IF NOT EXISTS public.document_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name VARCHAR(255) NOT NULL,
    document_url TEXT NOT NULL,
    document_type VARCHAR(50) NOT NULL, /* np. PRICE_LIST, BROCHURE, OTHER */
    brand VARCHAR(100),
    model VARCHAR(100),
    valid_from DATE,
    description TEXT,
    digital_twin JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Włączenie RLS
ALTER TABLE public.document_library ENABLE ROW LEVEL SECURITY;

-- Polityki dostępu (pozwalają każdemu na odczyt i zapis dla uproszczenia frontendu, lub mozna uzyc authenticated)
CREATE POLICY "Enable read access for all users" ON public.document_library FOR SELECT USING (true);
CREATE POLICY "Enable insert access for all users" ON public.document_library FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON public.document_library FOR UPDATE USING (true);
CREATE POLICY "Enable delete access for all users" ON public.document_library FOR DELETE USING (true);
