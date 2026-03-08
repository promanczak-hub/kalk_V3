-- Migration: Augment samar_classes as the MASTER table
-- Guarded: skip if samar_classes does not exist yet

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'samar_classes' AND table_schema = 'public') THEN
        RETURN;
    END IF;

    -- 1. Add new columns
    ALTER TABLE public.samar_classes
        ADD COLUMN IF NOT EXISTS excel_code TEXT,
        ADD COLUMN IF NOT EXISTS klasa_wr_id INTEGER,
        ADD COLUMN IF NOT EXISTS category TEXT,
        ADD COLUMN IF NOT EXISTS size_class TEXT,
        ADD COLUMN IF NOT EXISTS example_models TEXT;

    -- 2. Populate mappings
    UPDATE public.samar_classes SET excel_code='A',      klasa_wr_id=1,  category='PODSTAWOWA',             size_class='A MINI'                  WHERE id=1;
    UPDATE public.samar_classes SET excel_code='B',      klasa_wr_id=3,  category='PODSTAWOWA',             size_class='B MAŁE'                  WHERE id=2;
    UPDATE public.samar_classes SET excel_code='C',      klasa_wr_id=7,  category='PODSTAWOWA',             size_class='C NIŻSZA ŚREDNIA'        WHERE id=3;
    UPDATE public.samar_classes SET excel_code='D',      klasa_wr_id=11, category='PODSTAWOWA',             size_class='D ŚREDNIA'               WHERE id=4;
    UPDATE public.samar_classes SET excel_code='E',      klasa_wr_id=15, category='PODSTAWOWA',             size_class='E WYŻSZA'                WHERE id=5;
    UPDATE public.samar_classes SET excel_code='F',      klasa_wr_id=17, category='PODSTAWOWA',             size_class='F LUKSUSOWE, G S. LUKS.' WHERE id=6;

    UPDATE public.samar_classes SET excel_code='Asport', klasa_wr_id=2,  category='SPORTOWO-REKREACYJNE',   size_class='A MINI'                  WHERE id=12;
    UPDATE public.samar_classes SET excel_code='Bsport', klasa_wr_id=4,  category='SPORTOWO-REKREACYJNE',   size_class='B MAŁE'                  WHERE id=13;
    UPDATE public.samar_classes SET excel_code='Csport', klasa_wr_id=8,  category='SPORTOWO-REKREACYJNE',   size_class='C NIŻSZA ŚREDNIA'        WHERE id=16;
    UPDATE public.samar_classes SET excel_code='Dsport', klasa_wr_id=12, category='SPORTOWO-REKREACYJNE',   size_class='D ŚREDNIA'               WHERE id=19;
    UPDATE public.samar_classes SET excel_code='Fsport', klasa_wr_id=18, category='SPORTOWO-REKREACYJNE',   size_class='F LUKSUSOWE, G S. LUKS.' WHERE id=23;

    UPDATE public.samar_classes SET excel_code='Bsuv',   klasa_wr_id=5,  category='TERENOWO-REKREACYJNE',   size_class='B MAŁE'                  WHERE id=14;
    UPDATE public.samar_classes SET excel_code='Csuv',   klasa_wr_id=9,  category='TERENOWO-REKREACYJNE',   size_class='C NIŻSZA ŚREDNIA'        WHERE id=17;
    UPDATE public.samar_classes SET excel_code='Dsuv',   klasa_wr_id=13, category='TERENOWO-REKREACYJNE',   size_class='D ŚREDNIA'               WHERE id=20;
    UPDATE public.samar_classes SET excel_code='Esuv',   klasa_wr_id=16, category='TERENOWO-REKREACYJNE',   size_class='E WYŻSZA'                WHERE id=22;
    UPDATE public.samar_classes SET excel_code='Fsuv',   klasa_wr_id=19, category='TERENOWO-REKREACYJNE',   size_class='G S. LUKSUSOWE'          WHERE id=24;

    UPDATE public.samar_classes SET excel_code='Bvan',   klasa_wr_id=6,  category='VANY',                   size_class='B MICROVANY'             WHERE id=15;
    UPDATE public.samar_classes SET excel_code='Cvan',   klasa_wr_id=10, category='VANY',                   size_class='C MINIVANY'              WHERE id=18;
    UPDATE public.samar_classes SET excel_code='Dvan',   klasa_wr_id=14, category='VANY',                   size_class='D VANY'                  WHERE id=21;

    UPDATE public.samar_classes SET excel_code='M',          klasa_wr_id=20, category='KOMBIVANY',              size_class='H KOMBI-VANY'            WHERE id=25;
    UPDATE public.samar_classes SET excel_code='Mvan',       klasa_wr_id=21, category='S. DOSTAWCZE DO 6T',     size_class='KOMBI VAN, VAN'          WHERE id=26;
    UPDATE public.samar_classes SET excel_code='R',          klasa_wr_id=22, category='MINIBUS',                size_class='I MINIBUS'               WHERE id=27;
    UPDATE public.samar_classes SET excel_code='P',          klasa_wr_id=23, category='S. DOSTAWCZE DO 6T',     size_class='ŚREDNIE/CIĘŻKIE DOST.'   WHERE id=28;
    UPDATE public.samar_classes SET excel_code='T PICK-UP',  klasa_wr_id=24, category='S. DOSTAWCZE DO 6T',     size_class='PICK-UP'                 WHERE id=29;
    UPDATE public.samar_classes SET excel_code='Pciez',      klasa_wr_id=NULL, category='S. DOSTAWCZE DO 6T',   size_class='CIĘŻKIE DOSTAWCZE S.'    WHERE id=30;

    -- 3. Seed example_models (guarded)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'KlasaSAMAR_czak' AND table_schema = 'public') THEN
        UPDATE public.samar_classes sc
        SET example_models = czak.col_8
        FROM "KlasaSAMAR_czak" czak
        WHERE sc.name = czak.col_1
          AND czak.col_8 IS NOT NULL
          AND czak.col_8 != '';
    END IF;

    -- 4. Index
    CREATE UNIQUE INDEX IF NOT EXISTS idx_samar_classes_excel_code
        ON public.samar_classes(excel_code)
        WHERE excel_code IS NOT NULL;
END $$;
