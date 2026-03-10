-- Migration generated from V1 Express_test database extract

-- 1. LTRAdminUbezpieczenia (Stawki AC / OC w zaleznosci od roku i klasy)
DO $$
DECLARE
    -- ID dla klas ubezpieczenia "zwyżkowego" z klasy B MAŁE SUV
    v_klasa_id integer;
BEGIN
    SELECT id INTO v_klasa_id FROM public.samar_classes WHERE name = 'Terenowo-rekreacyjne (SUV) - B MAŁE' LIMIT 1;
    
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (1, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (2, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (3, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (4, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (5, 0.0150, 1476.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (5, 0.0150, 1750.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (4, 0.0150, 1750.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (3, 0.0150, 1750.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (2, 0.0150, 1750.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (1, 0.0150, 1750.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (6, 0.0150, 1750.0000, NULL);
    INSERT INTO public.ltr_admin_ubezpieczenia ("KolejnyRok", "StawkaBazowaAC", "SkladkaOC", "KlasaId") VALUES (6, 0.0150, 1476.0000, NULL);
END $$;

-- 2. LTRAdminWspolczynnikiSzkodowe (Wspolczynniki dla poszczegolnych klas)
DO $$
BEGIN
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.1400, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.9800, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.8200, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.0800, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.0000, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.3100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 2.6200, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9300, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.1300, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.1200, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 0.9100, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 2.6200, 1.0000);
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (NULL, 1.0000, 1.0000);

    -- DLA POZOSTAŁYCH KLAS DODANYCH W V3 (W TYM DOSTAWCZE) DAJEMY NEUTRALNY WSPÓŁCZYNNIK 1.0000, PONIEWAŻ V1 ICH NIE MIAŁA
    INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (klasa_wr_id, wsp_sredni_przebieg, wsp_wartosc_szkody) 
    SELECT NULL, 1.0000, 1.0000 FROM public.samar_classes c
    WHERE c.id NOT IN (SELECT klasa_wr_id FROM public.ltr_admin_wspolczynniki_szkodowe WHERE klasa_wr_id IS NOT NULL);
END $$;

-- 3. LTRAdminParametry (Globalne nastawy szkodowosci i ryzyka ubezpieczeniowego)
UPDATE public.control_center SET
  ins_theft_doub_pct = 0.10,
  ins_driving_school_doub_pct = 0.5,
  ins_avg_damage_value = 2587,
  ins_avg_damage_mileage = 80000;
