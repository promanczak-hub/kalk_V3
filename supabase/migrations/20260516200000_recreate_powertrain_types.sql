-- Odtworzenie public.powertrain_types po niezamierzonym dropie w 20260516130000.
-- Tabela jest live dependency dla fn_powertrain_family (uzywanej przez
-- rpc_get_similar_vehicles_batch_semantic do liczenia fuel_match na poziomie rodziny).
-- SOT: GSheet _dict_powertrains (9 wierszy: code, name_pl, family).

CREATE TABLE IF NOT EXISTS public.powertrain_types (
    code text PRIMARY KEY,
    name_pl text NOT NULL UNIQUE,
    family text NOT NULL
);

INSERT INTO public.powertrain_types (code, name_pl, family) VALUES
    ('ice_pb',  'Benzyna (PB)',              'ice'),
    ('ice_on',  'Diesel (ON)',               'ice'),
    ('mhev_pb', 'Benzyna mHEV (PB-mHEV)',    'mhev'),
    ('mhev_on', 'Diesel mHEV (ON-mHEV)',     'mhev'),
    ('hev',     'Hybryda (HEV)',             'hev'),
    ('phev',    'Hybryda Plug-in (PHEV)',    'phev'),
    ('bev',     'Elektryczny (BEV)',         'bev'),
    ('fcev',    'Wodór (FCEV)',              'fcev'),
    ('lpg',     'Autogaz (LPG)',             'lpg')
ON CONFLICT (code) DO UPDATE SET
    name_pl = EXCLUDED.name_pl,
    family  = EXCLUDED.family;
