-- Migracja: konwersja cen opon z per-sztuka na per-komplet (×4)
-- Guarded: skip if koszty_opon table does not exist yet

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'koszty_opon' AND table_schema = 'public') THEN
        UPDATE public.koszty_opon SET
          budget = budget * 4,
          medium = medium * 4,
          premium = premium * 4,
          wzmocnione_budget = wzmocnione_budget * 4,
          wzmocnione_medium = wzmocnione_medium * 4,
          wzmocnione_premium = wzmocnione_premium * 4,
          wielosezon_budget = wielosezon_budget * 4,
          wielosezon_medium = wielosezon_medium * 4,
          wielosezon_premium = wielosezon_premium * 4,
          wielosezon_wzmocnione_budget = wielosezon_wzmocnione_budget * 4,
          wielosezon_wzmocnione_medium = wielosezon_wzmocnione_medium * 4,
          wielosezon_wzmocnione_premium = wielosezon_wzmocnione_premium * 4;
    END IF;
END $$;
