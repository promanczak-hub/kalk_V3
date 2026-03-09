-- Fix broken FK constraint on ltr_admin_korekta_wr_markas
-- Old FK referenced samar_klasa_wr(id) which doesn't exist
-- Now klasa_wr_id maps to samar_classes(id)

DO $$
BEGIN
    -- Drop old FK if exists
    ALTER TABLE public.ltr_admin_korekta_wr_markas
        DROP CONSTRAINT IF EXISTS ltr_admin_korekta_wr_markas_klasa_wr_id_fkey;

    -- Add new FK to samar_classes
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_brand_corr_samar_class'
          AND table_name = 'ltr_admin_korekta_wr_markas'
    ) THEN
        ALTER TABLE public.ltr_admin_korekta_wr_markas
            ADD CONSTRAINT fk_brand_corr_samar_class
            FOREIGN KEY (klasa_wr_id) REFERENCES public.samar_classes(id) ON DELETE CASCADE;
    END IF;

    -- Add FK to engines
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_brand_corr_engine'
          AND table_name = 'ltr_admin_korekta_wr_markas'
    ) THEN
        ALTER TABLE public.ltr_admin_korekta_wr_markas
            ADD CONSTRAINT fk_brand_corr_engine
            FOREIGN KEY (rodzaj_paliwa) REFERENCES public.engines(id) ON DELETE CASCADE;
    END IF;
END $$;
