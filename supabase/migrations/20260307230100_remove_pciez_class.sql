-- Migration: Remove extra SAMAR class 'Pciez' (id=30)
-- Guarded: skip if tables do not exist yet

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'samar_classes' AND table_schema = 'public') THEN
        DELETE FROM public.replacement_car_rates WHERE samar_class_id = 30;
        DELETE FROM public.samar_classes WHERE id = 30;
    END IF;
END $$;
