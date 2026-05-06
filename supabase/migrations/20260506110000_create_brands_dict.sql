-- A2: SOT-aligned brands dictionary.
-- Source: GSheet `brands_dict` tab (25 rows). Currently absent from DB.
-- Today `tabela_rabaty.marka` is free text — adding this lookup enables future
-- normalization (e.g. SEAT/CUPRA, VW Dostawcze) without breaking existing rows.
-- No FK additions in this PR; FK refactor is a separate calc-touching change.

CREATE TABLE IF NOT EXISTS public.brands_dict (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    category    TEXT,
    api_key     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE public.brands_dict IS
'SOT-aligned brand dictionary. Source: GSheet `brands_dict` tab.';

INSERT INTO public.brands_dict (id, name, category, api_key) VALUES
    ( 1, 'ALFA',       'Osobowa', 'ALFA'),
    ( 2, 'AUDI',       'Osobowa', 'AUDI'),
    ( 3, 'BMW',        'Osobowa', 'BMW'),
    ( 4, 'BYD',        'Osobowa', 'BYD'),
    ( 5, 'CITROEN',    'Osobowa', 'CITROEN'),
    ( 6, 'CUPRA',      'Osobowa', 'CUPRA'),
    ( 7, 'DACIA',      'Osobowa', 'DACIA'),
    ( 8, 'FIAT',       'Osobowa', 'FIAT'),
    ( 9, 'FORD',       'Osobowa', 'FORD'),
    (10, 'HYUNDAI',    'Osobowa', 'HYUNDAI'),
    (11, 'IVECO',      'Osobowa', 'IVECO'),
    (12, 'KIA',        'Osobowa', 'KIA'),
    (13, 'MAN',        'Osobowa', 'MAN'),
    (14, 'MERCEDES',   'Osobowa', 'MERCEDES'),
    (15, 'NISSAN',     'Osobowa', 'NISSAN'),
    (16, 'OPEL',       'Osobowa', 'OPEL'),
    (17, 'PEUGEOT',    'Osobowa', 'PEUGEOT'),
    (18, 'RENAULT',    'Osobowa', 'RENAULT'),
    (19, 'SEAT',       'Osobowa', 'SEAT'),
    (20, 'SKODA',      'Osobowa', 'SKODA'),
    (21, 'SUBARU',     'Osobowa', 'SUBARU'),
    (22, 'SUZUKI',     'Osobowa', 'SUZUKI'),
    (23, 'TOYOTA',     'Osobowa', 'TOYOTA'),
    (24, 'VOLKSWAGEN', 'Osobowa', 'VOLKSWAGEN'),
    (25, 'VOLVO',      'Osobowa', 'VOLVO')
ON CONFLICT (id) DO UPDATE SET
    name     = EXCLUDED.name,
    category = EXCLUDED.category,
    api_key  = EXCLUDED.api_key;
