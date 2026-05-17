-- Konwersja control_center z wide-row singletonu (1 wiersz x ~43 kolumny)
-- na pionowy EAV (key, value, updated_at). Dashboard Supabase pokazuje
-- teraz parametry jako wiersze, jeden klucz na wiersz.
--
-- Backward compatibility: adapter w core/control_center.py rekonstruuje
-- wide-row dict z key/value rows tak, by call-site'y w kalkulatorach
-- i Pydantic ControlCenterSettings dzialaly bez zmian.
--
-- Stara tabela zostaje jako control_center_legacy_wide do recznego DROP
-- po pelnej weryfikacji w prod (smoke test kalkulatorow + sync GSheet).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.control_center WHERE id = 1) THEN
        RAISE EXCEPTION 'control_center singleton (id=1) not found - aborting EAV migration';
    END IF;
END $$;

ALTER TABLE public.control_center RENAME TO control_center_legacy_wide;
ALTER TRIGGER trigger_update_control_center_updated_at ON public.control_center_legacy_wide RENAME TO trigger_update_control_center_legacy_updated_at;

CREATE TABLE public.control_center (
    key text PRIMARY KEY,
    value jsonb NOT NULL,
    category text,
    description text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.control_center IS
    'Globalne parametry aplikacji LTR jako key/value (pionowy EAV). '
    'Kazdy wiersz = jeden parametr. Adapter w core/control_center.py '
    'rekonstruuje wide-row dict dla kalkulatorow.';

INSERT INTO public.control_center (key, value, updated_at)
SELECT
    j.key,
    j.value,
    cw.updated_at
FROM public.control_center_legacy_wide cw,
     LATERAL jsonb_each(to_jsonb(cw) - 'id' - 'updated_at') AS j(key, value)
WHERE cw.id = 1;

UPDATE public.control_center SET category = 'finanse'        WHERE key IN ('default_wibor','default_ltr_margin','bank_spread','vat_rate');
UPDATE public.control_center SET category = 'samar_rv'       WHERE key LIKE 'samar_rv_%';
UPDATE public.control_center SET category = 'samar'          WHERE key LIKE 'samar_%' AND key NOT LIKE 'samar_rv_%';
UPDATE public.control_center SET category = 'samar'          WHERE key LIKE 'value_threshold_%';
UPDATE public.control_center SET category = 'ubezpieczenia'  WHERE key LIKE 'ins_%';
UPDATE public.control_center SET category = 'opony'          WHERE key LIKE 'all_season_threshold_%' OR key LIKE 'season_threshold_%';
UPDATE public.control_center SET category = 'opony'          WHERE key IN ('cost_tyre_storage','cost_tyre_swap');
UPDATE public.control_center SET category = 'koszty'         WHERE (key LIKE 'cost_%' OR key = 'gsm_amortization_years') AND key NOT IN ('cost_tyre_storage','cost_tyre_swap');
UPDATE public.control_center SET category = 'flota'          WHERE key IN ('normatywny_przebieg_mc','przewidywana_cena_sprzedazy_lo','budzet_marketingowy_ltr','resale_time_days');

CREATE TRIGGER trigger_update_control_center_updated_at
BEFORE UPDATE ON public.control_center
FOR EACH ROW
EXECUTE FUNCTION update_control_center_updated_at();

ALTER TABLE public.control_center ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access for control_center"
ON public.control_center
FOR SELECT
USING (true);

CREATE POLICY "Allow public update access for control_center"
ON public.control_center
FOR UPDATE
USING (true)
WITH CHECK (true);

CREATE POLICY "Allow public insert access for control_center"
ON public.control_center
FOR INSERT
WITH CHECK (true);

CREATE POLICY "Allow public delete access for control_center"
ON public.control_center
FOR DELETE
USING (true);
