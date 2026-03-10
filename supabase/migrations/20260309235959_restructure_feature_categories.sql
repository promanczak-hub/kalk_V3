-- Migration: Restructure universal_feature_categories
-- Fixes misclassified features, removes duplicates, adds new categories

BEGIN;

-- ================================================
-- 1. Create new category: Parkowanie
-- ================================================
INSERT INTO reverse_search.universal_feature_categories
    (category_key, display_name, vehicle_scope, sort_order, is_active)
VALUES
    ('parking', 'Parkowanie', 'both', 72, true)
ON CONFLICT (category_key) DO NOTHING;


-- ================================================
-- 2. Fix display_name: m2 → powierzchnia ładunkowa w m²
-- ================================================
UPDATE reverse_search.universal_features
SET display_name = 'powierzchnia ładunkowa w m²'
WHERE feature_key = 'm2';


-- ================================================
-- 3. Remove duplicate "il europalet" (keep "ilość europalet")
-- ================================================

-- 3a. Move any evidence from il_europalet → ilosc_europalet
UPDATE reverse_search.vehicle_feature_evidence
SET feature_id = (
    SELECT id FROM reverse_search.universal_features
    WHERE feature_key = 'ilosc_europalet' LIMIT 1
)
WHERE feature_id = (
    SELECT id FROM reverse_search.universal_features
    WHERE feature_key = 'il_europalet' LIMIT 1
)
AND (SELECT id FROM reverse_search.universal_features WHERE feature_key = 'ilosc_europalet' LIMIT 1) IS NOT NULL
AND (SELECT id FROM reverse_search.universal_features WHERE feature_key = 'il_europalet' LIMIT 1) IS NOT NULL;

-- 3b. Move any state from il_europalet → ilosc_europalet
UPDATE reverse_search.vehicle_feature_state
SET feature_id = (
    SELECT id FROM reverse_search.universal_features
    WHERE feature_key = 'ilosc_europalet' LIMIT 1
)
WHERE feature_id = (
    SELECT id FROM reverse_search.universal_features
    WHERE feature_key = 'il_europalet' LIMIT 1
)
AND (SELECT id FROM reverse_search.universal_features WHERE feature_key = 'ilosc_europalet' LIMIT 1) IS NOT NULL
AND (SELECT id FROM reverse_search.universal_features WHERE feature_key = 'il_europalet' LIMIT 1) IS NOT NULL;

-- 3c. Delete aliases for il_europalet
DELETE FROM reverse_search.universal_feature_aliases
WHERE feature_id = (
    SELECT id FROM reverse_search.universal_features
    WHERE feature_key = 'il_europalet' LIMIT 1
);

-- 3d. Delete the duplicate feature itself
DELETE FROM reverse_search.universal_features
WHERE feature_key = 'il_europalet';


-- ================================================
-- 4. Set vehicle_scope=commercial on cargo-only features
-- ================================================
UPDATE reverse_search.universal_features
SET vehicle_scope = 'commercial'
WHERE feature_key IN ('m2', 'ilosc_europalet');


-- ================================================
-- 5. Move features to correct categories
-- ================================================

-- Helper: move feature by key to category by key
-- comfort → safety
UPDATE reverse_search.universal_features
SET category_id = (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'safety')
WHERE feature_key IN (
    'esp',
    'kurtyny_powietrzne',
    'poduszki_powietrzne',
    'kolo_dojazdowe_i_zestaw_narzedzi',
    'zestaw_naprawczy'
)
AND (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'safety') IS NOT NULL;

-- comfort → lighting
UPDATE reverse_search.universal_features
SET category_id = (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'lighting')
WHERE feature_key IN (
    'lampy_przeciwmgielne',
    'reflektory',
    'swiatla_do_jazdy_dziennej'
)
AND (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'lighting') IS NOT NULL;

-- comfort → multimedia
UPDATE reverse_search.universal_features
SET category_id = (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'multimedia')
WHERE feature_key IN (
    'bluetooth',
    'radio'
)
AND (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'multimedia') IS NOT NULL;

-- comfort → cargo (m2, europalet)
UPDATE reverse_search.universal_features
SET category_id = (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo')
WHERE feature_key IN (
    'm2',
    'ilosc_europalet'
)
AND (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo') IS NOT NULL;

-- multimedia → safety (Ogranicznik prędkości)
UPDATE reverse_search.universal_features
SET category_id = (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'safety')
WHERE feature_key = 'ogranicznik_predkosci'
AND (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'safety') IS NOT NULL;

-- multimedia → drivetrain (Funkcja szybkiego ładowania)
UPDATE reverse_search.universal_features
SET category_id = (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'drivetrain')
WHERE feature_key = 'funkcja_szybkiego_ladowania_samochodu'
AND (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'drivetrain') IS NOT NULL;

-- safety → multimedia (system audio)
UPDATE reverse_search.universal_features
SET category_id = (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'multimedia')
WHERE feature_key = 'system_audio'
AND (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'multimedia') IS NOT NULL;

-- safety → comfort (System Auto hold)
UPDATE reverse_search.universal_features
SET category_id = (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort')
WHERE feature_key = 'system_auto_hold'
AND (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort') IS NOT NULL;

-- safety → parking (czujniki + kamera + 360)
UPDATE reverse_search.universal_features
SET category_id = (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'parking')
WHERE feature_key IN (
    'czujniki_parkowania_przod',
    'czujniki_parkowania_tyl',
    'kamera_parkowania_tyl',
    'system_360'
)
AND (SELECT id FROM reverse_search.universal_feature_categories WHERE category_key = 'parking') IS NOT NULL;

COMMIT;
