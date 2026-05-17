-- Konsolidacja: przenosimy progi opon z global_setup do control_center (singleton id=1),
-- po czym dropujemy global_setup. control_center pozostaje source-of-truth dla kluczy
-- ktore istnialy w obu miejscach (np. normatywny_przebieg_mc = 1666, default_wibor = 3.81).

ALTER TABLE public.control_center
    ADD COLUMN IF NOT EXISTS all_season_threshold_1 numeric NOT NULL DEFAULT 60000,
    ADD COLUMN IF NOT EXISTS all_season_threshold_2 numeric NOT NULL DEFAULT 120000,
    ADD COLUMN IF NOT EXISTS all_season_threshold_3 numeric NOT NULL DEFAULT 180000,
    ADD COLUMN IF NOT EXISTS all_season_threshold_4 numeric NOT NULL DEFAULT 240000,
    ADD COLUMN IF NOT EXISTS all_season_threshold_5 numeric NOT NULL DEFAULT 300000,
    ADD COLUMN IF NOT EXISTS season_threshold_1 numeric NOT NULL DEFAULT 120000,
    ADD COLUMN IF NOT EXISTS season_threshold_2 numeric NOT NULL DEFAULT 180000,
    ADD COLUMN IF NOT EXISTS season_threshold_3 numeric NOT NULL DEFAULT 240000,
    ADD COLUMN IF NOT EXISTS season_threshold_4 numeric NOT NULL DEFAULT 300000;

UPDATE public.control_center cc SET
    all_season_threshold_1 = COALESCE((SELECT config_value::numeric FROM public.global_setup WHERE config_key = 'all_season_threshold_1'), cc.all_season_threshold_1),
    all_season_threshold_2 = COALESCE((SELECT config_value::numeric FROM public.global_setup WHERE config_key = 'all_season_threshold_2'), cc.all_season_threshold_2),
    all_season_threshold_3 = COALESCE((SELECT config_value::numeric FROM public.global_setup WHERE config_key = 'all_season_threshold_3'), cc.all_season_threshold_3),
    all_season_threshold_4 = COALESCE((SELECT config_value::numeric FROM public.global_setup WHERE config_key = 'all_season_threshold_4'), cc.all_season_threshold_4),
    all_season_threshold_5 = COALESCE((SELECT config_value::numeric FROM public.global_setup WHERE config_key = 'all_season_threshold_5'), cc.all_season_threshold_5),
    season_threshold_1     = COALESCE((SELECT config_value::numeric FROM public.global_setup WHERE config_key = 'season_threshold_1'),     cc.season_threshold_1),
    season_threshold_2     = COALESCE((SELECT config_value::numeric FROM public.global_setup WHERE config_key = 'season_threshold_2'),     cc.season_threshold_2),
    season_threshold_3     = COALESCE((SELECT config_value::numeric FROM public.global_setup WHERE config_key = 'season_threshold_3'),     cc.season_threshold_3),
    season_threshold_4     = COALESCE((SELECT config_value::numeric FROM public.global_setup WHERE config_key = 'season_threshold_4'),     cc.season_threshold_4)
WHERE id = 1;

DROP TABLE IF EXISTS public.global_setup;
