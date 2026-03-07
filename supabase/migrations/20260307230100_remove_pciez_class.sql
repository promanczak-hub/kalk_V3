-- Migration: Remove extra SAMAR class 'Pciez' (id=30)
-- This class does not exist in the Excel SAMAR reference sheet (JŁ 02.02)
-- and should not appear in the Control Center.

-- 1. Delete FK references first
DELETE FROM public.replacement_car_rates WHERE samar_class_id = 30;

-- 2. Delete the class itself
DELETE FROM public.samar_classes WHERE id = 30;
