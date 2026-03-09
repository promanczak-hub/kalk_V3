-- Fix ltr_admin_korekta_wr_markas: add auto-increment to id column
-- The old table has BIGINT PRIMARY KEY without sequence

-- Create sequence if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'ltr_admin_korekta_wr_markas_id_seq') THEN
        CREATE SEQUENCE public.ltr_admin_korekta_wr_markas_id_seq;
    END IF;

    ALTER TABLE public.ltr_admin_korekta_wr_markas
        ALTER COLUMN id SET DEFAULT nextval('public.ltr_admin_korekta_wr_markas_id_seq');

    -- Set sequence to start after max existing id
    PERFORM setval('public.ltr_admin_korekta_wr_markas_id_seq',
        COALESCE((SELECT MAX(id) FROM public.ltr_admin_korekta_wr_markas), 0) + 1);
END $$;
