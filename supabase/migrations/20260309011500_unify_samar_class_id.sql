-- Migration: Unify SAMAR class references
-- Rename klasa_wr_id → samar_class_id in legacy tables
-- Rename "KlasaId" → samar_class_id in insurance table
-- Drop unused bridge column samar_classes.klasa_wr_id

BEGIN;

-- ═══════════════════════════════════════════════════════════════
-- 1. ltr_admin_korekta_wr_markas: klasa_wr_id → samar_class_id
-- ═══════════════════════════════════════════════════════════════

-- Drop existing constraints that reference old column name
ALTER TABLE public.ltr_admin_korekta_wr_markas
    DROP CONSTRAINT IF EXISTS ltr_admin_korekta_wr_markas_klasa_wr_id_fkey;

ALTER TABLE public.ltr_admin_korekta_wr_markas
    DROP CONSTRAINT IF EXISTS ltr_admin_korekta_wr_markas_klasa_wr_id_rodzaj_paliwa_brand_key;

-- Rename column
ALTER TABLE public.ltr_admin_korekta_wr_markas
    RENAME COLUMN klasa_wr_id TO samar_class_id;

-- Cleanup orphans before applying FK mapping
DELETE FROM public.ltr_admin_korekta_wr_markas 
WHERE samar_class_id NOT IN (SELECT id FROM public.samar_classes);

-- Re-add FK and unique constraint with new name
ALTER TABLE public.ltr_admin_korekta_wr_markas
    ADD CONSTRAINT ltr_admin_korekta_wr_markas_samar_class_fk
    FOREIGN KEY (samar_class_id) REFERENCES public.samar_classes(id) ON DELETE CASCADE;

ALTER TABLE public.ltr_admin_korekta_wr_markas
    ADD CONSTRAINT ltr_admin_korekta_wr_markas_unique_class_fuel_brand
    UNIQUE (samar_class_id, rodzaj_paliwa, brand_name);


-- ═══════════════════════════════════════════════════════════════
-- 2. ltr_admin_wspolczynniki_szkodowe: klasa_wr_id → samar_class_id
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE public.ltr_admin_wspolczynniki_szkodowe
    RENAME COLUMN klasa_wr_id TO samar_class_id;

-- Cleanup orphans before applying FK mapping
DELETE FROM public.ltr_admin_wspolczynniki_szkodowe 
WHERE samar_class_id NOT IN (SELECT id FROM public.samar_classes);

-- Add FK (was missing)
ALTER TABLE public.ltr_admin_wspolczynniki_szkodowe
    ADD CONSTRAINT ltr_admin_wspolczynniki_szkodowe_samar_class_fk
    FOREIGN KEY (samar_class_id) REFERENCES public.samar_classes(id) ON DELETE CASCADE;


-- ═══════════════════════════════════════════════════════════════
-- 3. ltr_admin_ubezpieczenia: "KlasaId" → samar_class_id
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE public.ltr_admin_ubezpieczenia
    RENAME COLUMN "KlasaId" TO samar_class_id;

-- Cleanup orphans before applying FK mapping
DELETE FROM public.ltr_admin_ubezpieczenia 
WHERE samar_class_id IS NOT NULL 
  AND samar_class_id NOT IN (SELECT id FROM public.samar_classes);

-- KlasaId allows NULL (for default/fallback rates), keep nullable
-- Add FK only for non-null values
ALTER TABLE public.ltr_admin_ubezpieczenia
    ADD CONSTRAINT ltr_admin_ubezpieczenia_samar_class_fk
    FOREIGN KEY (samar_class_id) REFERENCES public.samar_classes(id) ON DELETE CASCADE;


-- ═══════════════════════════════════════════════════════════════
-- 4. samar_classes: DROP klasa_wr_id (all NULL, unused bridge)
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE public.samar_classes
    DROP COLUMN IF EXISTS klasa_wr_id;

COMMIT;
