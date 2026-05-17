-- Rename tyre_configurations -> global_setup
-- Tabela wyrosla z 9 progow opon do 31 globalnych parametrow aplikacji LTR
-- (finanse, koszty operacyjne, sprzedaz, ubezpieczenia, opony).

ALTER TABLE IF EXISTS public.tyre_configurations RENAME TO global_setup;

ALTER POLICY "Allow public read access for tyre_configurations"
  ON public.global_setup
  RENAME TO "Allow public read access for global_setup";

ALTER POLICY "Allow public update access for tyre_configurations"
  ON public.global_setup
  RENAME TO "Allow public update access for global_setup";

ALTER POLICY tyre_config_read  ON public.global_setup RENAME TO global_setup_read;
ALTER POLICY tyre_config_write ON public.global_setup RENAME TO global_setup_write;
