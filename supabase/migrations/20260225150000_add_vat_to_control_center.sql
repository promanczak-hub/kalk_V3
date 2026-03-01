-- Migration: Add VAT rate to Control Center

ALTER TABLE public.control_center ADD COLUMN IF NOT EXISTS vat_rate numeric(5,2) NOT NULL DEFAULT 23.00;
