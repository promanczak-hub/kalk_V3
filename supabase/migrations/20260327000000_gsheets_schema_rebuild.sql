-- ============================================================
-- Migration: FINAL Rebuild (v2) - INTEGER Class IDs 1:1
-- ============================================================

-- 1. tab_okres_final
DROP TABLE IF EXISTS tab_okres_final CASCADE;
CREATE TABLE tab_okres_final (
    id                                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar                         INTEGER NOT NULL, -- Match 'Klasa SAMAR (FK)' or similar
    rodzaj_silnika                      TEXT NOT NULL,    -- 'Rodzaj silnika' (Text in sheet)
    km_35000                            FLOAT,
    km_70000                            FLOAT,
    km_105000                           FLOAT,
    km_140000                           FLOAT,
    km_175000                           FLOAT,
    km_210000                           FLOAT,
    km_245000                           FLOAT,
    created_at                          TIMESTAMPTZ DEFAULT now()
);

-- 2. samar_class_depreciation_rates
DROP TABLE IF EXISTS samar_class_depreciation_rates CASCADE;
CREATE TABLE samar_class_depreciation_rates (
    id                      UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar             INTEGER NOT NULL UNIQUE,
    benzyna_pb              FLOAT,
    diesel_on               FLOAT,
    benzyna_mhev_pb_mhev    FLOAT,
    diesel_mhev_on_mhev     FLOAT,
    hybryda_hev             FLOAT,
    plug_in_hybrid_phev     FLOAT,
    elektryczny_bev         FLOAT,
    wodor_fcev              FLOAT,
    lpg                     FLOAT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- 3. samar_class_mileage_corrections
DROP TABLE IF EXISTS samar_class_mileage_corrections CASCADE;
CREATE TABLE samar_class_mileage_corrections (
    id                      UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar             INTEGER NOT NULL UNIQUE,
    prog_przebiegu_km       INTEGER,
    korekta_lt_prog         FLOAT,
    korekta_gt_prog         FLOAT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- 4. samar_brand_corrections
DROP TABLE IF EXISTS samar_brand_corrections CASCADE;
CREATE TABLE samar_brand_corrections (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar INTEGER NOT NULL,
    marka       TEXT NOT NULL,
    model       TEXT,
    silnik      TEXT,
    korekta     FLOAT NOT NULL DEFAULT 0.0,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 5. replacement_car_rates
DROP TABLE IF EXISTS replacement_car_rates CASCADE;
CREATE TABLE replacement_car_rates (
    id                      UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar_fk          INTEGER NOT NULL UNIQUE,
    srednia_l_dni_rok       FLOAT,
    stawka_dzienna_netto_zl FLOAT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- 6. ltr_admin_ubezpieczenia
DROP TABLE IF EXISTS ltr_admin_ubezpieczenia CASCADE;
CREATE TABLE ltr_admin_ubezpieczenia (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar_fk      INTEGER NOT NULL,
    rok                 INTEGER NOT NULL,
    stawka_bazowa_ac    FLOAT,
    skladka_oc_zl       FLOAT,
    wsp_sredni_przebieg FLOAT,
    wsp_wartosc_szkody  FLOAT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- 7. samar_class_service_rates
DROP TABLE IF EXISTS samar_class_service_rates CASCADE;
CREATE TABLE samar_class_service_rates (
    id                      UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar_fk          INTEGER NOT NULL,
    przebieg_do             INTEGER NOT NULL,
    stawka_aso_per_km       FLOAT,
    stawka_non_aso_per_km   FLOAT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

-- 8. koszty_opon
DROP TABLE IF EXISTS koszty_opon CASCADE;
CREATE TABLE koszty_opon (
    id                              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    srednica                        INTEGER NOT NULL UNIQUE,
    budget                          FLOAT,
    medium                          FLOAT,
    premium                         FLOAT,
    wzmocnione_budget               FLOAT,
    wzmocnione_medium               FLOAT,
    wzmocnione_premium              FLOAT,
    wielosezon_budget               FLOAT,
    wielosezon_medium               FLOAT,
    wielosezon_premium              FLOAT,
    wielosezon_wzmocnione_budget    FLOAT,
    wielosezon_wzmocnione_medium    FLOAT,
    wielosezon_wzmocnione_premium   FLOAT,
    odkup_opon                      FLOAT,
    created_at                      TIMESTAMPTZ DEFAULT now()
);

-- 9. samar_classes
DROP TABLE IF EXISTS samar_classes CASCADE;
CREATE TABLE samar_classes (
    id                              INTEGER PRIMARY KEY, -- ID_Numeryczne
    name                            TEXT,                -- Nazwa_Klasy_SAMAR
    example_models                  TEXT,
    created_at                      TIMESTAMPTZ DEFAULT now()
);

-- 10. body_types
DROP TABLE IF EXISTS body_types CASCADE;
CREATE TABLE body_types (
    id              INTEGER PRIMARY KEY,
    nazwa_nadwozia  TEXT,
    typ_pojazdu     TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);
