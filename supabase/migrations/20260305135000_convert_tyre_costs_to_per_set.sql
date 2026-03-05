-- Migracja: konwersja cen opon z per-sztuka na per-komplet (×4)
-- Powód: V1 LTRSubCalculatorOpony.cs L134 traktuje pozycja.Netto jako cenę za komplet.
--         V3 LTRSubCalculatorOpony.py usunięto ×4 z kodu — cena w bazie musi być za komplet.
-- Audyt: calc_01_opony.md, 2026-03-05

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
