-- Migration: Simplify Utility Features (Deduplicate europallets, delete excessive details, recategorize)
-- Date: 2026-03-11

-- 1. Deduplicate europallets
DO $$
DECLARE
    target_euro_id UUID;
    cat_przestrzen UUID;
    cat_towing UUID;
    cat_seats UUID;
BEGIN
    -- Get target feature ID
    SELECT id INTO target_euro_id FROM reverse_search.universal_features WHERE feature_key = 'ilość_europalet' LIMIT 1;
    
    -- If target_euro_id is null, it means the seed hasn't run or this DB is different, but let's assume it exists.
    IF target_euro_id IS NOT NULL THEN
        -- 1a. Move state evidence
        UPDATE reverse_search.vehicle_feature_evidence
        SET feature_id = target_euro_id
        WHERE feature_id IN (
            SELECT id FROM reverse_search.universal_features 
            WHERE feature_key IN ('il_europalet', 'ilość_europalet1', 'ilość_europalet2')
        );

        -- 1b. Move state (handling conflicts by simply deleting duplicates for the same vehicle first)
        DELETE FROM reverse_search.vehicle_feature_state
        WHERE feature_id IN (SELECT id FROM reverse_search.universal_features WHERE feature_key IN ('il_europalet', 'ilość_europalet1', 'ilość_europalet2'))
        AND source_vehicle_id IN (
            SELECT source_vehicle_id FROM reverse_search.vehicle_feature_state WHERE feature_id = target_euro_id
        );

        UPDATE reverse_search.vehicle_feature_state
        SET feature_id = target_euro_id
        WHERE feature_id IN (
            SELECT id FROM reverse_search.universal_features 
            WHERE feature_key IN ('il_europalet', 'ilość_europalet1', 'ilość_europalet2')
        );

        -- 1c. Delete the duplicate features
        DELETE FROM reverse_search.universal_features 
        WHERE feature_key IN ('il_europalet', 'ilość_europalet1', 'ilość_europalet2');
    END IF;

    -- 2. Recategorize features
    SELECT id INTO cat_przestrzen FROM reverse_search.universal_feature_categories WHERE category_key = 'przestrzeń_ładunkowa' LIMIT 1;
    SELECT id INTO cat_towing FROM reverse_search.universal_feature_categories WHERE category_key = 'towing' LIMIT 1;
    SELECT id INTO cat_seats FROM reverse_search.universal_feature_categories WHERE category_key = 'seats' LIMIT 1;

    -- m2 -> Przestrzeń ładunkowa
    IF cat_przestrzen IS NOT NULL THEN
        UPDATE reverse_search.universal_features SET category_id = cat_przestrzen WHERE feature_key = 'm2';
    END IF;

    -- Uciąg i hak -> Holowanie / Hak (towing)
    -- Jeśli nie ma w 'towing', to do 'wymiary_masy'
    IF cat_towing IS NULL THEN
        SELECT id INTO cat_towing FROM reverse_search.universal_feature_categories WHERE category_key = 'wymiary_masy' LIMIT 1;
    END IF;
    IF cat_towing IS NOT NULL THEN
        UPDATE reverse_search.universal_features SET category_id = cat_towing WHERE feature_key IN ('d_uciag', 's_nacisk_na_hak');
    END IF;

    -- Fotele z masażem -> Fotele (seats), jeśli brak to do 'komfort_wnętrze' / 'comfort'
    IF cat_seats IS NULL THEN
        SELECT id INTO cat_seats FROM reverse_search.universal_feature_categories WHERE category_key IN ('komfort_wnętrze', 'comfort') LIMIT 1;
    END IF;
    IF cat_seats IS NOT NULL THEN
        UPDATE reverse_search.universal_features SET category_id = cat_seats WHERE feature_key IN ('fotele_przednie_z_funkcją_masażu', 'fotele_tylne_z_funkcją_masażu');
    END IF;

    -- 3. Delete overly granular features (drzwi, burty, platformy windy, puste zbiorniki 1/2)
    DELETE FROM reverse_search.universal_features
    WHERE feature_key IN (
        'wysokość_progu_załadunku_w_mm',
        'wysokość_tylnych_drzwi_załadunku_w_mm',
        'szerokość_tylnych_drzwi_załadunku_w_mm',
        'wysokość_drzwi_bocznego_załadunku_w_mm',
        'szerokość_drzwi_bocznego_załadunku_w_mm',
        'wysokość_burt_załadunku_w_mm',
        'długość_platformy_windy',
        'szerokość_platformy_windy',
        'zbiornik_na_wodę_1_pojemność_w_litrach',
        'zbiornik_na_wodę_2_pojemność_zbiorniaka_w_litrach',
        'skrzynia_narzędziowa_1_w_litrach',
        'skrzynia_narzędziowa_2_w_litrach'
    );

END $$;
