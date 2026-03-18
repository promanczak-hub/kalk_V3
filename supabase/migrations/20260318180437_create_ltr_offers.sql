-- Migration: Create ltr_offers table and storage bucket

-- 1. Create table ltr_offers
CREATE TABLE IF NOT EXISTS public.ltr_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    client_name TEXT NOT NULL,
    client_nip TEXT,
    total_calculations INTEGER NOT NULL DEFAULT 1,
    offer_snapshot JSONB NOT NULL,
    excel_file_path TEXT
);

-- 2. RLS Policies for ltr_offers
ALTER TABLE public.ltr_offers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for all users" ON public.ltr_offers
    AS PERMISSIVE FOR SELECT
    TO public
    USING (true);

CREATE POLICY "Enable insert for all users" ON public.ltr_offers
    AS PERMISSIVE FOR INSERT
    TO public
    WITH CHECK (true);

-- 3. Create storage bucket "offers_excel"
INSERT INTO storage.buckets (id, name, public) 
VALUES ('offers_excel', 'offers_excel', true)
ON CONFLICT (id) DO NOTHING;

-- 4. RLS for storage.objects in bucket "offers_excel"
CREATE POLICY "Public Access offers_excel" ON storage.objects 
    FOR SELECT 
    USING (bucket_id = 'offers_excel');

CREATE POLICY "Public Upload offers_excel" ON storage.objects 
    FOR INSERT 
    WITH CHECK (bucket_id = 'offers_excel');
